import frappe


def execute():
	"""Turn on ERPNext stock reservation so a Sales Order can reserve a vehicle."""
	frappe.db.set_single_value("Stock Settings", "enable_stock_reservation", 1)
	frappe.db.set_single_value("Stock Settings", "allow_partial_reservation", 1)
	frappe.db.set_single_value("Stock Settings", "auto_reserve_serial_and_batch", 1)
	frappe.db.set_single_value("Stock Settings", "pick_serial_and_batch_based_on", "FIFO")
	frappe.db.commit()

	import alf.alf.setup as alf_setup

	alf_setup.setup_item_group()
	alf_setup.setup_vehicle_item()
