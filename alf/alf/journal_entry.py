import json

import frappe
from erpnext.accounts.utils import get_balance_on
from frappe import _
from frappe.utils import getdate


@frappe.whitelist()
def get_account_balances(accounts, date=None, company=None):
	"""Return {account: balance} as on `date` for the Journal Entry accounts grid."""
	if isinstance(accounts, str):
		accounts = json.loads(accounts)

	date = getdate(date) if date else getdate()
	balances = {}
	for account in set(filter(None, accounts or [])):
		if not frappe.has_permission("Account", "read", account):
			frappe.throw(_("Not permitted to read Account {0}").format(account), frappe.PermissionError)
		balances[account] = get_balance_on(account=account, date=date, company=company)

	return balances
