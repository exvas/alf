"""Create the Vehicle Item Group + a ready-to-use serial tracked vehicle Item.

Run once per site: `bench --site <site> execute alf.alf.setup.run`
"""

import frappe
from frappe import _

from alf.alf.inventory import VEHICLE_ITEM_GROUP


def run():
	setup_item_group()
	setup_vehicle_item()
	print("Vehicle item group and item are ready.")


def setup_item_group(parent="All Item Groups"):
	if frappe.db.exists("Item Group", VEHICLE_ITEM_GROUP):
		return VEHICLE_ITEM_GROUP

	item_group = frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": VEHICLE_ITEM_GROUP,
			"parent_item_group": parent if frappe.db.exists("Item Group", parent) else None,
			"is_group": 0,
		}
	)
	item_group.flags.ignore_permissions = True
	item_group.insert()
	return item_group.name


def setup_vehicle_item(item_code="VEHICLE", item_name="Vehicle"):
	"""Serial tracked vehicle item. Serial No = VIN / chassis number."""
	if frappe.db.exists("Item", item_code):
		return item_code

	stock_uom = frappe.db.get_value("UOM", "Nos", "name") or frappe.get_all("UOM", pluck="name", limit=1)[0]
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": setup_item_group(),
			"is_stock_item": 1,
			"has_serial_no": 1,
			"serial_no_series": None,
			"stock_uom": stock_uom,
			"valuation_method": "FIFO",
			"include_item_in_manufacturing": 0,
			"allow_alternative_item": 0,
			"is_sales_item": 1,
			"is_purchase_item": 1,
		}
	)
	item.flags.ignore_permissions = True
	item.flags.ignore_mandatory = True
	item.insert()

	frappe.msgprint(
		_(
			"Created Item {0} (serial tracked). Serial Series is left empty on purpose: enter the VIN "
			"manually on the Purchase Receipt."
		).format(item_code)
	)
	return item.name
