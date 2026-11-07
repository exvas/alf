"""Put repaired vehicle Serial Nos back in the warehouse they were received into.

`fix_vehicle_serial_tracking` created the missing `Serial No` records for VINs
received while the item was not serial tracked, but left their warehouse blank.
ERPNext only lets a serial go out from the warehouse it is recorded in, so those
vehicles could not be delivered ("Serial No ... is not present in the warehouse").
"""

import frappe
from frappe.utils import flt

from alf.alf.inventory import get_serial_nos, is_vehicle_item
from alf.patches.v1_0.fix_vehicle_serial_tracking import get_vehicle_rows


def execute():
	receipt_rows = {}
	for row in get_vehicle_rows():
		for serial_no in get_serial_nos(row):
			receipt_rows.setdefault(serial_no, row)

	for serial in frappe.get_all(
		"Serial No",
		filters={"warehouse": ("is", "not set"), "status": ("in", ("Active", ""))},
		fields=["name", "item_code", "company", "purchase_rate"],
	):
		row = receipt_rows.get(serial.name)
		if not row or row.item_code != serial.item_code or not is_vehicle_item(serial.item_code):
			continue

		# Serials that already moved through a bundle are tracked by ERPNext itself.
		if frappe.db.exists("Serial and Batch Entry", {"serial_no": serial.name, "docstatus": 1}):
			continue

		in_stock = flt(
			frappe.db.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "actual_qty")
		)
		if in_stock <= 0:
			continue

		values = {"warehouse": row.warehouse, "status": "Active"}
		if not serial.company:
			values["company"] = row.company
		if not flt(serial.purchase_rate):
			values["purchase_rate"] = row.rate

		frappe.db.set_value("Serial No", serial.name, values, update_modified=False)
