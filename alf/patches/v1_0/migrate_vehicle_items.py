"""Move serial tracked vehicle items into the Vehicle Item Group and backfill the
Vehicle records for Purchase Receipts submitted before the item group existed.

`purchase_receipt_before_submit` only creates a Vehicle when `is_vehicle_item`
is True, which requires the item to sit in the configured Vehicle Item Group.
Receipts submitted while the item was filed under another group were therefore
skipped; those VINs are replayed here.
"""

import frappe

from alf.alf.events import sync_vehicle_from_purchase_receipt
from alf.alf.inventory import (
	get_serial_nos,
	get_vehicle_item_group,
	get_vehicle_item_group_candidates,
)


def execute():
	setup_item_group()
	migrate_items()
	frappe.clear_cache()
	backfill_vehicles()


def setup_item_group(parent="All Item Groups"):
	group = get_vehicle_item_group()
	if frappe.db.exists("Item Group", group):
		return group

	item_group = frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": group,
			"parent_item_group": parent if frappe.db.exists("Item Group", parent) else None,
			"is_group": 0,
		}
	)
	item_group.flags.ignore_permissions = True
	item_group.insert()
	return item_group.name


def migrate_items():
	"""Move serial tracked vehicle items into the configured Vehicle Item Group."""
	group = get_vehicle_item_group()
	if not frappe.db.exists("Item Group", group):
		return

	for item_code in get_vehicle_item_group_candidates(get_receipt_item_codes()):
		frappe.db.set_value("Item", item_code, "item_group", group, update_modified=False)


def get_receipt_item_codes():
	return frappe.get_all(
		"Purchase Receipt Item",
		filters={"docstatus": 1},
		pluck="item_code",
		distinct=True,
	)


def backfill_vehicles():
	"""Create the missing Vehicle for VINs received on already submitted receipts."""
	group = get_vehicle_item_group()
	item_cache = {}

	for receipt in frappe.get_all(
		"Purchase Receipt",
		filters={"docstatus": 1},
		fields=["name"],
		order_by="posting_date, creation",
	):
		doc = frappe.get_doc("Purchase Receipt", receipt.name)
		receipt_vehicle = None

		for row in doc.items:
			if row.item_code not in item_cache:
				item_cache[row.item_code] = frappe.db.get_value(
					"Item", row.item_code, ["item_group", "has_serial_no"], as_dict=True
				)
			item = item_cache[row.item_code]
			if not item or not item.has_serial_no or item.item_group != group:
				continue

			for serial_no in get_serial_nos(row):
				if not frappe.db.exists("Serial No", serial_no):
					continue
				if frappe.db.exists("Vehicle", {"serial_no": serial_no}):
					continue

				vehicle = sync_vehicle_from_purchase_receipt(doc, row, serial_no)
				if not vehicle:
					continue

				frappe.db.set_value(
					"Purchase Receipt Item", row.name, "vehicle", vehicle, update_modified=False
				)
				frappe.db.set_value("Serial No", serial_no, "vehicle", vehicle, update_modified=False)
				receipt_vehicle = receipt_vehicle or vehicle

		if receipt_vehicle:
			frappe.db.set_value(
				"Purchase Receipt", doc.name, "vehicle", receipt_vehicle, update_modified=False
			)

	frappe.db.commit()
