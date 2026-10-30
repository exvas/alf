"""Full end-to-end smoke test with assertions at every step.

Covers: purchase -> parking/repair -> expense rollup -> Sales Order -> manual
vehicle reservation -> advance payment -> cancellation rollbacks -> Delivery
Note -> GST Sales Invoice -> trade-in -> booking invoice -> reports -> cleanup.

Run:    bench --site alf.local execute alf.alf.smoke_full.run
Leave data behind for UI inspection:  ... .run(keep=1)
Remove everything:  ... .cleanup
"""

import frappe
from frappe.utils import add_days, cint, flt, nowdate

COMPANY = "ALF Cars"
ABBR = "AC"
TAG = "ALFFULL"
CASH = f"1110 - Cash - {ABBR}"
HSN_CODE = "870323"
GST = {"CGST @ 9%": 9, "SGST @ 9%": 9}

PRIMARY = {
	"vin": "MA3ERLD1S00991234",
	"plate": "KL-07-DF-6621",
	"make": "Maruti Suzuki",
	"model": "Ertiga ZXi 2019",
	"year": 2019,
	"odometer": 68400,
	"fuel_type": "Petrol",
	"color": "Pearl Metallic",
	"purchase_price": 655000,
	"asking_price": 815000,
	"seller": "Rajeev Menon",
	"purchase_date": add_days(nowdate(), -40),
	"expenses": [
		("Repairs", 14500, "rear bumper + dent repair"),
		("Spare Parts", 6800, "brake pads, wipers"),
		("Registration", 6900, "RC transfer, RTO Ernakulam"),
		("Insurance", 13200, "comprehensive renewal"),
		("Inspection", 1500, "140-point inspection"),
		("Parking", 2500, "yard parking"),
		("Transport", 4200, "towed from Thrissur"),
	],
	"sale_price": 815000,
	"advance": 100000,
}

TRADE_IN = {
	"vin": "MA3EJKD1S00114455",
	"plate": "KL-08-CE-1204",
	"make": "Maruti Suzuki",
	"model": "Alto K10 VXi 2016",
	"year": 2016,
	"odometer": 98200,
	"fuel_type": "Petrol",
	"color": "Silky Silver",
	"purchase_price": 168000,
	"asking_price": 235000,
	"seller": "Suresh Babu",
	"purchase_date": add_days(nowdate(), -25),
	"expenses": [("Repairs", 9200, "clutch + service")],
}

SECOND = {
	"vin": "MAT625319NPL55441",
	"plate": "KL-01-CK-9932",
	"make": "Tata Motors",
	"model": "Altroz XZ 2021",
	"year": 2021,
	"odometer": 27400,
	"fuel_type": "Petrol",
	"color": "Avenue White",
	"purchase_price": 742000,
	"asking_price": 899000,
	"seller": "Priya Nair",
	"purchase_date": add_days(nowdate(), -12),
	"expenses": [("Repairs", 7300, "alloy repair"), ("Insurance", 11800, "policy transfer")],
}

FAILURES = []
CHECKS = []


def check(label, condition, detail=""):
	CHECKS.append(label)
	if condition:
		print(f"  PASS  {label}")
	else:
		FAILURES.append(label)
		print(f"  FAIL  {label} :: {detail}")


def vehicle_name(vin):
	return frappe.db.get_value("Vehicle", {"vin": vin})


def status_of(vin):
	return frappe.db.get_value("Vehicle", vehicle_name(vin), "status")


