"""India secondhand-car smoke test for `alf`.

Creates six realistic vehicles, walks each through the lifecycle
(Purchased -> Parked -> Reserved -> Delivered -> Sold), books the usual
secondhand-car expenses and validates the profit numbers plus both reports.

Run:
    bench --site alf.local execute alf.alf.smoke_india.run

Everything is committed so you can open it in the UI. Remove it with:
    bench --site alf.local execute alf.alf.smoke_india.cleanup
"""

import frappe
from frappe.utils import add_days, flt, nowdate

COMPANY = "ALF Cars"
ABBR = "AC"
TAG = "ALFSMOKE"

VEHICLES = [
	{
		"vin": "MA3EJKD1S00245671",
		"plate": "KL-07-CJ-4821",
		"make": "Maruti Suzuki",
		"model": "Swift VXi 2019",
		"year": 2019,
		"odometer": 48200,
		"fuel_type": "Petrol",
		"color": "Pearl Arctic White",
		"purchase_price": 435000,
		"asking_price": 549000,
		"seller": "Individual",
		"seller_name": "Rajesh Kumar Nair",
		"purchase_date": "2026-08-12",
		"status": "Parked",
		"expenses": [
			("Repairs", 18500, "door ding + bumper touch-up, Muvattupuzha"),
			("Spare Parts", 7800, "new brake pads, wipers, battery terminals"),
			("Registration", 6200, "RC transfer + NOC, RTO Ernakulam"),
			("Insurance", 11400, "comprehensive policy transfer, New India Assurance"),
			("Inspection", 1500, "140-point pre-sale inspection"),
			("Parking", 3000, "yard parking, Aug-Sep"),
		],
	},
	{
		"vin": "MAT596472NPK12345",
		"plate": "KL-01-BA-9188",
		"make": "Tata Motors",
		"model": "Nexon XZ+ 2021",
		"year": 2021,
		"odometer": 31500,
		"fuel_type": "Diesel",
		"color": "Calgary White",
		"purchase_price": 812000,
		"asking_price": 995000,
		"seller": "Individual",
		"seller_name": "Anitha Menon",
		"purchase_date": "2026-09-02",
		"status": "Reserved",
		"expenses": [
			("Repairs", 9500, "clutch adjustment + AC service"),
			("Spare Parts", 4200, "air filter, cabin filter, engine oil"),
			("Registration", 7800, "RC transfer, RTO Trivandrum"),
			("Insurance", 18750, "own damage + third party renewal"),
			("Transport", 6500, "transported from Trivandrum yard"),
		],
	},
	{
		"vin": "MA3FHEB1S00119988",
		"plate": "KL-11-BC-3301",
		"make": "Maruti Suzuki",
		"model": "Ciaz ZXi 2018",
		"year": 2018,
		"odometer": 76000,
		"fuel_type": "Petrol",
		"color": "Nexa Blue",
		"purchase_price": 512000,
		"asking_price": 638000,
		"seller": "Supplier",
		"seller_name": "Kozhikode Auto Traders",
		"purchase_date": "2026-07-21",
		"status": "Sold",
		"expenses": [
			("Repairs", 22400, "front suspension overhaul"),
			("Spare Parts", 13600, "tyres x2, brake discs"),
			("Registration", 6900, "RC transfer + hypothecation removal"),
			("Insurance", 14200, "comprehensive renewal"),
			("Inspection", 1500, "pre-sale inspection"),
			("Parking", 4500, "yard parking, Jul-Aug"),
		],
		"sale": {"customer": "Vineeth Balakrishnan", "price": 690000, "advance": 50000},
	},
	{
		"vin": "MA3EWDE1S00773421",
		"plate": "KL-08-AW-7712",
		"make": "Maruti Suzuki",
		"model": "Baleno Zeta 2020",
		"year": 2020,
		"odometer": 39950,
		"fuel_type": "Petrol",
		"color": "Fire Red",
		"purchase_price": 605000,
		"asking_price": 735000,
		"seller": "Individual",
		"seller_name": "Fathima Beevi",
		"purchase_date": "2026-09-18",
		"status": "Ready for Sale",
		"expenses": [
			("Repairs", 6200, "alloy wheel curb repair"),
			("Spare Parts", 3900, "wiper blades, cabin filter"),
			("Insurance", 12800, "comprehensive renewal"),
		],
	},
	{
		"vin": "MEEA1B012TH045112",
		"plate": "KL-10-CC-2045",
		"make": "Hyundai",
		"model": "i20 Asta 2017",
		"year": 2017,
		"odometer": 92300,
		"fuel_type": "Petrol",
		"color": "Stardust Grey",
		"purchase_price": 398000,
		"asking_price": 499000,
		"seller": "Individual",
		"seller_name": "Thomas Chacko",
		"purchase_date": "2026-08-28",
		"status": "In Repair",
		"expenses": [
			("Repairs", 31500, "gearbox overhaul at workshop"),
			("Spare Parts", 8900, "clutch kit, bearings"),
			("Inspection", 1500, "post-repair inspection"),
		],
	},
	{
		"vin": "MA1TA2MHKJ2M98765",
		"plate": "KL-05-CE-5567",
		"make": "Mahindra",
		"model": "XUV300 W8 2020",
		"year": 2020,
		"odometer": 64200,
		"fuel_type": "Diesel",
		"color": "Aquamarine",
		"purchase_price": 748000,
		"asking_price": 910000,
		"seller": "Customer",
		"seller_name": "Sneha Pillai",
		"purchase_date": "2026-09-25",
		"status": "Parked",
		"expenses": [
			("Repairs", 12400, "dented rear quarter panel"),
			("Spare Parts", 5300, "air cleaner, glow plugs"),
			("Registration", 7100, "RC transfer, RTO Kottayam"),
			("Parking", 2500, "yard parking, Sep-Oct"),
		],
		"trade_in_of": "MA3EWDE1S00773421",
	},
]

