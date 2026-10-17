import frappe

from alf.alf.schema_fix import fix_address_contact_custom_fields


def execute():
	"""Restore erpnext's Address/Contact custom fields on drifted sites.

	Without Address.is_your_company_address every Purchase Receipt form fails with
	`Unknown column 'tabAddress.is_your_company_address' in 'WHERE'`.
	"""
	frappe.clear_cache()
	fix_address_contact_custom_fields()
	remaining = __import__("alf.alf.schema_fix", fromlist=["find_column_drift"]).find_column_drift()
	if remaining:
		print("address/contact patch: remaining column drift:", [d[0] for d in remaining])

	frappe.clear_cache()
	frappe.db.commit()