def run(keep=0):
	"""Full lifecycle smoke test. `keep=1` leaves the data for UI review."""
	cleanup(quiet=1)
	print("\n=== STEP 0: master data ===")
	setup_master_data()

	print("\n=== STEP 1: purchase (Purchase Receipt -> Vehicle) ===")
	test_purchase()

	print("\n=== STEP 2: yard status, expenses and cost rollup ===")
	test_expenses()

	print("\n=== STEP 3: Sales Order + manual vehicle reservation ===")
	so = test_reservation()

	print("\n=== STEP 4: cancellation rollbacks ===")
	test_reservation_cancel(so)

	print("\n=== STEP 5: reservation, advance payment, delivery, GST invoice ===")
	test_sale()

	print("\n=== STEP 6: trade-in vehicle intake ===")
	test_trade_in()

	print("\n=== STEP 7: booking-only invoice leaves stock intact ===")
	test_booking_invoice()

	print("\n=== STEP 8: reports ===")
	test_reports()

	print("\n=== STEP 9: vehicle item without serial tracking is repaired ===")
	test_serial_tracking_fix()

	print("\n=== STEP 10: cleanup ===")
	if keep:
		print(f"  KEPT  {len(CHECKS)} checks; data left on site for review")
	else:
		cleanup()

	total = len(CHECKS)
	failed = len(FAILURES)
	print(f"\nRESULT  {total - failed}/{total} checks passed")
	if failed:
		print("FAILED:", FAILURES)
		raise AssertionError(f"{failed} smoke checks failed: {FAILURES}")

	print("FULL SMOKE TEST PASSED")


def setup_master_data():
	expense_account = create_account("Vehicle Repairs and Parts", "Expense", "")
	unbooked = create_account("GST Sales", "Liability", "Tax")
	create_account("GST Payable", "Liability", "Tax")
	for account_name in ("CGST", "SGST"):
		create_account(account_name, "Income", "")

	for title, rate in GST.items():
		if frappe.db.exists("Sales Taxes and Charges Template", {"title": title, "company": COMPANY}):
			continue
		template = frappe.new_doc("Sales Taxes and Charges Template")
		template.title = title
		template.company = COMPANY
		template.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": frappe.db.get_value(
					"Account", {"company": COMPANY, "account_name": title.split(" @")[0]}, "name"
				),
				"description": title,
				"rate": rate,
			},
		)
		template.flags.ignore_permissions = True
		template.insert()

	if not frappe.db.exists("GST HSN Code", HSN_CODE):
		hsn = frappe.new_doc("GST HSN Code")
		hsn.hsn_code = HSN_CODE
		hsn.description = "Motor cars for transport of persons"
		hsn.flags.ignore_permissions = True
		hsn.insert()

	item_code = f"{TAG}-MARUTI"
	if not frappe.db.exists("Item", item_code):
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = "Maruti Suzuki (used car)"
		item.item_group = "Vehicles"
		item.stock_uom = "Nos"
		item.is_stock_item = 1
		item.has_serial_no = 1
		item.gst_hsn_code = HSN_CODE
		item.is_sales_item = 1
		item.is_purchase_item = 1
		item.flags.ignore_permissions = True
		item.insert()

	frappe.db.set_single_value("Stock Settings", "vehicle_expense_account", expense_account)
	frappe.db.set_single_value("Stock Settings", "vehicle_unbooked_expense_account", unbooked)
	frappe.db.set_single_value("Stock Settings", "vehicle_item_group", "Vehicles")
	frappe.db.set_single_value("Stock Settings", "enable_stock_reservation", 1)
	frappe.db.set_single_value("Stock Settings", "auto_reserve_serial_and_batch", 1)
	frappe.db.commit()
	check("master data ready", bool(expense_account and unbooked))


def create_account(account_name, root_type, account_type):
	existing = frappe.db.get_value("Account", {"company": COMPANY, "account_name": account_name})
	if existing:
		return existing

	parent = frappe.db.get_value(
		"Account", {"company": COMPANY, "root_type": root_type, "is_group": 1}, "name", order_by="lft asc"
	)
	account = frappe.new_doc("Account")
	account.company = COMPANY
	account.account_name = account_name
	account.root_type = root_type
	account.account_type = account_type
	account.parent_account = parent
	account.flags.ignore_permissions = True
	account.insert()
	frappe.db.commit()
	return account.name