EXPENSE_ACCOUNT = f"5204 - Entertainment Expenses - {ABBR}"
BANK_ACCOUNT = f"1110 - Cash - {ABBR}"
GST_TEMPLATES = {"CGST @ 9%": 9, "SGST @ 9%": 9, "IGST @ 18%": 18}


def run():
	"""Runs the full India smoke test and prints a summary."""
	cleanup()
	setup_master_data()

	pr = purchase_all_vehicles()
	print(
		"\nPURCHASE RECEIPT",
		pr.name,
		"|",
		len(VEHICLES),
		"vehicles bought for INR",
		flt(sum(v["purchase_price"] for v in VEHICLES)),
	)

	book_expenses()
	sell_one_vehicle()
	reserve_one_vehicle()

	frappe.db.commit()
	report()


def setup_master_data():
	ensure_expense_and_tax_accounts()
	ensure_item()

	settle_account = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "GST Sales"}, "name")
	settle_account = settle_account or create_account("GST Sales", "Liability", "Tax")
	frappe.db.set_single_value("Stock Settings", "vehicle_expense_account", EXPENSE_ACCOUNT)
	frappe.db.set_single_value("Stock Settings", "vehicle_unbooked_expense_account", settle_account)
	frappe.db.set_single_value("Stock Settings", "vehicle_item_group", "Vehicles")
	frappe.db.set_single_value("Stock Settings", "enable_stock_reservation", 1)
	frappe.db.set_single_value("Stock Settings", "auto_reserve_serial_and_batch", 1)
	frappe.db.commit()
	print("SETTINGS  vehicle_expense_account =", EXPENSE_ACCOUNT, "| unbooked =", settle_account)


def ensure_expense_and_tax_accounts():
	for account_name, root_type, account_type in (
		("Vehicle Repairs and Parts", "Expense", ""),
		("GST Payable", "Liability", "Tax"),
		("GST Sales", "Liability", "Tax"),
	):
		create_account(account_name, root_type, account_type)

	for account_name, root_type in (
		("CGST", "Income"),
		("SGST", "Income"),
		("IGST", "Income"),
	):
		create_account(account_name, root_type, "")

	for title, _rate in GST_TEMPLATES.items():
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
					"Account",
					{"company": COMPANY, "account_name": title.split(" @")[0]},
					"name",
				),
				"description": title,
				"rate": _rate,
			},
		)
		template.flags.ignore_permissions = True
		template.insert()
		print("TAX TEMPLATE", title)


