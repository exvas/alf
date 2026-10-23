"""Row-level wiring of ERPNext documents to the vehicle lifecycle.

Purchase Receipt        -> creates / updates the Vehicle and marks it Purchased
Stock Reservation Entry -> marks the vehicle Reserved (or back to Ready for Sale)
Delivery Note           -> marks the vehicle Delivered
Sales Invoice           -> marks the vehicle Sold and records the selling price
Vehicle Expense         -> recomputes cost / profit of the vehicle
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, now, nowdate

from alf.alf.inventory import (
	compute_vehicle_costs,
	get_serial_no_for_row,
	get_serial_nos,
	get_vehicle_for_serial,
	is_vehicle_item,
	recompute_vehicle,
	set_parking,
	set_vehicle_status,
)

FUEL_TYPES = ("Petrol", "Diesel", "Natural Gas", "Electric")


def purchase_receipt_before_submit(doc, method=None):
	"""Vehicle Purchase & Inventory: one Vehicle per VIN received.

	Runs on `before_submit` - not `on_submit` - so the vehicle link is already on
	the item rows when ERPNext writes the stock GL entries. That is what makes
	the `Vehicle` accounting dimension flow into `GL Entry` automatically.
	"""
	vehicles = set()

	for row in doc.items:
		if not is_vehicle_item(row.item_code):
			continue

		serial_nos = get_serial_nos(row)
		if not serial_nos:
			frappe.msgprint(
				_(
					"Row #{0}: Item {1} is serial tracked but no VIN (Serial No) was entered, so no Vehicle was created."
				).format(row.idx, frappe.bold(row.item_code)),
				alert=True,
				indicator="orange",
			)
			continue

		vehicle_name = None
		for serial_no in serial_nos:
			vehicle_name = sync_vehicle_from_purchase_receipt(doc, row, serial_no) or vehicle_name

		if vehicle_name:
			row.vehicle = vehicle_name
			vehicles.add(vehicle_name)

	# Header dimension covers the non-item Profit and Loss lines (taxes, round off).
	if len(vehicles) == 1:
		doc.vehicle = next(iter(vehicles))


def sync_vehicle_from_purchase_receipt(doc, row, serial_no):
	"""Create or refresh the Vehicle for one VIN.

	The `Serial No` record does not exist yet on `before_submit` (ERPNext creates
	it while submitting), so it is read defensively and the row values are used
	as the fallback.
	"""
	serial_details = (
		frappe.db.get_value(
			"Serial No",
			serial_no,
			["item_code", "item_name", "item_group", "brand", "warehouse", "purchase_rate"],
			as_dict=True,
		)
		or frappe._dict()
	)

	incoming_rate = flt(row.get("valuation_rate")) or flt(serial_details.purchase_rate) or flt(row.rate)
	brand = serial_details.brand or frappe.get_cached_value("Item", row.item_code, "brand")
	item_label = serial_details.item_name or row.item_name or row.item_code
	existing = frappe.db.get_value("Vehicle", {"serial_no": serial_no})

	if existing:
		vehicle = frappe.get_doc("Vehicle", existing)
		vehicle.update(
			{
				"purchase_price": incoming_rate,
				"purchase_date": doc.posting_date,
				"purchase_receipt": doc.name,
				"purchase_document_type": doc.doctype,
				"supplier": doc.supplier,
				"seller_name": doc.supplier_name or doc.supplier,
				"warehouse": serial_details.warehouse or row.warehouse,
				"company": doc.company,
				"item_code": row.item_code,
			}
		)
		blank_values = {
			"stock_id": existing,
			"vin": serial_no,
			"make": brand or "Not Set",
			"model": item_label,
			"item_code": row.item_code,
			"item_name": item_label,
			"stock_uom": frappe.get_cached_value("Item", row.item_code, "stock_uom"),
			"fuel_type": get_fuel_type(row.item_code),
			"status": "Purchased",
			"parking_location": serial_details.warehouse or row.warehouse,
			"parking_from": doc.posting_date,
		}
		for fieldname, value in blank_values.items():
			if not vehicle.get(fieldname):
				vehicle.set(fieldname, value)

		vehicle.append(
			"status_history",
			{
				"status": "Purchased",
				"posting_datetime": now(),
				"voucher_type": doc.doctype,
				"voucher_no": doc.name,
				"vehicle_reference": vehicle.name,
				"remarks": _("Re-synced from Purchase Receipt {0}").format(doc.name),
			},
		)
		compute_vehicle_costs(vehicle)
		vehicle.flags.ignore_permissions = True
		vehicle.save(ignore_permissions=True)
	else:
		vehicle = frappe.get_doc(
			{
				"doctype": "Vehicle",
				"license_plate": serial_no,
				"make": brand or "Not Set",
				"model": item_label,
				"item_name": item_label,
				"last_odometer": 0,
				"fuel_type": get_fuel_type(row.item_code),
				"uom": frappe.get_cached_value("Item", row.item_code, "stock_uom") or "Nos",
				"vehicle_value": incoming_rate,
				"item_code": row.item_code,
				"stock_uom": frappe.get_cached_value("Item", row.item_code, "stock_uom"),
				"serial_no": serial_no,
				"vin": serial_no,
				"stock_id": serial_no,
				"warehouse": serial_details.warehouse or row.warehouse,
				"company": doc.company,
				"purchase_price": incoming_rate,
				"purchase_date": doc.posting_date,
				"purchase_receipt": doc.name,
				"purchase_document_type": doc.doctype,
				"supplier": doc.supplier,
				"seller_name": doc.supplier_name or doc.supplier,
				"status": "Purchased",
				"parking_location": serial_details.warehouse or row.warehouse,
				"parking_from": doc.posting_date,
				"status_history": [
					{
						"status": "Purchased",
						"voucher_type": doc.doctype,
						"voucher_no": doc.name,
						"remarks": _("Created from Purchase Receipt {0}").format(doc.name),
					}
				],
			}
		)
		vehicle.flags.ignore_mandatory = True
		vehicle.insert(ignore_permissions=True, ignore_links=True)
		recompute_vehicle(vehicle.name)

	return vehicle.name


def purchase_receipt_on_submit(doc, method=None):
	"""Link each submitted VIN to its Vehicle once the Serial No row exists."""
	for row in doc.items:
		if not is_vehicle_item(row.item_code):
			continue

		for serial_no in get_serial_nos(row):
			if not frappe.db.exists("Serial No", serial_no):
				continue

			vehicle = frappe.db.get_value("Vehicle", {"serial_no": serial_no})
			if vehicle:
				frappe.db.set_value("Serial No", serial_no, "vehicle", vehicle, update_modified=False)


def stock_reservation_entry_on_submit(doc, method=None):
	"""Manual vehicle reservation: Sales Order -> Stock Reservation -> Reserve."""
	if doc.docstatus != 1 or not cint(doc.reserved_qty):
		return

	vehicle = get_vehicle_for_reservation(doc)
	if not vehicle:
		return

	frappe.db.set_value("Stock Reservation Entry", doc.name, "vehicle", vehicle, update_modified=False)

	set_vehicle_status(
		vehicle,
		"Reserved",
		doc.doctype,
		doc.name,
		_("Reserved for {0} {1}").format(doc.voucher_type, doc.voucher_no),
		extra={
			"sales_order": doc.voucher_no if doc.voucher_type == "Sales Order" else None,
			"customer": frappe.db.get_value(doc.voucher_type, doc.voucher_no, "customer")
			if doc.voucher_type == "Sales Order"
			else None,
		},
	)


def stock_reservation_entry_on_cancel(doc, method=None):
	vehicle = get_vehicle_for_reservation(doc)
	if not vehicle:
		return

	if frappe.db.exists(
		"Stock Reservation Entry",
		{
			"serial_no": frappe.db.get_value("Vehicle", vehicle, "serial_no"),
			"docstatus": 1,
			"status": ("not in", ["Delivered", "Cancelled"]),
		},
	):
		other = frappe.get_value(
			"Stock Reservation Entry",
			{
				"voucher_type": doc.voucher_type,
				"voucher_no": doc.voucher_no,
				"docstatus": 1,
				"name": ("!=", doc.name),
				"status": ("not in", ["Delivered", "Cancelled"]),
			},
			"name",
		)
		if other or frappe.db.get_value("Stock Reservation Entry", doc.name, "status") != "Cancelled":
			return

	if frappe.db.get_value("Vehicle", vehicle, "sales_invoice"):
		return

	set_vehicle_status(
		vehicle,
		"Ready for Sale",
		doc.doctype,
		doc.name,
		_("Reservation cancelled"),
		extra={"sales_order": None},
	)


def delivery_note_on_submit(doc, method=None):
	"""The vehicle left the yard; invoicing may still follow."""
	for row in doc.items:
		vehicle = row.get("vehicle") or get_vehicle_for_serial(get_serial_no_for_row(row))
		if not vehicle:
			continue

		if frappe.db.get_value("Vehicle", vehicle, "status") in ("Reserved", "Ready for Sale", "Parked"):
			set_vehicle_status(
				vehicle, "Delivered", doc.doctype, doc.name, _("Delivered against {0}").format(doc.name)
			)

		if row.warehouse:
			set_parking(vehicle, row.warehouse, doc.posting_date)


def sales_invoice_on_submit(doc, method=None):
	if doc.docstatus != 1:
		return

	for row in doc.items:
		vehicle = row.get("vehicle") or get_vehicle_for_serial(get_serial_no_for_row(row))
		if not vehicle:
			continue

		# A booking / advance invoice must not roll a sold vehicle back.
		if doc.get("is_vehicle_booking") and frappe.db.get_value("Vehicle", vehicle, "status") == "Sold":
			frappe.db.set_value("Vehicle", vehicle, "customer", doc.customer, update_modified=True)
			continue

		status = "Reserved" if doc.get("is_vehicle_booking") else "Sold"
		values = {"customer": doc.customer}
		if status == "Sold":
			values.update({"sales_invoice": doc.name, "selling_price": flt(row.amount)})

		set_vehicle_status(
			vehicle,
			status,
			doc.doctype,
			doc.name,
			_("{0} against {1}").format(status, doc.name),
			extra=values,
		)
		recompute_vehicle(vehicle)

	if doc.get("trade_in_vehicle"):
		on_trade_in(doc)


def sales_invoice_on_cancel(doc, method=None):
	for row in doc.items:
		vehicle = row.get("vehicle") or get_vehicle_for_serial(get_serial_no_for_row(row))
		if not vehicle:
			continue

		values = {"customer": None}
		if not doc.get("is_vehicle_booking"):
			values.update(
				{
					"sales_invoice": None,
					"selling_price": 0,
					"status": "Reserved" if has_open_reservation(vehicle) else "Ready for Sale",
				}
			)

		frappe.db.set_value("Vehicle", vehicle, values, update_modified=True)
		recompute_vehicle(vehicle)


def vehicle_expense_on_submit(doc, method=None):
	recompute_vehicle(doc.vehicle)


def vehicle_expense_on_cancel(doc, method=None):
	recompute_vehicle(doc.vehicle)


def vehicle_on_validate(doc, method=None):
	compute_vehicle_costs(doc)

	if not doc.stock_id:
		doc.stock_id = doc.name

	if not doc.mileage:
		doc.mileage = doc.last_odometer


def on_trade_in(doc):
	"""Trade-in vehicle management: the customer's vehicle enters our stock."""
	trade_in = doc.trade_in_vehicle
	if not frappe.db.exists("Vehicle", trade_in):
		frappe.msgprint(
			_("Trade-in vehicle {0} does not exist, so no trade-in valuation was recorded.").format(
				frappe.bold(trade_in)
			),
			alert=True,
			indicator="orange",
		)
		return

	set_vehicle_status(
		trade_in,
		"Ready for Sale",
		doc.doctype,
		doc.name,
		_("Taken in as trade-in against {0}").format(doc.name),
		extra={
			"purchase_price": flt(doc.trade_in_value),
			"purchase_date": doc.posting_date,
			"purchase_receipt": doc.name,
			"purchase_document_type": doc.doctype,
			"customer": doc.customer,
			"supplier": None,
			"seller_name": doc.customer_name or doc.customer,
		},
	)
	recompute_vehicle(trade_in)