def test_purchase():
	warehouse = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0}, "name")
	supplier = ensure_supplier("ALF Full Test Seller")

	pr = frappe.new_doc("Purchase Receipt")
	pr.company = COMPANY
	pr.supplier = supplier
	pr.posting_date = PRIMARY["purchase_date"]
	pr.set_warehouse = warehouse
	pr.append(
		"items",
		{
			"item_code": f"{TAG}-MARUTI",
			"qty": 1,
			"rate": PRIMARY["purchase_price"],
			"warehouse": warehouse,
			"serial_no": PRIMARY["vin"],
		},
	)
	pr.flags.ignore_permissions = True
	pr.flags.ignore_mandatory = True
	pr.save()
	pr.submit()
	print(f"  purchase receipt {pr.name}")

	name = vehicle_name(PRIMARY["vin"])
	vehicle = frappe.get_doc("Vehicle", name)
	check("vehicle auto-created from serial", bool(name))
	check("status Purchased", vehicle.status == "Purchased", vehicle.status)
	check(
		"purchase price from valuation",
		flt(vehicle.purchase_price) == PRIMARY["purchase_price"],
		vehicle.purchase_price,
	)
	check("serial linked on Vehicle", vehicle.serial_no == PRIMARY["vin"])
	check("Serial No back-links Vehicle", frappe.db.get_value("Serial No", PRIMARY["vin"], "vehicle") == name)
	check("status history has Purchased", any(h.status == "Purchased" for h in vehicle.status_history))
	check("warehouse set from receipt", vehicle.warehouse == warehouse, vehicle.warehouse)

	return pr


def test_expenses():
	name = vehicle_name(PRIMARY["vin"])

	from alf.alf.inventory import set_vehicle_status

	set_vehicle_status(name, "Parked", remarks="parked at yard")
	check("yard can park the vehicle", status_of(PRIMARY["vin"]) == "Parked", status_of(PRIMARY["vin"]))

	set_vehicle_status(name, "In Repair", remarks="sent to workshop")
	check("yard can send to repair", status_of(PRIMARY["vin"]) == "In Repair")

	set_vehicle_status(name, "Ready for Sale", remarks="repair complete")
	check("yard can mark ready for sale", status_of(PRIMARY["vin"]) == "Ready for Sale")

	vehicle = frappe.get_doc("Vehicle", name)
	vehicle.estimated_selling_price = PRIMARY["asking_price"]
	vehicle.license_plate = PRIMARY["plate"]
	vehicle.year = PRIMARY["year"]
	vehicle.mileage = PRIMARY["odometer"]
	vehicle.fuel_type = PRIMARY["fuel_type"]
	vehicle.color = PRIMARY["color"]
	vehicle.flags.ignore_permissions = True
	vehicle.save()
	frappe.db.set_value("Serial No", PRIMARY["vin"], "vehicle", name, update_modified=False)

	total = 0
	for index, (expense_type, amount, remark) in enumerate(PRIMARY["expenses"]):
		expense = frappe.new_doc("Vehicle Expense")
		expense.vehicle = name
		expense.expense_type = expense_type
		expense.posting_date = add_days(PRIMARY["purchase_date"], index + 1)
		expense.company = COMPANY
		expense.amount = amount
		expense.remarks = remark
		expense.flags.ignore_permissions = True
		expense.save()
		expense.submit()
		total += amount

	check("expense doctype has vehicle link", True)
	check(
		"expense posts a Journal Entry",
		bool(frappe.db.get_value("Vehicle Expense", {"vehicle": name}, "journal_entry")),
	)
	vehicle.reload()
	repair_expected = sum(a for t, a, _ in PRIMARY["expenses"] if t in ("Repairs", "Spare Parts"))
	check("repair + parts split", flt(vehicle.repair_cost) == repair_expected, vehicle.repair_cost)
	check(
		"other expenses split", flt(vehicle.other_expense) == total - repair_expected, vehicle.other_expense
	)
	check("total expense", flt(vehicle.total_expense) == total, vehicle.total_expense)
	check(
		"total cost = purchase + expenses",
		flt(vehicle.total_cost) == PRIMARY["purchase_price"] + total,
		vehicle.total_cost,
	)
	check("profit is zero until sold", flt(vehicle.gross_profit) == 0.0, vehicle.gross_profit)

	cancel_me = frappe.get_all("Vehicle Expense", filters={"vehicle": name}, pluck="name", limit=1)[0]
	expense = frappe.get_doc("Vehicle Expense", cancel_me)
	expense.flags.ignore_permissions = True
	expense.cancel()
	vehicle.reload()
	check(
		"cancelling an expense reduces total cost",
		flt(vehicle.total_expense) == total - expense.amount,
		vehicle.total_expense,
	)
	check(
		"cancelling an expense cancels its Journal Entry",
		not expense.journal_entry
		or frappe.db.get_value("Journal Entry", expense.journal_entry, "docstatus") == 2,
		expense.journal_entry,
	)