def create_account(account_name, root_type, account_type):
	existing = frappe.db.get_value("Account", {"company": COMPANY, "account_name": account_name}, "name")
	if existing:
		return existing

	parent = frappe.db.get_value(
		"Account",
		{"company": COMPANY, "root_type": root_type, "is_group": 1},
		"name",
		order_by="lft asc",
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
	print("ACCOUNT", account.name)
	return account.name


HSN_CODE = "870323"


def ensure_hsn():
	if frappe.db.exists("GST HSN Code", HSN_CODE):
		return HSN_CODE

	hsn = frappe.new_doc("GST HSN Code")
	hsn.hsn_code = HSN_CODE
	hsn.description = "Motor cars and other motor vehicles for transport of persons"
	hsn.flags.ignore_permissions = True
	hsn.insert()
	print("HSN", HSN_CODE)
	return HSN_CODE


def ensure_item():
	"""One serial-tracked item per make keeps the valuation realistic."""
	ensure_hsn()
	for vehicle in VEHICLES:
		item_code = f"{TAG}-{vehicle['make'].split()[0].upper()}"
		if frappe.db.exists("Item", item_code):
			continue
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = f"{vehicle['make']} (used car)"
		item.item_group = "Vehicles"
		item.stock_uom = "Nos"
		item.is_stock_item = 1
		item.has_serial_no = 1
		item.gst_hsn_code = HSN_CODE
		item.is_sales_item = 1
		item.is_purchase_item = 1
		item.flags.ignore_permissions = True
		item.insert()
		print("ITEM", item_code)


def purchase_all_vehicles():
	"""One Purchase Receipt per seller type, serial No = VIN (real-world habit)."""
	pr_by_seller = {}
	warehouse = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0}, "name")

	for vehicle in VEHICLES:
		seller_type = vehicle["seller"]
		if seller_type == "Supplier":
			party = ensure_party("Supplier", vehicle["seller_name"])
		else:
			vehicle["buyer_party"] = ensure_party("Customer", vehicle["seller_name"])
			party = ensure_supplier(vehicle["seller_name"])
		key = (seller_type, party)
		if key not in pr_by_seller:
			pr = frappe.new_doc("Purchase Receipt")
			pr.company = COMPANY
			pr.supplier = party
			pr.posting_date = vehicle["purchase_date"]
			pr.set_warehouse = warehouse
			pr.supplier_delivery_note = f"{TAG}-{len(pr_by_seller) + 1}"
			pr.flags.ignore_permissions = True
			pr_by_seller[key] = pr

		pr = pr_by_seller[key]
		pr.append(
			"items",
			{
				"item_code": f"{TAG}-{vehicle['make'].split()[0].upper()}",
				"qty": 1,
				"rate": vehicle["purchase_price"],
				"warehouse": warehouse,
				"serial_no": vehicle["vin"],
				"description": f"{vehicle['make']} {vehicle['model']}, {vehicle['year']}, "
				f"{vehicle['odometer']} km, {vehicle['fuel_type']}",
			},
		)

	first_pr = None
	for pr in pr_by_seller.values():
		pr.flags.ignore_mandatory = True
		pr.save()
		pr.submit()
		first_pr = first_pr or pr
		print("PURCHASE RECEIPT", pr.name, "from", pr.supplier)

	for vehicle in VEHICLES:
		update_vehicle_details(vehicle)

	return first_pr


def ensure_supplier(name):
	existing = frappe.db.get_value("Supplier", {"supplier_name": name}, "name")
	if existing:
		return existing

	supplier = frappe.new_doc("Supplier")
	supplier.supplier_name = name
	supplier.supplier_group = "Local"
	supplier.flags.ignore_permissions = True
	supplier.insert()
	return supplier.name


def ensure_party(seller_type, name):
	if seller_type == "Supplier":
		existing = frappe.db.get_value("Supplier", {"supplier_name": name}, "name")
		if existing:
			return existing
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = name
		supplier.supplier_group = "Local"
		supplier.flags.ignore_permissions = True
		supplier.insert()
		return supplier.name

	existing = frappe.db.get_value("Customer", {"customer_name": name}, "name")
	if existing:
		return existing

	customer = frappe.new_doc("Customer")
	customer.customer_name = name
	customer.customer_group = "Individual"
	customer.territory = "India"
	customer.flags.ignore_permissions = True
	customer.insert()
	return customer.name


