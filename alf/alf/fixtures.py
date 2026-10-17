"""Fixtures owned by `alf`.

Customisations on ERPNext doctypes are declared here and synced by
`bench migrate`, so no core ERPNext file is modified.
"""

VEHICLE_STATUSES = "Purchased\nIn Repair\nReady for Sale\nParked\nReserved\nDelivered\nSold"


def custom_field(name, dt, fieldname, label, **kwargs):
	return {
		"doctype": "Custom Field",
		"name": name,
		"dt": dt,
		"fieldname": fieldname,
		"label": label,
		"insert_after": kwargs.pop("insert_after", None),
		"fieldtype": kwargs.pop("fieldtype", "Data"),
		"module": "Alf",
		**kwargs,
	}


def vehicle_custom_fields():
	"""Sales-inventory fields on ERPNext `Vehicle` (Setup module doctype)."""
	return [
		custom_field(
			"Vehicle-stock_section",
			"Vehicle",
			"stock_section",
			"Stock & Purchase",
			fieldtype="Section Break",
			insert_after="vehicle_details",
		),
		custom_field(
			"Vehicle-stock_id",
			"Vehicle",
			"stock_id",
			"Vehicle Stock ID",
			insert_after="stock_section",
			read_only=1,
			unique=1,
			allow_on_submit=1,
			in_list_view=1,
			description="Generated on purchase. Re-uses the existing vehicle name.",
		),
		custom_field(
			"Vehicle-vin",
			"Vehicle",
			"vin",
			"VIN",
			insert_after="chassis_no",
			unique=1,
			in_list_view=1,
			in_standard_filter=1,
			description="Vehicle Identification Number (VIN) - 17-character chassis number printed on the vehicle.",
		),
		custom_field("Vehicle-year", "Vehicle", "year", "Year", insert_after="model", fieldtype="Int"),
		custom_field(
			"Vehicle-mileage",
			"Vehicle",
			"mileage",
			"Current Mileage",
			insert_after="last_odometer",
			fieldtype="Int",
		),
		custom_field(
			"Vehicle-status",
			"Vehicle",
			"status",
			"Vehicle Status",
			insert_after="stock_id",
			fieldtype="Select",
			options=VEHICLE_STATUSES,
			default="Purchased",
			in_list_view=1,
			in_standard_filter=1,
			allow_on_submit=1,
			search_index=1,
		),
		custom_field(
			"Vehicle-serial_no",
			"Vehicle",
			"serial_no",
			"VIN",
			insert_after="status",
			fieldtype="Link",
			options="Serial No",
			unique=1,
			in_standard_filter=1,
			allow_on_submit=1,
			description=(
				"Vehicle Identification Number (VIN) / chassis number. Entered manually on the "
				"Purchase Receipt - a VIN never changes, so it is not auto-generated."
			),
		),
		custom_field(
			"Vehicle-item_code",
			"Vehicle",
			"item_code",
			"Item Code",
			insert_after="serial_no",
			fieldtype="Link",
			options="Item",
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-warehouse",
			"Vehicle",
			"warehouse",
			"Warehouse",
			insert_after="item_code",
			fieldtype="Link",
			options="Warehouse",
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-company",
			"Vehicle",
			"company",
			"Company",
			insert_after="warehouse",
			fieldtype="Link",
			options="Company",
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-column_break_stock",
			"Vehicle",
			"column_break_stock",
			"",
			fieldtype="Column Break",
			insert_after="company",
		),
		custom_field(
			"Vehicle-purchase_price",
			"Vehicle",
			"purchase_price",
			"Purchase Price",
			insert_after="column_break_stock",
			fieldtype="Currency",
			allow_on_submit=1,
			in_list_view=1,
		),
		custom_field(
			"Vehicle-purchase_date",
			"Vehicle",
			"purchase_date",
			"Purchase Date",
			insert_after="purchase_price",
			fieldtype="Date",
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-purchase_document_type",
			"Vehicle",
			"purchase_document_type",
			"Purchase Document Type",
			insert_after="purchase_date",
			fieldtype="Link",
			options="DocType",
			hidden=1,
			read_only=1,
			no_copy=1,
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-purchase_receipt",
			"Vehicle",
			"purchase_receipt",
			"Purchase Receipt",
			insert_after="purchase_date",
			fieldtype="Dynamic Link",
			options="purchase_document_type",
			no_copy=1,
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-supplier",
			"Vehicle",
			"supplier",
			"Seller",
			insert_after="purchase_receipt",
			fieldtype="Link",
			options="Supplier",
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-seller_name",
			"Vehicle",
			"seller_name",
			"Seller Name (as printed)",
			insert_after="supplier",
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-parking_section",
			"Vehicle",
			"parking_section",
			"Parking",
			fieldtype="Section Break",
			insert_after="seller_name",
			collapsible=1,
		),
		custom_field(
			"Vehicle-parking_location",
			"Vehicle",
			"parking_location",
			"Parking Location",
			insert_after="parking_section",
			fieldtype="Link",
			options="Warehouse",
			description="Yard / park where the vehicle is physically kept.",
		),
		custom_field(
			"Vehicle-parking_from",
			"Vehicle",
			"parking_from",
			"Parked Since",
			insert_after="parking_location",
			fieldtype="Date",
		),
		custom_field(
			"Vehicle-costing_section",
			"Vehicle",
			"costing_section",
			"Costing",
			fieldtype="Section Break",
			insert_after="parking_from",
		),
		custom_field(
			"Vehicle-repair_cost",
			"Vehicle",
			"repair_cost",
			"Repair & Parts Cost",
			insert_after="costing_section",
			fieldtype="Currency",
			read_only=1,
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-other_expense",
			"Vehicle",
			"other_expense",
			"Other Expenses",
			insert_after="repair_cost",
			fieldtype="Currency",
			read_only=1,
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-total_expense",
			"Vehicle",
			"total_expense",
			"Total Expenses",
			insert_after="other_expense",
			fieldtype="Currency",
			read_only=1,
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-column_break_costing",
			"Vehicle",
			"column_break_costing",
			"",
			fieldtype="Column Break",
			insert_after="total_expense",
		),
		custom_field(
			"Vehicle-total_cost",
			"Vehicle",
			"total_cost",
			"Total Cost",
			insert_after="column_break_costing",
			fieldtype="Currency",
			read_only=1,
			allow_on_submit=1,
			in_list_view=1,
		),
		custom_field(
			"Vehicle-selling_price",
			"Vehicle",
			"selling_price",
			"Selling Price",
			insert_after="total_cost",
			fieldtype="Currency",
			read_only=1,
			allow_on_submit=1,
			in_list_view=1,
		),
		custom_field(
			"Vehicle-gross_profit",
			"Vehicle",
			"gross_profit",
			"Sold Profit / Loss",
			insert_after="selling_price",
			fieldtype="Currency",
			read_only=1,
			allow_on_submit=1,
			in_list_view=1,
		),
		custom_field(
			"Vehicle-profit_percent",
			"Vehicle",
			"profit_percent",
			"Profit %",
			insert_after="gross_profit",
			fieldtype="Percent",
			read_only=1,
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-estimated_profit",
			"Vehicle",
			"estimated_profit",
			"Estimated Profit",
			insert_after="profit_percent",
			fieldtype="Currency",
			read_only=1,
			allow_on_submit=1,
			description="Selling price of the open (or last) Sales Order minus total cost.",
		),
		custom_field(
			"Vehicle-sales_order",
			"Vehicle",
			"sales_order",
			"Reserved Against Sales Order",
			insert_after="estimated_profit",
			fieldtype="Link",
			options="Sales Order",
			read_only=1,
			no_copy=1,
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-column_break_sales",
			"Vehicle",
			"column_break_sales",
			"",
			fieldtype="Column Break",
			insert_after="sales_order",
		),
		custom_field(
			"Vehicle-customer",
			"Vehicle",
			"customer",
			"Customer",
			insert_after="column_break_sales",
			fieldtype="Link",
			options="Customer",
			allow_on_submit=1,
		),
		custom_field(
			"Vehicle-sales_invoice",
			"Vehicle",
			"sales_invoice",
			"Sales Invoice",
			insert_after="customer",
			fieldtype="Link",
			options="Sales Invoice",
			read_only=1,
			no_copy=1,
			allow_on_submit=1,
		),
		[
			custom_field(
				"Vehicle-status_history_section",
				"Vehicle",
				"status_history_section",
				"Status History",
				fieldtype="Section Break",
				insert_after="sales_invoice",
				collapsible=1,
			),
			custom_field(
				"Vehicle-status_history",
				"Vehicle",
				"status_history",
				"Status History",
				fieldtype="Table",
				options="Vehicle Status Log",
				insert_after="status_history_section",
				read_only=1,
				no_copy=1,
				allow_on_submit=1,
			),
		],
	]