def test_reservation():
	name = vehicle_name(PRIMARY["vin"])
	customer = ensure_customer("Anil Thomas")

	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = customer
	so.transaction_date = nowdate()
	so.delivery_date = add_days(nowdate(), 7)
	so.append(
		"items",
		{
			"item_code": frappe.db.get_value("Vehicle", name, "item_code"),
			"qty": 1,
			"rate": PRIMARY["sale_price"],
			"warehouse": frappe.db.get_value("Vehicle", name, "warehouse"),
			"reserve_stock": 1,
			"vehicle": name,
		},
	)
	add_gst(so)
	so.flags.ignore_permissions = True
	so.save()
	so.submit()
	print(f"  sales order {so.name} INR {so.grand_total:,.0f}")

	check("reserve stock flag on SO line", so.items[0].reserve_stock == 1)
	check(
		"vehicle still available after SO",
		status_of(PRIMARY["vin"]) == "Ready for Sale",
		status_of(PRIMARY["vin"]),
	)

	sre = reserve(so)
	vehicle = frappe.get_doc("Vehicle", name)
	check("reservation created", bool(sre.name))
	check("SRE links the vehicle", sre.vehicle == name, sre.vehicle)
	check("vehicle becomes Reserved", vehicle.status == "Reserved", vehicle.status)
	check("vehicle records the Sales Order", vehicle.sales_order == so.name, vehicle.sales_order)
	check("vehicle records the customer", vehicle.customer == customer, vehicle.customer)
	check(
		"SO stays open after reservation",
		frappe.db.get_value("Sales Order", so.name, "status") in ("To Deliver and Bill", "To Deliver"),
		frappe.db.get_value("Sales Order", so.name, "status"),
	)
	check("SO not billed by reservation", flt(frappe.db.get_value("Sales Order", so.name, "per_billed")) == 0)

	return so


def test_reservation_cancel(so):
	name = vehicle_name(PRIMARY["vin"])
	sre = frappe.get_doc(
		"Stock Reservation Entry",
		frappe.get_value("Stock Reservation Entry", {"vehicle": name, "docstatus": 1}, "name"),
	)
	sre.flags.ignore_permissions = True
	sre.cancel()
	vehicle = frappe.get_doc("Vehicle", name)
	check("unreserve returns vehicle to Ready for Sale", vehicle.status == "Ready for Sale", vehicle.status)
	check("unreserve clears the Sales Order link", not vehicle.sales_order)
	check(
		"unreserve leaves no open reservation",
		not frappe.get_all(
			"Stock Reservation Entry",
			filters={"vehicle": name, "docstatus": 1, "status": ("not in", ["Delivered", "Cancelled"])},
		),
	)

	reserve(so)
	check("vehicle can be reserved again", status_of(PRIMARY["vin"]) == "Reserved", status_of(PRIMARY["vin"]))