def update_vehicle_details(vehicle):
	"""Real secondhand data that the Purchase Receipt cannot supply."""
	name = frappe.db.get_value("Vehicle", {"serial_no": vehicle["vin"]})
	doc = frappe.get_doc("Vehicle", name)
	doc.license_plate = vehicle["plate"]
	doc.vin = vehicle["vin"]
	doc.make = vehicle["make"]
	doc.model = vehicle["model"]
	doc.year = vehicle["year"]
	doc.mileage = vehicle["odometer"]
	if doc.last_odometer != vehicle["odometer"]:
		doc.db_set("last_odometer", vehicle["odometer"], update_modified=False)
	doc.fuel_type = vehicle["fuel_type"]
	doc.color = vehicle["color"]
	doc.estimated_selling_price = vehicle["asking_price"]
	doc.parking_location = doc.warehouse
	doc.parking_from = vehicle["purchase_date"]
	if vehicle["seller"] in ("Individual", "Customer"):
		doc.seller_name = vehicle["seller_name"]

	status_changed = doc.status != vehicle["status"] and doc.status not in ("Sold", "Delivered")
	if status_changed:
		doc.status = vehicle["status"]

	from alf.alf.inventory import compute_vehicle_costs

	compute_vehicle_costs(doc)
	doc.flags.ignore_permissions = True
	doc.save()

	if doc.license_plate != vehicle["plate"]:
		# Vehicle is autonamed by license plate: rename from the VIN placeholder.
		frappe.rename_doc("Vehicle", doc.name, vehicle["plate"], force=True, merge=False)
		doc = frappe.get_doc("Vehicle", vehicle["plate"])
	frappe.db.set_value("Serial No", vehicle["vin"], "vehicle", doc.name, update_modified=False)

	if status_changed:
		from alf.alf.inventory import append_status_log

		append_status_log(
			doc,
			vehicle["status"],
			remarks=f"Moved to {vehicle['status']} at the yard",
		)


def book_expenses():
	"""Repairs, parts, RTO, insurance, transport, inspection and parking per vehicle."""
	total = 0
	for vehicle in VEHICLES:
		name = frappe.db.get_value("Vehicle", {"serial_no": vehicle["vin"]})
		for day, (expense_type, amount, remarks) in enumerate(vehicle["expenses"]):
			expense = frappe.new_doc("Vehicle Expense")
			expense.vehicle = name
			expense.expense_type = expense_type
			expense.posting_date = add_days(vehicle["purchase_date"], day + 2)
			expense.company = COMPANY
			expense.amount = amount
			expense.expense_account = EXPENSE_ACCOUNT
			expense.paid_from = BANK_ACCOUNT
			expense.remarks = remarks
			expense.flags.ignore_permissions = True
			expense.save()
			expense.submit()
			total += amount
		print(
			"EXPENSES",
			vehicle["plate"],
			"INR",
			sum(e[1] for e in vehicle["expenses"]),
		)

	print("TOTAL EXPENSES BOOKED INR", total)