def sales_order_item_custom_fields():
	return [
		custom_field(
			"Sales Order Item-vehicle",
			"Sales Order Item",
			"vehicle",
			"Vehicle (VIN)",
			insert_after="item_code",
			fieldtype="Link",
			options="Vehicle",
			in_list_view=1,
			columns=2,
			description="Vehicle to reserve for this line (picks its serial number).",
		),
	]


def sales_invoice_item_custom_fields():
	return [
		custom_field(
			"Sales Invoice Item-vehicle",
			"Sales Invoice Item",
			"vehicle",
			"Vehicle (VIN)",
			insert_after="item_code",
			fieldtype="Link",
			options="Vehicle",
			in_list_view=1,
			columns=2,
			print_hide=1,
		),
	]


def stock_reservation_entry_custom_fields():
	return [
		custom_field(
			"Stock Reservation Entry-vehicle",
			"Stock Reservation Entry",
			"vehicle",
			"Vehicle (VIN)",
			insert_after="item_code",
			fieldtype="Link",
			options="Vehicle",
			read_only=1,
			no_copy=1,
			in_list_view=1,
			in_standard_filter=1,
		),
	]


def sales_invoice_custom_fields():
	return [
		custom_field(
			"Sales Invoice-is_vehicle_booking",
			"Sales Invoice",
			"is_vehicle_booking",
			"Is Vehicle Booking",
			insert_after="customer",
			fieldtype="Check",
			print_hide=1,
			description="Booking / advance invoice against a reserved vehicle.",
		),
		custom_field(
			"Sales Invoice-trade_in_vehicle",
			"Sales Invoice",
			"trade_in_vehicle",
			"Trade-in Vehicle",
			insert_after="is_vehicle_booking",
			fieldtype="Link",
			options="Vehicle",
			print_hide=1,
		),
		custom_field(
			"Sales Invoice-trade_in_value",
			"Sales Invoice",
			"trade_in_value",
			"Trade-in Value",
			insert_after="trade_in_vehicle",
			fieldtype="Currency",
			print_hide=1,
		),
	]