def get_vehicle_for_reservation(doc):
	"""Vehicle the reservation belongs to.

	Prefer the Sales Order line's explicit vehicle, then the serial(s) actually
	reserved. Never fall back to another row's serial.
	"""
	if doc.get("vehicle"):
		return doc.vehicle

	if doc.get("voucher_detail_no"):
		vehicle = (
			frappe.db.get_value("Sales Order Item", doc.voucher_detail_no, "vehicle")
			if doc.get("voucher_type") == "Sales Order"
			else None
		)
		if vehicle:
			return vehicle

	serials = [e.serial_no for e in (doc.get("sb_entries") or []) if e.serial_no]
	if not serials:
		return None

	for serial_no in serials:
		vehicle = get_vehicle_for_serial(serial_no)
		if vehicle:
			return vehicle

	return None


def has_open_reservation(vehicle):
	return bool(
		frappe.get_all(
			"Stock Reservation Entry",
			filters={
				"vehicle": vehicle,
				"docstatus": 1,
				"status": ("not in", ["Delivered", "Cancelled"]),
			},
			limit=1,
		)
	)


def get_fuel_type(item_code):
	fuel_type = frappe.get_cached_value("Item", item_code, "alf_fuel_type")
	return fuel_type if fuel_type in FUEL_TYPES else "Petrol"


