import frappe

VINS = ("ALFTESTVIN0000001", "ALFTESTVIN0000002", "ALFTESTVIN0000003")
CUSTOMER = "ALF Test Buyer"
SUPPLIER = "ALF Test Seller"


def run():
	"""Remove leftovers of `alf.alf.test_vehicle_flow` from the site."""
	vehicles = frappe.get_all("Vehicle", filters={"serial_no": ("in", VINS)}, pluck="name")
	print("vehicles", vehicles)

	expenses = frappe.get_all("Vehicle Expense", filters={"vehicle": ("in", VINS)}, pluck="name")
	for name in expenses:
		doc = frappe.get_doc("Vehicle Expense", name)
		if doc.docstatus == 1:
			doc.flags.ignore_permissions = True
			doc.cancel()
	doc_names = [d.name for d in frappe.get_all("Vehicle Expense", filters={"vehicle": ("in", VINS)})]
	for name in doc_names:
		frappe.delete_doc("Vehicle Expense", name, force=1, ignore_permissions=True, ignore_missing=True)
	print("expenses", doc_names)

	for name in frappe.get_all(
		"Journal Entry", filters={"user_remark": ("like", "%ALFTESTVIN%")}, pluck="name"
	):
		je = frappe.get_doc("Journal Entry", name)
		if je.docstatus == 1:
			je.flags.ignore_permissions = True
			je.cancel()
		frappe.delete_doc("Journal Entry", name, force=1, ignore_permissions=True, ignore_missing=True)
		print("journal entry", name)

	customer = frappe.db.get_value("Customer", {"customer_name": CUSTOMER})
	supplier = frappe.db.get_value("Supplier", {"supplier_name": SUPPLIER})

	for doctype, filters in (
		("Sales Invoice", {"customer": customer}),
		("Delivery Note", {"customer": customer}),
		("Payment Entry", {"party": customer}),
		("Sales Order", {"customer": customer}),
		("Purchase Receipt", {"supplier": supplier}),
	):
		if not any(filters.values()):
			continue
		for name in frappe.get_all(doctype, filters=filters, pluck="name"):
			doc = frappe.get_doc(doctype, name)
			if doc.docstatus == 1:
				doc.flags.ignore_permissions = True
				doc.cancel()
		for name in frappe.get_all(doctype, filters=filters, pluck="name"):
			frappe.delete_doc(doctype, name, force=1, ignore_permissions=True, ignore_missing=True)
			print("deleted", doctype, name)

	for vin in VINS:
		for bundle in frappe.get_all(
			"Serial and Batch Entry",
			filters={"serial_no": vin, "parenttype": "Serial and Batch Bundle"},
			pluck="parent",
		):
			frappe.delete_doc(
				"Serial and Batch Bundle", bundle, force=1, ignore_permissions=True, ignore_missing=True
			)
		if frappe.db.exists("Serial No", vin):
			frappe.delete_doc("Serial No", vin, force=1, ignore_permissions=True, ignore_missing=True)

	for name in vehicles:
		frappe.delete_doc("Vehicle", name, force=1, ignore_permissions=True, ignore_missing=True)
		print("deleted Vehicle", name)

	if customer:
		frappe.delete_doc("Customer", customer, force=1, ignore_permissions=True, ignore_missing=True)
		print("deleted Customer", customer)
	if supplier:
		frappe.delete_doc("Supplier", supplier, force=1, ignore_permissions=True, ignore_missing=True)
		print("deleted Supplier", supplier)

	frappe.db.commit()
	print("remaining vehicles:", frappe.get_all("Vehicle", filters={"serial_no": ("in", VINS)}, pluck="name"))
	print("remaining customer:", frappe.db.get_value("Customer", {"customer_name": CUSTOMER}))
	print("remaining supplier:", frappe.db.get_value("Supplier", {"supplier_name": SUPPLIER}))