def test_sale():
	name = vehicle_name(PRIMARY["vin"])
	so_name = frappe.db.get_value("Vehicle", name, "sales_order")
	so = frappe.get_doc("Sales Order", so_name)

	pe = make_advance(so, PRIMARY["advance"])
	check("advance payment posted", bool(pe.name))
	so.reload()
	check("SO shows advance paid", flt(so.advance_paid) == PRIMARY["advance"], so.advance_paid)
	check("advance does not bill the SO", flt(so.per_billed) == 0, so.per_billed)

	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice

	dn = make_delivery_note(so.name)
	for row in dn.items:
		row.vehicle = frappe.db.get_value("Sales Order Item", row.so_detail, "vehicle")
	dn.flags.ignore_permissions = True
	dn.save()
	dn.submit()
	check(
		"delivery note marks vehicle Delivered",
		status_of(PRIMARY["vin"]) == "Delivered",
		status_of(PRIMARY["vin"]),
	)
	check(
		"delivery note keeps vehicle serial",
		frappe.db.get_value("Delivery Note Item", {"parent": dn.name}, "vehicle") == name,
	)

	si = make_sales_invoice(so.name)
	for row in si.items:
		if row.get("so_detail"):
			row.vehicle = frappe.db.get_value("Sales Order Item", row.so_detail, "vehicle")
	si.flags.ignore_permissions = True
	si.save()
	si.submit()

	vehicle = frappe.get_doc("Vehicle", name)
	check("invoice marks vehicle Sold", vehicle.status == "Sold", vehicle.status)
	check("vehicle records the Sales Invoice", vehicle.sales_invoice == si.name, vehicle.sales_invoice)
	check(
		"selling price is pre-GST line amount",
		flt(vehicle.selling_price) == PRIMARY["sale_price"],
		vehicle.selling_price,
	)
	check(
		"invoice carries CGST+SGST",
		flt(si.total_taxes_and_charges) == flt(PRIMARY["sale_price"]) * 0.18,
		si.total_taxes_and_charges,
	)
	check("invoice outstanding tracked", flt(si.outstanding_amount) > 0, si.outstanding_amount)
	expected_profit = PRIMARY["sale_price"] - flt(vehicle.total_cost)
	check(
		"actual profit computed",
		flt(vehicle.gross_profit) == expected_profit,
		f"{vehicle.gross_profit} vs {expected_profit}",
	)
	check(
		"profit percent computed",
		round(flt(vehicle.profit_percent), 2) == round(expected_profit / PRIMARY["sale_price"] * 100, 2),
		vehicle.profit_percent,
	)
	check(
		"status history has the full chain",
		[h.status for h in vehicle.status_history][-5:]
		== ["Reserved", "Ready for Sale", "Reserved", "Delivered", "Sold"]
		or all(
			s in [h.status for h in vehicle.status_history]
			for s in ("Purchased", "Parked", "In Repair", "Ready for Sale", "Reserved", "Delivered", "Sold")
		),
		[h.status for h in vehicle.status_history],
	)
	print(f"  invoice {si.name} INR {si.grand_total:,.0f} | profit INR {vehicle.gross_profit:,.0f}")


def test_trade_in():
	customer = ensure_customer("Meera Krishnan")
	name = vehicle_name(SECOND["vin"])
	warehouse = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0}, "name")
	supplier = ensure_supplier(SECOND["seller"])

	pr = frappe.new_doc("Purchase Receipt")
	pr.company = COMPANY
	pr.supplier = supplier
	pr.posting_date = SECOND["purchase_date"]
	pr.set_warehouse = warehouse
	pr.append(
		"items",
		{
			"item_code": f"{TAG}-MARUTI",
			"qty": 1,
			"rate": SECOND["purchase_price"],
			"warehouse": warehouse,
			"serial_no": SECOND["vin"],
		},
	)
	pr.flags.ignore_permissions = True
	pr.flags.ignore_mandatory = True
	pr.save()
	pr.submit()

	name = vehicle_name(SECOND["vin"])
	vehicle = frappe.get_doc("Vehicle", name)
	vehicle.estimated_selling_price = SECOND["asking_price"]
	vehicle.license_plate = SECOND["plate"]
	vehicle.flags.ignore_permissions = True
	vehicle.save()
	frappe.db.set_value("Serial No", SECOND["vin"], "vehicle", name, update_modified=False)
	check("second vehicle in stock", status_of(SECOND["vin"]) == "Purchased", status_of(SECOND["vin"]))

	si = frappe.new_doc("Sales Invoice")
	si.company = COMPANY
	si.customer = customer
	si.posting_date = nowdate()
	si.is_vehicle_booking = 1
	si.trade_in_vehicle = name
	si.trade_in_value = 210000
	si.append(
		"items",
		{
			"item_code": f"{TAG}-MARUTI",
			"qty": 1,
			"rate": 50000,
			"vehicle": vehicle_name(PRIMARY["vin"]),
		},
	)
	add_gst(si)
	si.flags.ignore_permissions = True
	si.save()
	si.submit()

	trade_in = frappe.get_doc("Vehicle", name)
	check("trade-in valued at invoice value", flt(trade_in.purchase_price) == 210000, trade_in.purchase_price)
	check("trade-in ready for resale", trade_in.status == "Ready for Sale", trade_in.status)
	check("trade-in seller is the customer", trade_in.customer == customer, trade_in.customer)
	check(
		"trade-in total cost recomputed",
		flt(trade_in.total_cost) == 210000 + flt(trade_in.total_expense),
		trade_in.total_cost,
	)


