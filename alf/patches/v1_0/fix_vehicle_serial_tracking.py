"""A vehicle Item must be serial tracked, and every received VIN must have a Vehicle.

A vehicle Item created without "Has Serial No" is invisible to the whole
lifecycle: `is_vehicle_item` returns False, so Purchase Receipt creates no
Vehicle, and the row's `serial_no` is stored as free text with no `Serial No`
record behind it. Items created that way are corrected here and their already
submitted receipts are backfilled.
"""

import frappe

from alf.alf.inventory import get_serial_nos, get_vehicle_item_group
from alf.patches.v1_0.migrate_vehicle_items import backfill_vehicles


def execute():
	enable_serial_tracking()
	create_missing_serials()
	backfill_vehicles()


def enable_serial_tracking():
	"""Vehicle items are identified by their VIN, so they are always serial tracked."""
	group = get_vehicle_item_group()

	for item_code in frappe.get_all("Item", filters={"item_group": group, "has_serial_no": 0}, pluck="name"):
		frappe.db.set_value("Item", item_code, "has_serial_no", 1, update_modified=False)


def create_missing_serials():
	"""Receipts submitted before the item was serial tracked stored the VIN as text."""
	group = get_vehicle_item_group()
	item_cache = {}

	for row in get_vehicle_rows():
		if row.item_code not in item_cache:
			item_cache[row.item_code] = frappe.db.get_value(
				"Item", row.item_code, ["item_group", "has_serial_no"], as_dict=True
			)

		item = item_cache[row.item_code]
		if not item or not item.has_serial_no or item.item_group != group:
			continue

		for serial_no in get_serial_nos(row):
			if frappe.db.exists("Serial No", serial_no):
				continue

			serial = frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": serial_no,
					"item_code": row.item_code,
					"status": "Active",
					"purchase_rate": row.rate,
				}
			)
			serial.flags.ignore_permissions = True
			serial.flags.ignore_mandatory = True
			serial.insert()


def get_vehicle_rows():
	return frappe.db.sql(
		"""
		select
			pri.name, pri.item_code, pri.serial_no, pri.serial_and_batch_bundle,
			pri.warehouse, pri.rate, pri.parent as receipt, pr.company
		from `tabPurchase Receipt Item` pri
		join `tabPurchase Receipt` pr on pr.name = pri.parent
		where pr.docstatus = 1 and ifnull(pri.serial_no, '') != ''
		""",
		as_dict=True,
	)
