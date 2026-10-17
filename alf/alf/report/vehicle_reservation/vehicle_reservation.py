# Copyright (c) 2026, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	conditions = ""
	values = {}

	if filters.company:
		conditions += " and v.company = %(company)s"
		values["company"] = filters.company

	if filters.status:
		conditions += " and v.status = %(status)s"
		values["status"] = filters.status

	if filters.vehicle:
		conditions += " and v.name = %(vehicle)s"
		values["vehicle"] = filters.vehicle

	return frappe.db.sql(
		f"""
		select
			v.name as vehicle,
			v.vin,
			v.license_plate,
			v.make,
			v.model,
			v.status as vehicle_status,
			sre.name as stock_reservation_entry,
			sre.voucher_type,
			sre.voucher_no,
			so.customer,
			sre.reserved_qty,
			sre.delivered_qty,
			sre.status as reservation_status,
			sre.warehouse,
			date(sre.creation) as reserved_on,
			v.total_cost,
			v.estimated_selling_price,
			(ifnull(v.estimated_selling_price, 0) - ifnull(v.total_cost, 0)) as estimated_profit
		from `tabVehicle` v
		inner join `tabStock Reservation Entry` sre
			on sre.vehicle = v.name and sre.docstatus = 1
		left join `tabSales Order` so
			on sre.voucher_type = 'Sales Order' and so.name = sre.voucher_no
		where sre.status not in ('Cancelled', 'Delivered')
			{conditions}
		order by sre.creation desc
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
		{"label": _("Plate"), "fieldname": "license_plate", "fieldtype": "Data", "width": 110},
		{"label": _("Make"), "fieldname": "make", "fieldtype": "Data", "width": 100},
		{"label": _("Model"), "fieldname": "model", "fieldtype": "Data", "width": 120},
		{"label": _("Vehicle Status"), "fieldname": "vehicle_status", "fieldtype": "Data", "width": 110},
		{
			"label": _("Reservation"),
			"fieldname": "stock_reservation_entry",
			"fieldtype": "Link",
			"options": "Stock Reservation Entry",
			"width": 150,
		},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 110},
		{
			"label": _("Sales Order"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 130,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 140,
		},
		{"label": _("Reserved Qty"), "fieldname": "reserved_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Delivered Qty"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Reservation Status"),
			"fieldname": "reservation_status",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 140,
		},
		{"label": _("Reserved On"), "fieldname": "reserved_on", "fieldtype": "Date", "width": 110},
		{"label": _("Total Cost"), "fieldname": "total_cost", "fieldtype": "Currency", "width": 120},
		{
			"label": _("Expected Price"),
			"fieldname": "estimated_selling_price",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Estimated Profit"),
			"fieldname": "estimated_profit",
			"fieldtype": "Currency",
			"width": 130,
		},
	]
