import frappe
from frappe.utils import add_days, flt, nowdate

COMPANY = "ALF Cars"


def run():
	frappe.flags.in_test = True
	cleanup()
	try:
		_run_flow()
	finally:
		frappe.db.rollback()
		cleanup()


def _run_flow():
	vins = ["ALFTESTVIN0000001", "ALFTESTVIN0000002"]
	pr = make_purchase_receipt(vins)
	print("1. Purchase Receipt", pr.name, "submitted")

	for vin in vins:
		name = frappe.db.get_value("Vehicle", {"serial_no": vin}, "name")
		vehicle = frappe.get_doc("Vehicle", name)
		print(
			"   Vehicle",
			vehicle.name,
			"| status:",
			vehicle.status,
			"| purchase_price:",
			vehicle.purchase_price,
			"| total_cost:",
			vehicle.total_cost,
			"| serial:",
			vehicle.serial_no,
			"| history rows:",
			len(vehicle.status_history),
		)
		assert vehicle.status == "Purchased", vehicle.status
		assert frappe.db.get_value("Serial No", vin, "vehicle") == vehicle.name

	so = make_sales_order(vins[0])
	print("2. Sales Order", so.name, "submitted | reserve_stock:", so.items[0].reserve_stock)

	sre = reserve_so(so)
	vehicle = frappe.get_doc("Vehicle", frappe.db.get_value("Vehicle", {"serial_no": vins[0]}))
	print(
		"3. Stock Reservation",
		sre.name,
		"| vehicle:",
		sre.vehicle,
		"| status:",
		sre.status,
		"| Vehicle.status:",
		vehicle.status,
		"| Vehicle.sales_order:",
		vehicle.sales_order,
	)
	assert sre.vehicle == vehicle.name
	assert vehicle.status == "Reserved"

	pe = make_advance_payment(so)
	so.reload()
	print(
		"4. Advance Payment", pe.name, "| SO advance_paid:", so.advance_paid, "| per_billed:", so.per_billed
	)

	dn = make_delivery_note(so)
	vehicle.reload()
	print(
		"5. Delivery Note",
		dn.name,
		"| Vehicle.status:",
		vehicle.status,
		"| SRE:",
		frappe.db.get_value("Stock Reservation Entry", sre.name, "status"),
	)

	si = make_sales_invoice(so, dn)
	vehicle.reload()
	print(
		"6. Sales Invoice",
		si.name,
		"| Vehicle.status:",
		vehicle.status,
		"| selling_price:",
		vehicle.selling_price,
		"| outstanding:",
		si.outstanding_amount,
		"| customer:",
		vehicle.customer,
	)
	assert vehicle.status == "Sold"

	expenses = make_expenses(vehicle.name)
	vehicle.reload()
	print(
		"7. Expenses",
		expenses,
		"| repair_cost:",
		vehicle.repair_cost,
		"| other_expense:",
		vehicle.other_expense,
		"| total_expense:",
		vehicle.total_expense,
		"| total_cost:",
		vehicle.total_cost,
		"| gross_profit:",
		vehicle.gross_profit,
		"| profit_percent:",
		round(vehicle.profit_percent, 2),
	)
	assert flt(vehicle.total_expense) == 15000.0

	import alf.alf.report.vehicle_profitability.vehicle_profitability as pr_mod
	import alf.alf.report.vehicle_reservation.vehicle_reservation as sre_mod

	reserved_vehicle = frappe.db.get_value("Vehicle", {"serial_no": vins[0]})
	data = sre_mod.execute(SOFilter(COMPANY, None))[1]
	print("8. Vehicle Reservation report rows:", len(data))
	for row in data:
		print("   ", row[0], row[7], row[8], row[12])
		assert row[0] == reserved_vehicle, row[0]
		assert row[1] == vins[0]
		assert row[7] == "Sales Order"
		assert row[8] == so.name
		assert row[12] in ("Reserved", "Partially Reserved", "Partially Delivered")

	data = pr_mod.execute(SOFilter(COMPANY, None))[1]
	print("9. Vehicle Profitability report rows:", len(data))
	for row in data:
		print("   ", row[0], row[4], row[10], row[11], row[12])

	print("ALL CHECKS PASSED")


