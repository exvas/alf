"""Workspace, dashboard and number cards for the ALF Cars desk.

Everything is declared as fixtures so `bench migrate` recreates it on any site.
Console order: number cards -> charts -> dashboard -> workspace (sequence_id 1 so
it is the first workspace in the sidebar).
"""

import hashlib
import json

SEQUENCE_ID = 1
ICON = "quality"
GREY = "#8D99A6"
GREEN = "#29CD42"
ORANGE = "#FF8D00"
YELLOW = "#FACF7B"
BLUE = "#2490EF"
RED = "#E03636"
PURPLE = "#7C3AED"

VEHICLE_IDLE = ["Purchased", "In Repair", "Ready for Sale", "Parked"]
VEHICLE_RESERVED = ["Reserved"]


def _id(seed):
	return hashlib.md5(seed.encode()).hexdigest()[:10]


def number_card(name, document_type, function, filters, aggregate_function_based_on=None, stats="Monthly"):
	return {
		"doctype": "Number Card",
		"name": name,
		"label": name,
		"type": "Document Type",
		"document_type": document_type,
		"function": function,
		"aggregate_function_based_on": aggregate_function_based_on,
		"filters_json": json.dumps(filters),
		"is_public": 1,
		"show_percentage_stats": 1,
		"stats_time_interval": stats,
		"module": "Alf",
		"color": None,
	}


def number_cards():
	return [
		number_card(
			"Total Vehicles in Stock",
			"Vehicle",
			"Count",
			[["Vehicle", "status", "in", VEHICLE_IDLE, False]],
		),
		number_card(
			"Vehicles Reserved",
			"Vehicle",
			"Count",
			[["Vehicle", "status", "in", VEHICLE_RESERVED, False]],
		),
		number_card(
			"Vehicles Sold",
			"Vehicle",
			"Count",
			[["Vehicle", "status", "=", "Sold", False]],
		),
		number_card(
			"Stock Value",
			"Vehicle",
			"Sum",
			[["Vehicle", "status", "in", VEHICLE_IDLE, False]],
			aggregate_function_based_on="total_cost",
			stats="Monthly",
		),
		number_card(
			"Vehicles In Repair",
			"Vehicle",
			"Count",
			[["Vehicle", "status", "=", "In Repair", False]],
			stats="Weekly",
		),
		number_card(
			"Vehicle Expenses",
			"Vehicle Expense",
			"Sum",
			[
				["Vehicle Expense", "docstatus", "=", 1, False],
				["Vehicle Expense", "posting_date", "Timespan", "this month", False],
			],
			aggregate_function_based_on="amount",
			stats="Monthly",
		),
		number_card(
			"Repair Cost (This Month)",
			"Vehicle Expense",
			"Sum",
			[
				["Vehicle Expense", "docstatus", "=", 1, False],
				["Vehicle Expense", "expense_category", "=", "Repair & Parts", False],
				["Vehicle Expense", "posting_date", "Timespan", "this month", False],
			],
			aggregate_function_based_on="amount",
			stats="Monthly",
		),
		number_card(
			"Active Reservations",
			"Stock Reservation Entry",
			"Count",
			[
				["Stock Reservation Entry", "docstatus", "=", 1, False],
				["Stock Reservation Entry", "vehicle", "is", "set", False],
				["Stock Reservation Entry", "status", "not in", ["Delivered", "Cancelled"], False],
			],
			stats="Weekly",
		),
		number_card(
			"Open Sales Orders",
			"Sales Order",
			"Count",
			[
				["Sales Order", "status", "in", ["To Deliver and Bill", "To Deliver", "To Bill"], False],
				["Sales Order", "docstatus", "=", 1, False],
			],
			stats="Weekly",
		),
		number_card(
			"Vehicle Sales This Year",
			"Sales Invoice",
			"Sum",
			[
				["Sales Invoice", "docstatus", "=", 1, False],
				["Sales Invoice", "posting_date", "Timespan", "this year", False],
			],
			aggregate_function_based_on="base_grand_total",
			stats="Yearly",
		),
	]