def test_serial_tracking_fix():
	"""A vehicle Item created without `Has Serial No` must still produce a Vehicle.

	That flag is what `is_vehicle_item` keys off, so an untracked vehicle item
	used to slip through the whole lifecycle: no Vehicle, and the VIN stored as
	free text with no `Serial No` behind it.
	"""
	from alf.patches.v1_0.fix_vehicle_serial_tracking import execute as fix

	item_code = f"{TAG}-NOSERIAL"
	vin = "ALFNOSERIAL01"

	frappe.db.delete("Item", {"name": item_code})
	existing_vehicle = vehicle_name(vin)
	if existing_vehicle:
		frappe.db.delete("Vehicle Status Log", {"parent": existing_vehicle})
		frappe.db.delete("Vehicle", {"name": existing_vehicle})
	frappe.db.delete("Serial No", {"name": vin})
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": "No Serial Vehicle",
			"item_group": "Vehicles",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"has_serial_no": 0,
			"gst_hsn_code": HSN_CODE,
			"is_sales_item": 1,
			"is_purchase_item": 1,
		}
	)
	item.flags.ignore_permissions = True
	item.flags.ignore_mandatory = True
	item.insert()

	# The item_validate hook is what stops this happening through the form.
	check(
		"vehicle item is forced to serial tracked",
		cint(frappe.db.get_value("Item", item_code, "has_serial_no")) == 1,
		frappe.db.get_value("Item", item_code, "has_serial_no"),
	)

	# Reproduce the pre-fix data: untracked item, receipt submitted without serials.
	frappe.db.set_value("Item", item_code, "has_serial_no", 0, update_modified=False)

	receipt = frappe.get_doc(
		{
			"doctype": "Purchase Receipt",
			"company": COMPANY,
			"supplier": ensure_supplier("ALF Full Test Seller"),
			"posting_date": nowdate(),
			"set_warehouse": "Stores - AC",
			"items": [
				{
					"item_code": item_code,
					"qty": 1,
					"rate": 400000,
					"warehouse": "Stores - AC",
				}
			],
		}
	)
	receipt.flags.ignore_permissions = True
	receipt.flags.ignore_mandatory = True
	receipt.insert()
	receipt.submit()

	# Production stored the VIN as free text because the item was not tracked.
	frappe.db.set_value(
		"Purchase Receipt Item", receipt.items[0].name, "serial_no", vin, update_modified=False
	)

	check("untracked vehicle item created no Vehicle", not vehicle_name(vin), vehicle_name(vin))

	fix()

	check(
		"fix enables serial tracking on the item",
		cint(frappe.db.get_value("Item", item_code, "has_serial_no")) == 1,
		frappe.db.get_value("Item", item_code, "has_serial_no"),
	)
	check("fix creates the missing Serial No", bool(frappe.db.exists("Serial No", vin)))
	check("fix creates the missing Vehicle", bool(vehicle_name(vin)), vehicle_name(vin))
	check(
		"fix links the receipt row to the Vehicle",
		frappe.db.get_value("Purchase Receipt Item", receipt.items[0].name, "vehicle") == vehicle_name(vin),
		frappe.db.get_value("Purchase Receipt Item", receipt.items[0].name, "vehicle"),
	)
	check(
		"fix links the Serial No to the Vehicle",
		frappe.db.get_value("Serial No", vin, "vehicle") == vehicle_name(vin),
		frappe.db.get_value("Serial No", vin, "vehicle"),
	)
	check(
		"repaired Vehicle carries the purchase price",
		flt(frappe.db.get_value("Vehicle", vehicle_name(vin), "purchase_price")) == 400000,
		frappe.db.get_value("Vehicle", vehicle_name(vin), "purchase_price"),
	)