class SOFilter(dict):
	def __init__(self, company, status):
		super().__init__(company=company)
		if status:
			self["status"] = status


def cleanup():
	"""Cancel and delete every document created by the flow, then the masters."""
	for vin in ("ALFTESTVIN0000001", "ALFTESTVIN0000002", "ALFTESTVIN0000003"):
		name = frappe.db.get_value("Vehicle", {"serial_no": vin}, "name")
		if name:
			frappe.db.set_value("Vehicle", name, {"sales_invoice": None, "sales_order": None})
			existing = frappe.get_doc("Vehicle", name)
			for row in existing.get("status_history") or []:
				if row.voucher_type and vouchers_exist(row.voucher_type, row.voucher_no):
					voucher = frappe.get_doc(row.voucher_type, row.voucher_no)
					if voucher.docstatus == 1:
						voucher.flags.ignore_permissions = True
						voucher.cancel()
			frappe.db.delete("Vehicle", name)

	for doctype, field, value in (
		("Vehicle Expense", "vehicle", ("like", "ALFTESTVIN%")),
		("Journal Entry", "user_remark", ("like", "%ALFTESTVIN%")),
		("Sales Invoice", "customer", None),
		("Delivery Note", "customer", None),
		("Payment Entry", "party", None),
		("Sales Order", "customer", None),
		("Purchase Receipt", "supplier", None),
	):
		filters = {}
		if value:
			filters[field] = value
		elif field in ("customer", "party", "supplier"):
			party = frappe.db.get_value(
				"Customer" if field != "supplier" else "Supplier",
				"ALF Test Buyer" if field != "supplier" else "ALF Test Seller",
				"name",
			)
			if not party:
				continue
			filters[field] = party

		for name in frappe.get_all(doctype, filters=filters, pluck="name"):
			frappe.delete_doc(doctype, name, force=1, ignore_permissions=True, ignore_missing=True)

	for vin in ("ALFTESTVIN0000001", "ALFTESTVIN0000002", "ALFTESTVIN0000003"):
		for bundle in frappe.get_all(
			"Serial and Batch Bundle", filters={"name": ("like", "%")}, pluck="name"
		):
			entries = frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": bundle, "serial_no": vin},
				pluck="name",
			)
			if entries:
				frappe.delete_doc(
					"Serial and Batch Bundle", bundle, force=1, ignore_permissions=True, ignore_missing=True
				)

		if frappe.db.exists("Serial No", vin):
			frappe.delete_doc("Serial No", vin, force=1, ignore_permissions=True, ignore_missing=True)

	for doctype, field, label in (
		("Customer", "customer_name", "ALF Test Buyer"),
		("Supplier", "supplier_name", "ALF Test Seller"),
	):
		name = frappe.db.get_value(doctype, {field: label})
		if name:
			frappe.delete_doc(doctype, name, force=1, ignore_permissions=True, ignore_missing=True)

	frappe.db.commit()
	print("cleanup done: test vehicles and masters removed")


def vouchers_exist(voucher_type, voucher_no):
	if not voucher_type or not voucher_no:
		return False
	try:
		return bool(frappe.db.exists(voucher_type, voucher_no))
	except Exception:
		return False


def ensure_customer():
	name = frappe.db.get_value("Customer", {"customer_name": "ALF Test Buyer"}, "name")
	if name:
		return name
	group = frappe.get_all("Customer Group", filters={"is_group": 0}, pluck="name", limit=1)[0]
	territory = frappe.get_all("Territory", filters={"is_group": 0}, pluck="name", limit=1)[0]
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": "ALF Test Buyer",
			"customer_group": group,
			"territory": territory,
		}
	)
	customer.flags.ignore_permissions = True
	customer.insert()
	return customer.name