def charts():
	return [
		{
			"doctype": "Dashboard Chart",
			"name": "Vehicle Status",
			"chart_name": "Vehicle Status",
			"chart_type": "Group By",
			"document_type": "Vehicle",
			"based_on": "status",
			"group_by_based_on": "status",
			"group_by_type": "Count",
			"type": "Donut",
			"number_of_groups": 0,
			"filters_json": json.dumps([["Vehicle", "status", "is", "set", False]]),
			"is_public": 1,
			"module": "Alf",
			"color": None,
			"timespan": "Last Year",
			"time_interval": "Monthly",
		},
		{
			"doctype": "Dashboard Chart",
			"name": "Vehicle Profitability (Sold)",
			"chart_name": "Vehicle Profitability (Sold)",
			"chart_type": "Group By",
			"document_type": "Vehicle",
			"based_on": "status",
			"group_by_based_on": "status",
			"group_by_type": "Sum",
			"aggregate_function_based_on": "gross_profit",
			"type": "Bar",
			"number_of_groups": 0,
			"filters_json": json.dumps([["Vehicle", "sales_invoice", "is", "set", False]]),
			"is_public": 1,
			"module": "Alf",
			"color": GREEN,
			"timespan": "Last Year",
			"time_interval": "Monthly",
		},
		{
			"doctype": "Dashboard Chart",
			"name": "Vehicle Expenses by Type",
			"chart_name": "Vehicle Expenses by Type",
			"chart_type": "Group By",
			"document_type": "Vehicle Expense",
			"based_on": "expense_type",
			"group_by_based_on": "expense_type",
			"group_by_type": "Sum",
			"aggregate_function_based_on": "amount",
			"type": "Bar",
			"number_of_groups": 0,
			"filters_json": json.dumps([["Vehicle Expense", "docstatus", "=", 1, False]]),
			"is_public": 1,
			"module": "Alf",
			"color": ORANGE,
			"timespan": "Last Year",
			"time_interval": "Monthly",
		},
		{
			"doctype": "Dashboard Chart",
			"name": "Monthly Vehicle Expenses",
			"chart_name": "Monthly Vehicle Expenses",
			"chart_type": "Group By",
			"document_type": "Vehicle Expense",
			"based_on": "posting_date",
			"group_by_based_on": "expense_type",
			"group_by_type": "Sum",
			"aggregate_function_based_on": "amount",
			"type": "Line",
			"based_on_date_field": "posting_date",
			"number_of_groups": 0,
			"filters_json": json.dumps([["Vehicle Expense", "docstatus", "=", 1, False]]),
			"is_public": 1,
			"module": "Alf",
			"color": BLUE,
			"timespan": "Last Year",
			"time_interval": "Monthly",
		},
		{
			"doctype": "Dashboard Chart",
			"name": "Vehicle Sales (Invoiced)",
			"chart_name": "Vehicle Sales (Invoiced)",
			"chart_type": "Sum",
			"document_type": "Sales Invoice",
			"based_on": "posting_date",
			"value_based_on": "base_grand_total",
			"type": "Bar",
			"filters_json": json.dumps([["Sales Invoice", "docstatus", "=", 1, False]]),
			"is_public": 1,
			"module": "Alf",
			"color": PURPLE,
			"timespan": "Last Year",
			"time_interval": "Monthly",
		},
		{
			"doctype": "Dashboard Chart",
			"name": "Reserved Vehicles",
			"chart_name": "Reserved Vehicles",
			"chart_type": "Count",
			"document_type": "Stock Reservation Entry",
			"based_on": "creation",
			"type": "Line",
			"filters_json": json.dumps(
				[
					["Stock Reservation Entry", "docstatus", "=", 1, False],
					["Stock Reservation Entry", "vehicle", "is", "set", False],
				]
			),
			"is_public": 1,
			"module": "Alf",
			"color": YELLOW,
			"timespan": "Last Year",
			"time_interval": "Monthly",
		},
	]


