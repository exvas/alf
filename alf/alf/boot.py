import frappe

from alf.alf.inventory import get_vehicle_item_group


def boot_session(bootinfo):
	"""Expose the vehicle item group so client scripts can flag vehicle rows."""
	bootinfo.alf_vehicle_item_group = get_vehicle_item_group()
