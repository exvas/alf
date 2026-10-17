"""Repair site schema drift.

Sites created (or restored) out of step with the installed erpnext version can
miss the Custom Fields that erpnext's install step creates on Address and
Contact. `Address.is_your_company_address` is one of them, and without it every
Purchase Receipt / Sales Order / Delivery Note form fails with:

    pymysql.err.OperationalError: (1054, "Unknown column
    'tabAddress.is_your_company_address' in 'WHERE'")

Re-applies erpnext's own custom-field definitions (idempotent) and then adds any
column that the DocType definitions declare but the database lacks.

    bench --site <site> execute alf.alf.schema_fix.run
"""

import frappe
from frappe.database.schema import get_definition


def run():
	fix_address_contact_custom_fields()

	drifted = find_column_drift()
	for doctype, _module, columns in drifted:
		print("schema fix: adding", doctype, [c for c, _t in columns])
		frappe.db.updatedb(doctype)

	frappe.db.commit()
	frappe.clear_cache()

	remaining = find_column_drift()
	print(f"schema fix: {len(drifted)} doctypes repaired, {len(remaining)} still drifted")
	return remaining


def fix_address_contact_custom_fields():
	"""Re-run erpnext's install step for its Address/Contact custom fields."""
	from erpnext.setup.install import create_address_and_contact_custom_fields

	create_address_and_contact_custom_fields()
	frappe.db.commit()
	frappe.clear_cache()

	print(
		"schema fix: Address custom fields =",
		frappe.get_all("Custom Field", filters={"dt": "Address"}, pluck="fieldname"),
	)
	print(
		"schema fix: Contact custom fields =",
		frappe.get_all("Custom Field", filters={"dt": "Contact"}, pluck="fieldname"),
	)


def real_columns(doctype):
	rows = frappe.db.sql(
		"""
		select column_name from information_schema.columns
		where table_schema = database() and table_name = %s
		""",
		f"tab{doctype}",
		as_list=True,
	)
	return {row[0] for row in rows}


def find_column_drift():
	"""Doctypes whose stored columns are missing a non-virtual, stored field."""
	drifted = []

	for row in frappe.get_all("DocType", filters={"issingle": 0}, fields=["name", "module"], limit=0):
		if not frappe.db.table_exists(row.name):
			continue

		existing = real_columns(row.name)
		if not existing:
			continue

		missing = []
		for df in frappe.get_meta(row.name).fields:
			if df.get("is_virtual"):
				continue
			if not get_definition(df.fieldtype, df.precision, df.length):
				continue
			if df.fieldname not in existing:
				missing.append((df.fieldname, df.fieldtype))

		if missing:
			drifted.append((row.name, row.module, missing))

	return drifted