def dashboard():
	return {
		"doctype": "Dashboard",
		"name": "ALF Cars",
		"dashboard_name": "ALF Cars",
		"is_standard": 1,
		"is_default": 1,
		"module": "Alf",
		"cards": [{"card": card["name"]} for card in number_cards()],
		"charts": [{"chart": chart["name"]} for chart in charts()],
	}


def _content():
	blocks = []
	blocks.append(
		{
			"id": _id("header-cards"),
			"type": "header",
			"data": {"text": '<span class="h4"><b>Quick Numbers</b></span>', "col": 12},
		}
	)
	for card in number_cards():
		blocks.append(
			{
				"id": _id(f"nc-{card['name']}"),
				"type": "number_card",
				"data": {"number_card_name": card["name"], "col": 3},
			}
		)

	blocks.append({"id": _id("spacer-1"), "type": "spacer", "data": {"col": 12}})
	blocks.append(
		{
			"id": _id("header-charts"),
			"type": "header",
			"data": {"text": '<span class="h4"><b>Charts</b></span>', "col": 12},
		}
	)
	for chart in charts():
		blocks.append(
			{
				"id": _id(f"ch-{chart['name']}"),
				"type": "chart",
				"data": {"chart_name": chart["name"], "col": 6},
			}
		)

	blocks.append({"id": _id("spacer-2"), "type": "spacer", "data": {"col": 12}})
	blocks.append(
		{
			"id": _id("header-shortcuts"),
			"type": "header",
			"data": {"text": '<span class="h4"><b>Quick Access</b></span>', "col": 12},
		}
	)
	for index, shortcut in enumerate(shortcuts()):
		blocks.append(
			{
				"id": _id(f"sc-{index}-{shortcut.get('label')}"),
				"type": "shortcut",
				"data": {"shortcut_name": shortcut.get("label"), "col": 3},
			}
		)

	blocks.append({"id": _id("spacer-3"), "type": "spacer", "data": {"col": 12}})
	cards = [
		("Vehicle Inventory", 4),
		("Vehicle Sales", 4),
		("Vehicle Expenses", 4),
		("Reports", 4),
		("Stock Reservation", 4),
		("Settings", 4),
	]
	for label, col in cards:
		blocks.append({"id": _id(f"card-{label}"), "type": "card", "data": {"card_name": label, "col": col}})

	return json.dumps(blocks)


def shortcuts():
	def doctype(label, link_to, color=None, fmt=None, stats_filter=None):
		shortcut = {"type": "DocType", "link_to": link_to, "label": label, "doc_view": "List"}
		if color:
			shortcut["color"] = color
		if fmt:
			shortcut["format"] = fmt
		if stats_filter:
			shortcut["stats_filter"] = json.dumps(stats_filter)
		return shortcut

	def report(label, link_to, report_ref_doctype):
		return {
			"type": "Report",
			"link_to": link_to,
			"label": label,
			"report_ref_doctype": report_ref_doctype,
		}

	def dashboard(label, link_to):
		return {"type": "Dashboard", "link_to": link_to, "label": label}

	return [
		doctype("Purchase Receipt", "Purchase Receipt", GREY),
		doctype(
			"Vehicle",
			"Vehicle",
			GREEN,
			"{} In Stock",
			{"status": ["in", VEHICLE_IDLE]},
		),
		doctype(
			"Sales Order",
			"Sales Order",
			YELLOW,
			"{} Booked",
			{"status": ["in", ["To Deliver and Bill", "To Deliver"]]},
		),
		doctype(
			"Vehicle Expense",
			"Vehicle Expense",
			ORANGE,
			"{} This Month",
			{"posting_date": ["Timespan", "this month"]},
		),
		report("Vehicle Reservation", "Vehicle Reservation", "Stock Reservation Entry"),
		report("Vehicle Profitability", "Vehicle Profitability", "Vehicle"),
		doctype("Sales Invoice", "Sales Invoice", BLUE),
		dashboard("ALF Cars Dashboard", "ALF Cars"),
	]