def sell_one_vehicle():
	"""Sold car: Sales Order -> reservation -> advance -> delivery -> GST invoice."""
	vehicle = next(v for v in VEHICLES if v["status"] == "Sold")
	name = frappe.db.get_value("Vehicle", {"serial_no": vehicle["vin"]})
	customer = ensure_party("Individual", vehicle["sale"]["customer"])

	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = customer
	so.transaction_date = add_days(vehicle["purchase_date"], 30)
	so.delivery_date = add_days(vehicle["purchase_date"], 35)
	so.append(
		"items",
		{
			"item_code": frappe.db.get_value("Vehicle", name, "item_code"),
			"qty": 1,
			"rate": vehicle["sale"]["price"],
			"warehouse": frappe.db.get_value("Vehicle", name, "warehouse"),
			"reserve_stock": 1,
			"vehicle": name,
		},
	)
	add_gst(so, "CGST @ 9%", "SGST @ 9%")
	so.flags.ignore_permissions = True
	so.save()
	so.submit()
	print(
		"\nSALES ORDER",
		so.name,
		"|",
		vehicle["plate"],
		"| INR",
		so.grand_total,
		"incl. CGST+SGST on",
		so.total_taxes_and_charges,
	)

	sre = reserve(so)
	print(
		"RESERVED",
		sre.name,
		"| vehicle",
		vehicle["plate"],
		"| status",
		frappe.db.get_value("Vehicle", name, "status"),
	)

	advance = make_advance(so, vehicle["sale"]["advance"])
	print(
		"ADVANCE",
		advance.name,
		"| INR",
		advance.paid_amount,
		"| SO advance_paid",
		frappe.db.get_value("Sales Order", so.name, "advance_paid"),
	)

	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice

	dn = make_delivery_note(so.name)
	for row in dn.items:
		row.vehicle = frappe.db.get_value("Sales Order Item", row.so_detail, "vehicle")
	dn.flags.ignore_permissions = True
	dn.save()
	dn.submit()
	print("DELIVERY NOTE", dn.name, "| vehicle status", frappe.db.get_value("Vehicle", name, "status"))

	si = make_sales_invoice(so.name)
	for row in si.items:
		if row.get("so_detail"):
			row.vehicle = frappe.db.get_value("Sales Order Item", row.so_detail, "vehicle")
	si.flags.ignore_permissions = True
	si.save()
	si.submit()

	after = frappe.get_doc("Vehicle", name)
	print(
		"SALES INVOICE",
		si.name,
		"| grand total",
		si.grand_total,
		"| outstanding",
		si.outstanding_amount,
		"| vehicle status",
		after.status,
		"| actual selling price",
		after.selling_price,
	)


def reserve_one_vehicle():
	"""Booked car: reservation stays open so the SO keeps its advance workflow."""
	vehicle = next(v for v in VEHICLES if v["status"] == "Reserved")
	name = frappe.db.get_value("Vehicle", {"serial_no": vehicle["vin"]})
	customer = ensure_party("Individual", "Deepak Varma")

	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = customer
	so.transaction_date = add_days(vehicle["purchase_date"], 12)
	so.delivery_date = add_days(nowdate(), 10)
	so.append(
		"items",
		{
			"item_code": frappe.db.get_value("Vehicle", name, "item_code"),
			"qty": 1,
			"rate": vehicle["asking_price"],
			"warehouse": frappe.db.get_value("Vehicle", name, "warehouse"),
			"reserve_stock": 1,
			"vehicle": name,
		},
	)
	add_gst(so, "CGST @ 9%", "SGST @ 9%")
	so.flags.ignore_permissions = True
	so.save()
	so.submit()

	sre = reserve(so)
	advance = make_advance(so, 100000)
	print(
		"\nBOOKED",
		vehicle["plate"],
		"| SO",
		so.name,
		"| reservation",
		sre.name,
		"| advance",
		advance.paid_amount,
		"| vehicle status",
		frappe.db.get_value("Vehicle", name, "status"),
	)


def add_gst(doc, *templates):
	rates = {t: GST_TEMPLATES[t] for t in templates if t in GST_TEMPLATES}
	if not rates:
		return
	doc.set("taxes", [])
	for title, rate in rates.items():
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
	pe.posting_date = so.transaction_date
	pe.paid_from = company.default_receivable_account
	pe.paid_to = BANK_ACCOUNT
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


