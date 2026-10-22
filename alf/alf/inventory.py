"""Helpers shared by the vehicle lifecycle hooks, reports and patches."""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, nowdate

VEHICLE_STATUSES = ("Purchased", "In Repair", "Ready for Sale", "Parked", "Reserved", "Delivered", "Sold")

AVAILABLE_STATUSES = ("Purchased", "In Repair", "Ready for Sale", "Parked")

VEHICLE_ITEM_GROUP = "Vehicles"


def get_vehicle_item_group():
	return frappe.db.get_single_value("Stock Settings", "vehicle_item_group") or VEHICLE_ITEM_GROUP


def get_vehicle_item_group_candidates(extra_item_codes=None):
	"""Serial tracked items already used as vehicles on an existing document.

	Only items that a Vehicle or a receipt line already references are returned,
	so unrelated serial tracked stock is never pulled into the Vehicle Item Group.
	"""
	codes = set(code for code in (extra_item_codes or []) if code)

	for doctype, field in (
		("Vehicle", "item_code"),
		("Purchase Receipt Item", "item_code"),
		("Sales Invoice Item", "item_code"),
	):
		if not frappe.db.has_column(doctype, field):
			continue
		codes.update(
			code for code in frappe.get_all(doctype, filters={field: ("is", "set")}, pluck=field) if code
		)

	group = get_vehicle_item_group()
	return sorted(
		row.name
		for row in frappe.get_all(
			"Item",
			filters={"name": ("in", list(codes)), "item_group": ("!=", group), "has_serial_no": 1},
			fields=["name"],
		)
	)


def is_vehicle_item(item_code):
	if not item_code:
		return False

	item = frappe.db.get_value("Item", item_code, ["item_group", "has_serial_no"], as_dict=True)
	if not item:
		return False

	return bool(cint(item.has_serial_no)) and item.item_group == get_vehicle_item_group()


def get_vehicle_for_serial(serial_no):
	if not serial_no:
		return None

	return frappe.db.get_value("Vehicle", {"serial_no": serial_no}, "name")


def set_vehicle_status(vehicle_name, status, voucher_type=None, voucher_no=None, remarks=None, extra=None):
	"""Sets the vehicle status and appends a row to its status history."""
	if not vehicle_name or not frappe.db.exists("Vehicle", vehicle_name):
		return

	vehicle = frappe.get_doc("Vehicle", vehicle_name)
	previous_status = vehicle.status

	vehicle.update({"status": status, **(extra or {})})
	if previous_status != status:
		vehicle.append(
			"status_history",
			{
				"status": status,
				"posting_datetime": now_datetime(),
				"voucher_type": voucher_type,
				"voucher_no": voucher_no,
				"vehicle_reference": vehicle.name,
				"remarks": remarks,
			},
		)

	vehicle.flags.ignore_permissions = True
	vehicle.save(ignore_permissions=True)
	return status


def append_status_log(vehicle, status, voucher_type=None, voucher_no=None, remarks=None):
	vehicle.append(
		"status_history",
		{
			"status": status,
			"posting_datetime": now_datetime(),
			"voucher_type": voucher_type,
			"voucher_no": voucher_no,
			"vehicle_reference": vehicle.name,
			"remarks": remarks,
		},
	)
	vehicle.flags.ignore_permissions = True
	vehicle.save(ignore_permissions=True)


def set_parking(vehicle_name, warehouse=None, from_date=None):
	if not vehicle_name or not frappe.db.exists("Vehicle", vehicle_name):
		return

	frappe.db.set_value(
		"Vehicle",
		vehicle_name,
		{"parking_location": warehouse, "parking_from": from_date or getdate(nowdate())},
		update_modified=False,
	)