def _link(card, link_type, link_to, label=None, onboard=0, is_query_report=0, report_ref_doctype=None):
	link = {
		"type": "Link",
		"label": label or link_to,
		"link_type": link_type,
		"link_to": link_to if link_type != "Dashboard" else None,
		"hidden": 0,
		"onboard": onboard,
		"is_query_report": is_query_report,
		"link_count": 0,
	}
	if report_ref_doctype:
		link["report_ref_doctype"] = report_ref_doctype
	if link_type == "Dashboard":
		link["dependencies"] = ""
	return link


def links():
	def card(label):
		return {"type": "Card Break", "label": label, "link_count": 0, "hidden": 0, "onboard": 0}

	rows = [card("Vehicle Inventory")]
	for label, doctype in (
		("Vehicle", "Vehicle"),
		("Purchase Receipt", "Purchase Receipt"),
		("Item", "Item"),
		("Warehouse", "Warehouse"),
	):
		rows.append(
			_link("Vehicle Inventory", "DocType", doctype, label, onboard=1 if doctype == "Vehicle" else 0)
		)

	rows.append(card("Vehicle Sales"))
	for label, doctype in (
		("Sales Order", "Sales Order"),
		("Delivery Note", "Delivery Note"),
		("Sales Invoice", "Sales Invoice"),
		("Customer", "Customer"),
		("Payment Entry", "Payment Entry"),
	):
		rows.append(_link("Vehicle Sales", "DocType", doctype, label))

	rows.append(card("Vehicle Expenses"))
	for label, doctype in (
		("Vehicle Expense", "Vehicle Expense"),
		("Vehicle Expense Type", "Vehicle Expense Type"),
		("Journal Entry", "Journal Entry"),
		("Supplier", "Supplier"),
	):
		rows.append(
			_link(
				"Vehicle Expenses",
				"DocType",
				doctype,
				label,
				onboard=1 if doctype == "Vehicle Expense" else 0,
			)
		)

	rows.append(card("Reports"))
	for label, doctype in (
		("Vehicle Reservation", "Vehicle Reservation"),
		("Vehicle Profitability", "Vehicle Profitability"),
	):
		rows.append(_link("Reports", "Report", label, label, is_query_report=1, report_ref_doctype=doctype))

	rows.append(card("Stock Reservation"))
	for label, doctype in (
		("Stock Reservation Entry", "Stock Reservation Entry"),
		("Serial No", "Serial No"),
	):
		rows.append(_link("Stock Reservation", "DocType", doctype, label))

	rows.append(card("Settings"))
	for label, doctype in (
		("Stock Settings", "Stock Settings"),
		("Company", "Company"),
		("Item Group", "Item Group"),
		("UOM", "UOM"),
		("Vehicle Expense Type", "Vehicle Expense Type"),
	):
		rows.append(_link("Settings", "DocType", doctype, label))

	return rows


def workspace():
	return {
		"doctype": "Workspace",
		"name": "ALF Cars",
		"label": "ALF Cars",
		"title": "ALF Cars",
		"module": "Alf",
		"icon": ICON,
		"indicator_color": "green",
		"sequence_id": SEQUENCE_ID,
		"public": 1,
		"is_hidden": 0,
		"hide_custom": 0,
		"restrict_to_domain": None,
		"parent_page": None,
		"for_user": None,
		"content": _content(),
		"number_cards": [{"number_card_name": card["name"]} for card in number_cards()[:4]],
		"charts": [{"chart_name": "Vehicle Status", "label": "Vehicle Status"}],
		"shortcuts": shortcuts(),
		"links": links(),
		"quick_lists": [],
		"custom_blocks": [],
		"roles": [],
	}