def ensure_supplier():
	name = frappe.db.get_value("Supplier", {"supplier_name": "ALF Test Seller"}, "name")
	if name:
		return name
	supplier = frappe.new_doc("Supplier")
	supplier.supplier_name = "ALF Test Seller"
	supplier.supplier_group = frappe.get_all(
		"Supplier Group", filters={"is_group": 0}, pluck="name", limit=1
	)[0]
	supplier.flags.ignore_permissions = True
	supplier.insert()
	return supplier.name


def make_purchase_receipt(vins):
	supplier = ensure_supplier()
	warehouse = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0}, "name")
	pr = frappe.new_doc("Purchase Receipt")
	pr.company = COMPANY
	pr.supplier = supplier
	pr.posting_date = nowdate()
	pr.set_warehouse = warehouse
	pr.append(
		"items",
		{
			"item_code": "VEHICLE",
			"qty": len(vins),
			"rate": 500000,
			"warehouse": warehouse,
			"serial_no": "\n".join(vins),
		},
	)
	pr.flags.ignore_permissions = True
	pr.flags.ignore_mandatory = True
	pr.save()
	pr.submit()
	return pr


def make_sales_order(vin):
	customer = ensure_customer()
	vehicle_name = frappe.db.get_value("Vehicle", {"serial_no": vin})
	vehicle = frappe.get_doc("Vehicle", vehicle_name)
	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = customer
	so.transaction_date = nowdate()
	so.delivery_date = add_days(nowdate(), 7)
	so.append(
		"items",
		{
			"item_code": vehicle.item_code,
			"qty": 1,
			"rate": 600000,
			"warehouse": vehicle.warehouse,
			"reserve_stock": 1,
			"vehicle": vehicle.name,
		},
	)
	so.flags.ignore_permissions = True
	so.save()
	so.submit()
	return so


def reserve_so(so):
	so.reload()
	so.create_stock_reservation_entries(
		items_details=[
			{"sales_order_item": so.items[0].name, "warehouse": so.items[0].warehouse, "qty_to_reserve": 1}
		],
		notify=False,
	)
	return frappe.get_last_doc("Stock Reservation Entry")


def make_advance_payment(so):
	account = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0}, "name"
	) or frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Asset", "is_group": 0}, "name")
	pe = frappe.new_doc("Payment Entry")
	pe.company = COMPANY
	pe.payment_type = "Receive"
	pe.party_type = "Customer"
	pe.party = so.customer
	pe.posting_date = nowdate()
	pe.paid_from = frappe.db.get_value("Company", COMPANY, "default_receivable_account")
	pe.paid_to = account
	pe.paid_amount = 100000
	pe.received_amount = 100000
	pe.append(
		"references",
		{"reference_doctype": "Sales Order", "reference_name": so.name, "allocated_amount": 100000},
	)
	pe.flags.ignore_permissions = True
	pe.save()
	pe.submit()
	return pe


def make_delivery_note(so):
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	dn = make_delivery_note(so.name)
	for row in dn.items:
		so_item = frappe.get_doc("Sales Order Item", row.so_detail)
		row.vehicle = so_item.vehicle
	dn.flags.ignore_permissions = True
	dn.save()
	dn.submit()
	return dn


def make_sales_invoice(so, dn):
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

	si = make_sales_invoice(so.name)
	for row in si.items:
		if row.get("so_detail"):
			row.vehicle = frappe.db.get_value("Sales Order Item", row.so_detail, "vehicle")
	si.flags.ignore_permissions = True
	si.save()
	si.submit()
	return si


def make_expenses(vehicle):
	company = frappe.get_doc("Company", COMPANY)
	expense_account = company.default_expense_account
	bank = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0}, "name")
	created = []
	for expense_type, amount in (("Repairs", 8000), ("Spare Parts", 2000), ("Insurance", 5000)):
		expense = frappe.new_doc("Vehicle Expense")
		expense.vehicle = vehicle
		expense.expense_type = expense_type
		expense.posting_date = nowdate()
		expense.company = COMPANY
		expense.amount = amount
		expense.expense_account = expense_account
		expense.paid_from = bank
		expense.flags.ignore_permissions = True
		expense.save()
		expense.submit()
		created.append(f"{expense.name}:{amount}")

	return ", ".join(created)