VEHICLE_QTY_DOCTYPES = (
	"Purchase Receipt",
	"Purchase Invoice",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
	"Stock Entry",
)


def validate_vehicle_qty(doc, method=None):
	"""One vehicle is one unit - block multi-quantity rows.

	A VIN identifies exactly one physical car, so a row can never cover more
	than one unit. Enter one row per vehicle instead.
	"""
	for row in doc.get("items") or []:
		if not is_vehicle_item(row.item_code):
			continue

		if flt(row.qty) != 1:
			frappe.throw(
				_(
					"Row #{0}: {1} is a vehicle, so Quantity must be 1 (found {2}). Add one row per vehicle."
				).format(row.idx, frappe.bold(row.item_code), frappe.bold(flt(row.qty))),
				title=_("One Vehicle Per Row"),
			)

		if row.get("rejected_qty") and flt(row.rejected_qty) > flt(row.qty):
			frappe.throw(
				_("Row #{0}: Rejected Quantity cannot be greater than the vehicle Quantity.").format(row.idx),
				title=_("One Vehicle Per Row"),
			)


def set_vehicle_dimension(doc, method=None):
	"""Fill the `Vehicle` accounting dimension from each row's VIN.

	ERPNext copies an accounting dimension from the item row into `GL Entry`
	(accounts_controller.get_gl_dict), so setting `row.vehicle` is enough to make
	every stock and sales posting carry the vehicle. Rows whose VIN has no
	Vehicle yet (a fresh Purchase Receipt) keep it blank - the dimension is
	optional.
	"""
	meta = frappe.get_meta(f"{doc.doctype} Item")
	if "vehicle" not in {df.fieldname for df in meta.fields}:
		return

	vehicles = {row.vehicle for row in doc.get("items") or [] if row.get("vehicle")}

	for row in doc.get("items") or []:
		if row.get("vehicle"):
			continue

		vin = get_serial_no_for_row(row) or row.get("vin")
		if not vin:
			continue

		vehicle = get_vehicle_for_serial(vin)
		if vehicle:
			row.vehicle = vehicle
			vehicles.add(vehicle)

	# Header dimension covers the non-item Profit and Loss lines (taxes, round off).
	if len(vehicles) == 1 and "vehicle" in {df.fieldname for df in frappe.get_meta(doc.doctype).fields}:
		doc.vehicle = next(iter(vehicles))