def vehicle_expense_type():
	return {
		"doctype": "Vehicle Expense Type",
		"name": "Repairs",
		"expense_category": "Repair & Parts",
		"is_parking": 0,
	}


def vehicle_expense_type_insurance():
	return {
		"doctype": "Vehicle Expense Type",
		"name": "Insurance",
		"expense_category": "Other",
	}


def vehicle_expense_type_registration():
	return {
		"doctype": "Vehicle Expense Type",
		"name": "Registration",
		"expense_category": "Other",
	}


def vehicle_expense_type_transport():
	return {
		"doctype": "Vehicle Expense Type",
		"name": "Transport",
		"expense_category": "Other",
	}


def vehicle_expense_type_inspection():
	return {
		"doctype": "Vehicle Expense Type",
		"name": "Inspection",
		"expense_category": "Other",
	}


def vehicle_expense_type_spare_parts():
	return {
		"doctype": "Vehicle Expense Type",
		"name": "Spare Parts",
		"expense_category": "Repair & Parts",
	}


def vehicle_expense_type_parking():
	return {
		"doctype": "Vehicle Expense Type",
		"name": "Parking",
		"expense_category": "Other",
		"is_parking": 1,
	}


def vehicle_expense_type_other():
	return {
		"doctype": "Vehicle Expense Type",
		"name": "Other",
		"expense_category": "Other",
	}
