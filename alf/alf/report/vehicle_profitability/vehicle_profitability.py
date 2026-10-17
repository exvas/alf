# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_data(filters):
	conditions = ""
	values = {}

	if filters.company:
		conditions += " and v.company = %(company)s"
		values["company"] = filters.company

	if filters.status:
		conditions += " and v.status = %(status)s"
		values["status"] = filters.status

	if filters.from_date:
		conditions += " and ifnull(v.purchase_date, v.creation) >= %(from_date)s"
		values["from_date"] = filters.from_date

	if filters.to_date:
		conditions += " and ifnull(v.purchase_date, v.creation) <= %(to_date)s"
		values["to_date"] = filters.to_date

	return frappe.db.sql(
		f"""
		select
			v.name as vehicle,
			v.vin,
			v.make,
			v.model,
			v.status,
			v.purchase_date,
			v.purchase_price,
			v.repair_cost,
			v.other_expense,
			v.total_expense,
			v.total_cost,
			v.selling_price,
			v.gross_profit,
			v.profit_percent,
			v.customer,
			v.sales_invoice,
			v.sales_order
		from `tabVehicle` v
		where v.status in ('Purchased', 'In Repair', 'Ready for Sale', 'Parked', 'Reserved', 'Delivered', 'Sold')
			{conditions}
		order by v.status, v.modified desc
		""",
		values,
		as_list=True,
	)


def get_columns():
	return [
		{
			"label": _("Vehicle"),
			"fieldname": "vehicle",
			"fieldtype": "Link",
			"options": "Vehicle",
			"width": 130,
		},
		{"label": _("VIN / Chassis"), "fieldname": "vin", "fieldtype": "Data", "width": 150},
		{"label": _("Make"), "fieldname": "make", "fieldtype": "Data", "width": 110},
		{"label": _("Model"), "fieldname": "model", "fieldtype": "Data", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Purchase Date"), "fieldname": "purchase_date", "fieldtype": "Date", "width": 110},
		{"label": _("Purchase Price"), "fieldname": "purchase_price", "fieldtype": "Currency", "width": 130},
		{"label": _("Repair & Parts"), "fieldname": "repair_cost", "fieldtype": "Currency", "width": 130},
		{"label": _("Other Expenses"), "fieldname": "other_expense", "fieldtype": "Currency", "width": 130},
		{"label": _("Total Expenses"), "fieldname": "total_expense", "fieldtype": "Currency", "width": 130},
		{"label": _("Total Cost"), "fieldname": "total_cost", "fieldtype": "Currency", "width": 130},
		{"label": _("Selling Price"), "fieldname": "selling_price", "fieldtype": "Currency", "width": 130},
		{
			"label": _("Profit / Loss"),
			"fieldname": "gross_profit",
			"fieldtype": "Currency",
			"width": 130,
		},
		{"label": _("Profit %"), "fieldname": "profit_percent", "fieldtype": "Percent", "width": 100},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 140,
		},
		{
			"label": _("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 140,
		},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 140,
		},
	]
