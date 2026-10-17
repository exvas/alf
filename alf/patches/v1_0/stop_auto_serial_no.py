import frappe
from frappe import _


def execute():
	"""Stop ERPNext from auto-generating vehicle serial numbers.

	Every serial number on a vehicle item is a real VIN supplied by the
	manufacturer, so it must be typed on the Purchase Receipt. Leaving
	`Item.serial_no_series` set makes ERPNext pre-fill a generated number
	(VEH-00001) that is not a VIN.
	"""
	item_group = frappe.db.get_single_value("Stock Settings", "vehicle_item_group") or "Vehicles"

	items = frappe.get_all(
		"Item",
		filters={
			"item_group": item_group,
			"has_serial_no": 1,
			"serial_no_series": ("is", "set"),
		},
		pluck="name",
	)

	for item_code in items:
		frappe.db.set_value("Item", item_code, "serial_no_series", None, update_modified=False)
		print(f"cleared Serial No Series on {item_code}")

	frappe.db.commit()
	print(f"VIN patch: {len(items)} item(s) no longer auto-generate serial numbers")
