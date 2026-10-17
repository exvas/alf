# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def has_vehicle_dimension():
	"""True when `Vehicle` is registered as an Accounting Dimension."""
	return "vehicle" in {df.fieldname for df in frappe.get_meta("Journal Entry Account").fields}


class VehicleExpense(Document):
	def validate(self):
		self.set_defaults()
		self.warn_if_sold()

	def set_defaults(self):
		if not self.company:
			self.company = (
				frappe.get_cached_value("Vehicle", self.vehicle, "company")
				or frappe.defaults.get_user_default("Company")
				or frappe.db.get_single_value("Global Defaults", "default_company")
			)

		if not self.cost_center:
			self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

		if not self.expense_account:
			self.expense_account = get_vehicle_expense_account(self.company)

		if not self.paid_from:
			self.paid_from = get_vehicle_unbooked_expense_account(self.company)

		if self.vendor_type == "Supplier" and self.supplier:
			self.vendor_name = self.supplier

	def warn_if_sold(self):
		if frappe.db.get_value("Vehicle", self.vehicle, "sales_invoice"):
			frappe.msgprint(
				_("Vehicle {0} is already sold. This expense will still reduce its final profit.").format(
					frappe.bold(self.vehicle)
				),
				alert=True,
				indicator="orange",
			)

	def on_submit(self):
		journal_entry = self.make_journal_entry()
		self.db_set("journal_entry", journal_entry.name)

	def on_cancel(self):
		if not self.journal_entry:
			return

		journal_entry = frappe.get_doc("Journal Entry", self.journal_entry)
		if journal_entry.docstatus == 1:
			journal_entry.flags.ignore_permissions = True
			journal_entry.cancel()

		self.db_set("journal_entry", None)

	def make_journal_entry(self):
		journal_entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": self.posting_date,
				"cheque_no": self.reference_no,
				"cheque_date": self.reference_date,
				"user_remark": _("Vehicle expense {0} for {1}").format(self.name, self.vehicle),
				"accounts": [
					{
						"account": self.expense_account,
						"debit_in_account_currency": self.amount,
						"cost_center": self.cost_center,
						"project": self.project,
					},
					{
						"account": self.paid_from,
						"credit_in_account_currency": self.amount,
						"cost_center": self.cost_center,
					},
				],
			}
		)

		# Accounting dimension: lets the General Ledger be filtered per vehicle.
		if has_vehicle_dimension():
			for account in journal_entry.accounts:
				account.vehicle = self.vehicle

		journal_entry.flags.ignore_permissions = True
		journal_entry.submit()
		return journal_entry


def get_vehicle_expense_account(company):
	account = frappe.db.get_single_value("Stock Settings", "vehicle_expense_account")
	if account and frappe.get_cached_value("Account", account, "company") == company:
		return account

	frappe.throw(
		_("Please set a Vehicle Expense account in Stock Settings, or set Expense Account in this document."),
		title=_("Expense Account Missing"),
	)


def get_vehicle_unbooked_expense_account(company):
	account = frappe.db.get_single_value("Stock Settings", "vehicle_unbooked_expense_account")
	if account and frappe.get_cached_value("Account", account, "company") == company:
		return account

	if default_expense := frappe.get_cached_value("Company", company, "default_expense_account"):
		return default_expense

	frappe.throw(
		_(
			"Please set a Vehicle Unbooked Expense account in Stock Settings, or set Paid Through in this document."
		),
		title=_("Paid Through Account Missing"),
	)