def compute_vehicle_costs(vehicle):
	"""Profit Calculation: purchase price + expenses vs actual selling price."""
	expenses = frappe.db.sql(
		"""
		select
			sum(case when ifnull(vet.expense_category, 'Other') = 'Repair & Parts'
					then ve.amount else 0 end) as repair_cost,
			sum(case when ifnull(vet.expense_category, 'Other') != 'Repair & Parts'
					then ve.amount else 0 end) as other_expense
		from `tabVehicle Expense` ve
		left join `tabVehicle Expense Type` vet on vet.name = ve.expense_type
		where ve.docstatus = 1 and ve.vehicle = %s
		""",
		vehicle.name,
		as_dict=True,
	)[0]

	vehicle.repair_cost = flt(expenses.repair_cost)
	vehicle.other_expense = flt(expenses.other_expense)
	vehicle.total_expense = flt(expenses.repair_cost) + flt(expenses.other_expense)
	vehicle.total_cost = flt(vehicle.purchase_price) + flt(vehicle.total_expense)

	vehicle.gross_profit = (
		flt(vehicle.selling_price) - flt(vehicle.total_cost) if flt(vehicle.selling_price) else 0.0
	)
	vehicle.profit_percent = (
		flt(vehicle.gross_profit) / flt(vehicle.selling_price, 2) * 100 if flt(vehicle.selling_price) else 0.0
	)

	return vehicle


def recompute_vehicle(vehicle_name):
	if not vehicle_name or not frappe.db.exists("Vehicle", vehicle_name):
		return

	vehicle = frappe.get_doc("Vehicle", vehicle_name)
	compute_vehicle_costs(vehicle)
	frappe.db.set_value(
		"Vehicle",
		vehicle_name,
		{
			"repair_cost": vehicle.repair_cost,
			"other_expense": vehicle.other_expense,
			"total_expense": vehicle.total_expense,
			"total_cost": vehicle.total_cost,
			"gross_profit": vehicle.gross_profit,
			"profit_percent": vehicle.profit_percent,
		},
		update_modified=False,
	)


def get_open_reservation_for_vehicle(vehicle_name):
	if not vehicle_name:
		return None

	entries = frappe.get_all(
		"Stock Reservation Entry",
		filters={
			"vehicle": vehicle_name,
			"docstatus": 1,
			"status": ("not in", ["Delivered", "Cancelled"]),
		},
		pluck="name",
	)
	return entries[0] if entries else None


def get_serial_nos(row):
	serial_nos = []

	if row.get("serial_and_batch_bundle"):
		serial_nos = frappe.get_all(
			"Serial and Batch Entry",
			filters={
				"parent": row.serial_and_batch_bundle,
				"parenttype": "Serial and Batch Bundle",
				"serial_no": ("is", "set"),
			},
			pluck="serial_no",
			order_by="idx",
		)
	elif row.get("serial_no"):
		serial_nos = [sn.strip() for sn in str(row.serial_no).replace(",", "\n").split("\n") if sn.strip()]

	return serial_nos


def get_serial_no_for_row(row):
	serial_nos = get_serial_nos(row)
	return serial_nos[0] if len(serial_nos) == 1 else None


def get_vehicle_item():
	"""First serial-tracked item belonging to the vehicle item group."""
	item_group = get_vehicle_item_group()
	items = frappe.get_all(
		"Item",
		filters={"item_group": item_group, "has_serial_no": 1, "is_stock_item": 1, "disabled": 0},
		pluck="name",
		limit=1,
	)
	return items[0] if items else None


def vehicle_label(vehicle_name):
	vehicle = frappe.db.get_value(
		"Vehicle", vehicle_name, ["license_plate", "make", "model", "vin"], as_dict=True
	)
	if not vehicle:
		return vehicle_name

	label = " ".join(part for part in (vehicle.make, vehicle.model) if part)
	return f"{vehicle_name} - {label} ({vehicle.vin or vehicle.license_plate})"


def get_company_warehouse(company):
	warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
	return warehouse


def throw_status_error(vehicle, expected):
	frappe.throw(
		_("Vehicle {0} is in status {1}, expected {2}.").format(
			frappe.bold(vehicle), frappe.bold(frappe.db.get_value("Vehicle", vehicle, "status")), expected
		)
	)