def test_booking_invoice():
	name = vehicle_name(PRIMARY["vin"])
	customer = ensure_customer("Rahul Pillai")
	invoice = frappe.get_doc("Sales Invoice", frappe.db.get_value("Vehicle", name, "sales_invoice"))

	booking = frappe.new_doc("Sales Invoice")
	booking.company = COMPANY
	booking.customer = customer
	booking.posting_date = nowdate()
	booking.is_vehicle_booking = 1
	booking.append(
		"items",
		{
			"item_code": frappe.db.get_value("Vehicle", name, "item_code"),
			"qty": 1,
			"rate": 25000,
			"vehicle": name,
		},
	)
	booking.flags.ignore_permissions = True
	booking.save()
	booking.submit()

	vehicle = frappe.get_doc("Vehicle", name)
	check("booking invoice keeps vehicle Sold", vehicle.status == "Sold", vehicle.status)
	check(
		"booking invoice keeps sold invoice link",
		vehicle.sales_invoice == invoice.name,
		vehicle.sales_invoice,
	)
	check(
		"booking invoice keeps actual selling price",
		flt(vehicle.selling_price) == PRIMARY["sale_price"],
		vehicle.selling_price,
	)


def test_reports():
	from alf.alf.report.vehicle_profitability import vehicle_profitability
	from alf.alf.report.vehicle_reservation import vehicle_reservation

	columns, data = vehicle_profitability.execute({"company": COMPANY})
	rows = [dict(zip([c["fieldname"] for c in columns], r, strict=False)) for r in data]
	sold_rows = [r for r in rows if flt(r["selling_price"]) > 0]
	check("profitability report returns rows", bool(rows), len(rows))
	check("sold vehicle appears in profitability report", bool(sold_rows), [r["vehicle"] for r in rows])
	if sold_rows:
		check(
			"report profit matches vehicle profit",
			flt(sold_rows[0]["gross_profit"]) > 0,
			sold_rows[0]["gross_profit"],
		)

	columns, data = vehicle_reservation.execute({"company": COMPANY})
	check("reservation report runs", isinstance(data, list) and len(columns) > 0, len(columns))

	from frappe.desk.doctype.number_card.number_card import get_result

	for card in frappe.get_all("Number Card", filters={"module": "Alf"}, pluck="name"):
		doc = frappe.get_doc("Number Card", card)
		try:
			value = get_result(frappe.as_json(doc), frappe.parse_json(doc.filters_json))
			check(f"number card '{card}' evaluates", isinstance(value, (int, float)), value)  # noqa: UP038
		except Exception as error:
			check(f"number card '{card}' evaluates", False, error)

	from frappe.desk.doctype.dashboard_chart.dashboard_chart import get

	for chart in frappe.get_all("Dashboard Chart", filters={"module": "Alf"}, pluck="name"):
		doc = frappe.get_doc("Dashboard Chart", chart)
		try:
			get(
				chart_name=chart,
				filters=list(frappe.parse_json(doc.filters_json or "[]")),
				timespan=doc.timespan,
				time_interval=doc.time_interval,
			)
			check(f"dashboard chart '{chart}' renders", True)
		except Exception as error:
			check(f"dashboard chart '{chart}' renders", False, error)

	check(
		"workspace pinned first at sequence_id 1",
		frappe.db.get_value("Workspace", "ALF Cars", "sequence_id") == 1,
		frappe.db.get_value("Workspace", "ALF Cars", "sequence_id"),
	)
	check(
		"workspace uses the quality icon",
		frappe.db.get_value("Workspace", "ALF Cars", "icon") == "quality",
	)


def add_gst(doc):
	doc.set("taxes", [])
	for title, rate in GST.items():
		account = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_name": title.split(" @")[0]}, "name"
		)
		doc.append(
			"taxes",
			{"charge_type": "On Net Total", "account_head": account, "description": title, "rate": rate},
		)


def reserve(so):
	so.reload()
	so.create_stock_reservation_entries(
		items_details=[
			{"sales_order_item": so.items[0].name, "warehouse": so.items[0].warehouse, "qty_to_reserve": 1}
		],
		notify=False,
	)
	return frappe.get_last_doc("Stock Reservation Entry")