def accounting_dimension_on_validate(doc, method=None):
	"""Vehicle must be tagged on every Profit and Loss posting.

	`mandatory_for_pl = 1` forces a vehicle on every expense / income GL line, so
	no cost can be posted without saying which vehicle it belongs to.

	`mandatory_for_bs` stays 0 on purpose: Balance Sheet lines such as Debtors,
	Creditors and Cash belong to the party or the bank, not to a vehicle, and
	making them mandatory blocks every invoice and payment.
	"""
	if doc.get("fieldname") != "vehicle":
		return

	if doc.get("dimension_defaults"):
		for row in doc.get("dimension_defaults"):
			row.mandatory_for_pl = 1
			row.mandatory_for_bs = 0
	else:
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)
		if company:
			doc.append("dimension_defaults", {"company": company, "mandatory_for_pl": 1})


def item_validate(doc, method=None):
	"""A vehicle item is identified by its VIN, so it has to be serial tracked.

	`is_vehicle_item` decides whether a document row is a vehicle from the item
	group plus `has_serial_no`. Creating a vehicle item without ticking
	"Has Serial No" silently opts that car out of the whole lifecycle, so the
	flag is enforced here instead of trusting the form.
	"""
	group = frappe.db.get_single_value("Stock Settings", "vehicle_item_group") or "Vehicles"

	if doc.get("item_group") != group or cint(doc.get("has_serial_no")):
		return

	doc.has_serial_no = 1
	frappe.msgprint(
		_("Item {0} belongs to the {1} item group, so it is serial tracked. Serial No = VIN.").format(
			frappe.bold(doc.get("item_code") or doc.get("item_name")), frappe.bold(group)
		),
		alert=True,
		indicator="blue",
	)
