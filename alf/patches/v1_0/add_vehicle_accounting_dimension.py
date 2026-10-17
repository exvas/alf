import frappe


def execute():
	"""Add `vehicle` as an accounting dimension so expenses reconcile per vehicle."""
	if not frappe.db.exists("Accounting Dimension", {"fieldname": "vehicle"}):
		dimension = frappe.get_doc(
			{
				"doctype": "Accounting Dimension",
				"label": "Vehicle",
				"document_type": "Vehicle",
			}
		)
		dimension.flags.ignore_permissions = True
		dimension.insert()
		frappe.db.commit()
		frappe.clear_cache()

	# Require a vehicle on every Profit and Loss line; keep Balance Sheet optional
	# so Debtors / Creditors / Cash do not block vouchers.
	for row in frappe.get_all("Accounting Dimension Detail", filters={"parent": "Vehicle"}, pluck="name"):
		frappe.db.set_value(
			"Accounting Dimension Detail",
			row,
			{"mandatory_for_pl": 1, "mandatory_for_bs": 0},
			update_modified=False,
		)
	frappe.db.commit()
	frappe.clear_cache()

	print(
		"vehicle dimension: Journal Entry Account.vehicle =",
		"vehicle" in {df.fieldname for df in frappe.get_meta("Journal Entry Account").fields},
		"| GL Entry.vehicle =",
		"vehicle" in {df.fieldname for df in frappe.get_meta("GL Entry").fields},
	)
