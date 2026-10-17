import frappe

from alf.alf.inventory import AVAILABLE_STATUSES


@frappe.whitelist()
def get_vehicle_for_serial(serial_no):
	"""Returns the vehicle linked to a serial number, if any."""
	if not serial_no:
		return None

	return frappe.db.get_value(
		"Vehicle",
		{"serial_no": serial_no},
		["name", "vin", "license_plate", "make", "model", "status", "sales_order", "warehouse"],
		as_dict=True,
	)


@frappe.whitelist()
def get_available_vehicles(item_code=None, company=None, warehouse=None):
	"""Vehicles in stock that are not reserved by an open Sales Order."""
	reserved = frappe.get_all(
		"Stock Reservation Entry",
		filters={"docstatus": 1, "status": ("not in", ["Delivered", "Cancelled"])},
		pluck="vehicle",
	)

	filters = {
		"serial_no": ("is", "set"),
		"status": ("in", list(AVAILABLE_STATUSES)),
	}
	if item_code:
		filters["item_code"] = item_code
	if company:
		filters["company"] = company
	if warehouse:
		filters["warehouse"] = warehouse
	if reserved:
		filters["name"] = ("not in", reserved)

	return frappe.get_all(
		"Vehicle",
		filters=filters,
		fields=[
			"name",
			"vin",
			"license_plate",
			"make",
			"model",
			"year",
			"serial_no",
			"status",
			"warehouse",
			"total_cost",
			"estimated_selling_price",
		],
		order_by="modified desc",
		limit_page_length=0,
	)


@frappe.whitelist()
def check_vin_duplicates(vins):
	"""Returns VINs that already exist as stock serial numbers."""
	if isinstance(vins, str):
		vins = frappe.parse_json(vins)

	vins = [value.strip() for value in (vins or []) if value and value.strip()]
	if not vins:
		return []

	existing = frappe.get_all("Serial No", filters={"name": ("in", vins)}, pluck="name")
	used_by_vehicle = frappe.get_all(
		"Vehicle",
		filters={"serial_no": ("in", vins), "status": ("not in", ["Purchased"])},
		pluck="serial_no",
	)

	return sorted(set(existing) | set(used_by_vehicle))
