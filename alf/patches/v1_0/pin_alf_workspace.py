import frappe

SEQUENCE_ID = 1
HOME_BUMPED = 1.5


def execute():
	"""Pin the ALF Cars workspace first while keeping its sequence id at 1."""
	if not frappe.db.exists("Workspace", "ALF Cars"):
		return

	frappe.db.set_value("Workspace", "ALF Cars", "sequence_id", SEQUENCE_ID, update_modified=False)

	home = frappe.db.get_value("Workspace", {"name": "Home", "public": 1}, "name")
	if home and frappe.db.get_value("Workspace", home, "sequence_id") <= SEQUENCE_ID:
		frappe.db.set_value("Workspace", home, "sequence_id", HOME_BUMPED, update_modified=False)

	frappe.clear_cache()
	frappe.db.commit()
