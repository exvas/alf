"""Register `Vehicle` as an Accounting Dimension.

Gives every vehicle expense a real GL dimension, so `Vehicle Repairs and Parts`
can be reconciled per vehicle straight from the General Ledger:

    bench --site <site> execute alf.alf.dimensions.run

The dimension adds a `vehicle` field to Journal Entry Account and GL Entry (via
erpnext's own make_dimension_in_accounting_doctypes) and is safe to re-run.
"""

import frappe
from frappe.utils import cint

DIMENSION_LABEL = "Vehicle"
DIMENSION_DOCTYPE = "Vehicle"


def run():
	ensure_dimension()
	make_mandatory()
	backfill_expense_dimension()
	print_summary()


def ensure_dimension():
	if frappe.db.exists("Accounting Dimension", {"fieldname": "vehicle"}):
		print("dimension: Vehicle already registered")
		return frappe.get_doc("Accounting Dimension", {"fieldname": "vehicle"})

	dimension = frappe.get_doc(
		{
			"doctype": "Accounting Dimension",
			"label": DIMENSION_LABEL,
			"document_type": DIMENSION_DOCTYPE,
		}
	)
	dimension.flags.ignore_permissions = True
	dimension.insert()

	# erpnext checks for an existing dimension with the same document type:
	# remove a duplicate entry if `label` created a second one
	duplicates = frappe.get_all(
		"Accounting Dimension",
		filters={"document_type": DIMENSION_DOCTYPE, "name": ("!=", dimension.name)},
		pluck="name",
	)
	for name in duplicates:
		if frappe.db.exists("Accounting Dimension", name):
			frappe.delete_doc("Accounting Dimension", name, force=1, ignore_permissions=True)

	frappe.db.commit()
	frappe.clear_cache()
	print(f"dimension: created Vehicle (fieldname={dimension.fieldname})")
	return frappe.get_doc("Accounting Dimension", dimension.name)


def make_mandatory():
	"""Require a vehicle on every Profit and Loss posting.

	`mandatory_for_pl = 1` blocks any expense/income GL line without a vehicle.
	`mandatory_for_bs` stays 0: Debtors, Creditors and Cash lines belong to the
	party, not to a vehicle, and making them mandatory blocks every voucher.
	"""
	updated = 0
	for row in frappe.get_all(
		"Accounting Dimension Detail",
		filters={"parent": "Vehicle"},
		fields=["name", "mandatory_for_pl", "mandatory_for_bs"],
	):
		if not cint(row.mandatory_for_pl) or cint(row.mandatory_for_bs):
			frappe.db.set_value(
				"Accounting Dimension Detail",
				row.name,
				{"mandatory_for_pl": 1, "mandatory_for_bs": 0},
				update_modified=False,
			)
			updated += 1

	frappe.db.commit()
	frappe.clear_cache()
	print(f"dimension: set mandatory_for_pl on {updated} row(s)")


def backfill_expense_dimension():
	"""Set the vehicle dimension on existing vehicle-expense Journal Entries."""
	from alf.alf.doctype.vehicle_expense.vehicle_expense import (
		get_vehicle_expense_account,
		get_vehicle_unbooked_expense_account,
	)

	updated = 0
	expenses = frappe.get_all(
		"Vehicle Expense",
		filters={"docstatus": 1, "journal_entry": ("is", "set")},
		fields=["name", "vehicle", "company", "journal_entry"],
	)

	for expense in expenses:
		journal_entry = frappe.get_doc("Journal Entry", expense.journal_entry)
		if journal_entry.docstatus != 1:
			continue

		debit_account = get_vehicle_expense_account(expense.company)
		credit_account = get_vehicle_unbooked_expense_account(expense.company)
		if any(account.get("vehicle") for account in journal_entry.accounts):
			continue

		for account in journal_entry.accounts:
			if account.account == debit_account:
				account.vehicle = expense.vehicle
				frappe.db.set_value(
					"Journal Entry Account",
					account.name,
					"vehicle",
					expense.vehicle,
					update_modified=False,
				)
			elif account.account == credit_account:
				frappe.db.set_value(
					"Journal Entry Account",
					account.name,
					"vehicle",
					expense.vehicle,
					update_modified=False,
				)

		frappe.db.sql(
			"""
			update `tabGL Entry`
			set vehicle = %s
			where voucher_type = 'Journal Entry' and voucher_no = %s
				and (vehicle is null or vehicle = '')
			""",
			(expense.vehicle, journal_entry.name),
		)
		updated += 1

	frappe.db.commit()
	frappe.clear_cache()
	print(f"dimension: backfilled {updated} expense Journal Entries")


def print_summary():
	dimensions = frappe.get_all(
		"Accounting Dimension",
		fields=["name", "label", "fieldname", "document_type", "disabled"],
	)
	print("dimension: registered =", dimensions)
	print(
		"dimension: details =",
		frappe.get_all(
			"Accounting Dimension Detail",
			fields=["parent", "company", "mandatory_for_pl", "mandatory_for_bs"],
		),
	)

	for doctype in ("Journal Entry Account", "GL Entry"):
		has_field = "vehicle" in {df.fieldname for df in frappe.get_meta(doctype).fields}
		print(f"dimension: {doctype}.vehicle present = {has_field}")