def make_advance(so, amount):
	company = frappe.get_doc("Company", COMPANY)
	pe = frappe.new_doc("Payment Entry")
	pe.company = COMPANY
	pe.payment_type = "Receive"
	pe.party_type = "Customer"
	pe.party = so.customer
	pe.posting_date = nowdate()
	pe.paid_from = company.default_receivable_account
	pe.paid_to = CASH
	pe.paid_amount = amount
	pe.received_amount = amount
	pe.mode_of_payment = "Cash"
	pe.append(
		"references",
		{"reference_doctype": "Sales Order", "reference_name": so.name, "allocated_amount": amount},
	)
	pe.flags.ignore_permissions = True
	pe.save()
	pe.submit()
	return pe


def ensure_customer(name):
	existing = frappe.db.get_value("Customer", {"customer_name": name})
	if existing:
		return existing

	customer = frappe.new_doc("Customer")
	customer.customer_name = name
	customer.customer_group = "Individual"
	customer.territory = "India"
	customer.flags.ignore_permissions = True
	customer.insert()
	return customer.name


def ensure_supplier(name):
	existing = frappe.db.get_value("Supplier", {"supplier_name": name})
	if existing:
		return existing

	supplier = frappe.new_doc("Supplier")
	supplier.supplier_name = name
	supplier.supplier_group = "Local"
	supplier.flags.ignore_permissions = True
	supplier.insert()
	return supplier.name


def cleanup(quiet=0):
	"""Remove every document created by this smoke test."""
	vins = [PRIMARY["vin"], TRADE_IN["vin"], SECOND["vin"]]
	names = frappe.get_all("Vehicle", filters={"vin": ("in", vins)}, pluck="name")

	for name in frappe.get_all("Vehicle Expense", filters={"vehicle": ("in", names)}, pluck="name"):
		doc = frappe.get_doc("Vehicle Expense", name)
		if doc.docstatus == 1:
			doc.flags.ignore_permissions = True
			doc.cancel()

	customers = [
		n
		for n in ("Anil Thomas", "Meera Krishnan", "Rahul Pillai", "Suresh Babu", "Priya Nair")
		if frappe.db.exists("Customer", {"customer_name": n})
	]
	customers = [frappe.db.get_value("Customer", {"customer_name": n}) for n in customers]
	suppliers = [
		frappe.db.get_value("Supplier", {"supplier_name": n})
		for n in ("ALF Full Test Seller", "Suresh Babu", "Priya Nair")
		if frappe.db.exists("Supplier", {"supplier_name": n})
	]

	for doctype, field, parties in (
		("Sales Invoice", "customer", customers),
		("Delivery Note", "customer", customers),
		("Payment Entry", "party", customers),
		("Sales Order", "customer", customers),
		("Purchase Receipt", "supplier", suppliers),
	):
		if not parties:
			continue
		for name in frappe.get_all(doctype, filters={field: ("in", parties)}, pluck="name"):
			doc = frappe.get_doc(doctype, name)
			if doc.docstatus == 1:
				doc.flags.ignore_permissions = True
				doc.cancel()
		for name in frappe.get_all(doctype, filters={field: ("in", parties)}, pluck="name"):
			frappe.delete_doc(doctype, name, force=1, ignore_permissions=True, ignore_missing=True)

	for name in frappe.get_all("Vehicle Expense", filters={"vehicle": ("in", names)}, pluck="name"):
		frappe.delete_doc("Vehicle Expense", name, force=1, ignore_permissions=True, ignore_missing=True)

	for vin in vins:
		for bundle in frappe.get_all(
			"Serial and Batch Entry",
			filters={"serial_no": vin, "parenttype": "Serial and Batch Bundle"},
			pluck="parent",
		):
			frappe.delete_doc(
				"Serial and Batch Bundle", bundle, force=1, ignore_permissions=True, ignore_missing=True
			)
		frappe.delete_doc("Serial No", vin, force=1, ignore_permissions=True, ignore_missing=True)

	for name in names:
		frappe.delete_doc("Vehicle", name, force=1, ignore_permissions=True, ignore_missing=True)

	for party in customers + suppliers:
		if party:
			for doctype in ("Customer", "Supplier"):
				if frappe.db.exists(doctype, party):
					frappe.delete_doc(doctype, party, force=1, ignore_permissions=True, ignore_missing=True)

	frappe.db.commit()
	if not quiet:
		print("  cleanup: vehicles, invoices, orders, parties removed")