def report():
	from alf.alf.report.vehicle_profitability import vehicle_profitability
	from alf.alf.report.vehicle_reservation import vehicle_reservation

	filters = {"company": COMPANY}
	print("\n=== VEHICLE STOCK (India secondhand) ===")
	print(f"{'Plate':<18}{'Vehicle':<32}{'Status':<16}{'Cost':>12}{'Asking':>12}{'Expense':>10}")
	for vehicle in VEHICLES:
		name = frappe.db.get_value("Vehicle", {"serial_no": vehicle["vin"]})
		doc = frappe.get_doc("Vehicle", name)
		print(
			f"{doc.license_plate:<18}{(doc.make + ' ' + doc.model)[:30]:<32}{doc.status:<16}"
			f"{doc.total_cost:>12,.0f}{doc.estimated_selling_price:>12,.0f}{doc.total_expense:>10,.0f}"
		)

	columns, data = vehicle_profitability.execute(filters)
	print("\n=== VEHICLE PROFITABILITY REPORT ===")
	print(f"{'Plate':<18}{'Status':<16}{'Cost':>12}{'Sold':>12}{'Profit':>12}{'Margin':>9}")
	sold_margin = 0
	profit_rows = []
	for raw in data:
		record = dict(zip([c["fieldname"] for c in columns], raw, strict=False))
		plate = frappe.db.get_value("Vehicle", record["vehicle"], "license_plate")
		profit_rows.append(record)
		print(
			f"{plate:<18}{record['status']:<16}{flt(record['total_cost']):>12,.0f}"
			f"{flt(record['selling_price']):>12,.0f}{flt(record['gross_profit']):>12,.0f}"
			f"{flt(record['profit_percent']):>8.2f}%"
		)
		if record["status"] == "Sold":
			sold_margin = flt(record["gross_profit"])

	assert sold_margin > 0, "sold vehicle must show a profit"
	assert not any(
		r["status"] == "Sold" and flt(r["selling_price"]) <= 0 for r in profit_rows
	), "sold vehicle must carry its actual selling price"

	columns, data = vehicle_reservation.execute(filters)
	print("\n=== VEHICLE RESERVATION REPORT ===")
	print(f"{'Plate':<18}{'Customer':<26}{'SO':<24}{'Reservation':<26}{'Status':<20}{'Cost':>12}")
	keys = [c["fieldname"] for c in columns]
	assert data, "at least one vehicle must be reserved"
	so = None
	for raw in data:
		record = dict(zip(keys, raw, strict=False))
		plate = frappe.db.get_value("Vehicle", record["vehicle"], "license_plate")
		print(
			f"{plate:<18}{(record['customer'] or '-')[:24]:<26}{record['voucher_no']:<24}"
			f"{record['stock_reservation_entry']:<26}{record['reservation_status']:<20}"
			f"{flt(record['total_cost']):>12,.0f}"
		)
		so = so or record["voucher_no"]
	print(
		"\nSO",
		so,
		"still open: docstatus",
		frappe.db.get_value("Sales Order", so, "docstatus"),
		"| advance paid",
		frappe.db.get_value("Sales Order", so, "advance_paid"),
		"| status",
		frappe.db.get_value("Sales Order", so, "status"),
	)
	print("\nSMOKE TEST PASSED")


def cleanup():
	"""Remove everything created by this smoke test."""
	vins = [v["vin"] for v in VEHICLES]
	names = frappe.get_all("Vehicle", filters={"vin": ("in", vins)}, pluck="name")

	for name in frappe.get_all("Vehicle Expense", filters={"vehicle": ("in", names)}, pluck="name"):
		doc = frappe.get_doc("Vehicle Expense", name)
		if doc.docstatus == 1:
			doc.flags.ignore_permissions = True
			doc.cancel()

	customers = frappe.get_all("Customer", filters={"customer_name": ("like", "ALFSMOKE%")}, pluck="name")
	customers += [
		n
		for n in (
			"Vineeth Balakrishnan",
			"Deepak Varma",
			"Rajesh Kumar Nair",
			"Anitha Menon",
			"Fathima Beevi",
			"Sneha Pillai",
			"Thomas Chacko",
		)
		if frappe.db.exists("Customer", {"customer_name": n})
		and frappe.db.get_value("Customer", {"customer_name": n}, "name") not in customers
	]
	suppliers = ["Kozhikode Auto Traders"] + [v["seller_name"] for v in VEHICLES if v["seller"] != "Supplier"]

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
		if frappe.db.exists("Customer", party):
			frappe.delete_doc("Customer", party, force=1, ignore_permissions=True, ignore_missing=True)
		if frappe.db.exists("Supplier", party):
			frappe.delete_doc("Supplier", party, force=1, ignore_permissions=True, ignore_missing=True)

	for item in frappe.get_all(
		"Item", filters={"item_group": "Vehicles", "name": ("like", f"{TAG}-%")}, pluck="name"
	):
		frappe.delete_doc("Item", item, force=1, ignore_permissions=True, ignore_missing=True)

	frappe.db.commit()
	print("cleanup: smoke vehicles, invoices, parties and items removed")
