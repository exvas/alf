app_name = "alf"
app_title = "Alf"
app_publisher = "sammish"
app_description = "alf cars"
app_email = "sammish.thundiyil@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "alf",
# 		"logo": "/assets/alf/logo.png",
# 		"title": "Alf",
# 		"route": "/alf",
# 		"has_permission": "alf.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/alf/css/alf.css"
# app_include_js = "/assets/alf/js/alf.js"

# include js, css files in header of web template
# web_include_css = "/assets/alf/css/alf.css"
# web_include_js = "/assets/alf/js/alf.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "alf/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
	"Vehicle": "public/js/vehicle.js",
	"Vehicle Expense": "public/js/vehicle_expense.js",
	"Purchase Receipt": ["public/js/purchase_receipt.js", "public/js/vehicle_qty.js"],
	"Purchase Invoice": "public/js/vehicle_qty.js",
	"Sales Order": ["public/js/sales_order_item.js", "public/js/vehicle_qty.js"],
	"Delivery Note": "public/js/vehicle_qty.js",
	"Sales Invoice": ["public/js/sales_invoice.js", "public/js/vehicle_qty.js"],
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "alf/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "alf.utils.jinja_methods",
# 	"filters": "alf.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "alf.install.before_install"
# after_install = "alf.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "alf.uninstall.before_uninstall"
# after_uninstall = "alf.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "alf.utils.before_app_install"
# after_app_install = "alf.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "alf.utils.before_app_uninstall"
# after_app_uninstall = "alf.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "alf.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Receipt": {
		"validate": "alf.alf.events.validate_vehicle_qty",
		"before_submit": "alf.alf.events.purchase_receipt_before_submit",
		"on_submit": "alf.alf.events.purchase_receipt_on_submit",
	},
	"Purchase Invoice": {
		"validate": [
			"alf.alf.events.validate_vehicle_qty",
			"alf.alf.events.set_vehicle_dimension",
		],
	},
	"Sales Order": {
		"validate": [
			"alf.alf.events.validate_vehicle_qty",
			"alf.alf.events.set_vehicle_dimension",
		],
	},
	"Delivery Note": {
		"validate": [
			"alf.alf.events.validate_vehicle_qty",
			"alf.alf.events.set_vehicle_dimension",
		],
		"on_submit": "alf.alf.events.delivery_note_on_submit",
	},
	"Stock Reservation Entry": {
		"on_submit": "alf.alf.events.stock_reservation_entry_on_submit",
		"on_cancel": "alf.alf.events.stock_reservation_entry_on_cancel",
	},
	"Stock Entry": {
		"validate": "alf.alf.events.validate_vehicle_qty",
	},
	"Sales Invoice": {
		"validate": [
			"alf.alf.events.validate_vehicle_qty",
			"alf.alf.events.set_vehicle_dimension",
		],
		"on_submit": "alf.alf.events.sales_invoice_on_submit",
		"on_cancel": "alf.alf.events.sales_invoice_on_cancel",
	},
	"Vehicle Expense": {
		"on_submit": "alf.alf.events.vehicle_expense_on_submit",
		"on_cancel": "alf.alf.events.vehicle_expense_on_cancel",
	},
	"Vehicle": {
		"validate": "alf.alf.events.vehicle_on_validate",
	},
	"Accounting Dimension": {
		"validate": "alf.alf.events.accounting_dimension_on_validate",
	},
}

# Fixtures
# --------
# Custom fields on ERPNext doctypes are declared in `alf/fixtures` so no core
# ERPNext file is touched. The Sales Order Item script adds the `Vehicle` picker.

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Alf"]]},
	{"dt": "Vehicle Expense Type"},
	{"dt": "Number Card", "filters": [["module", "=", "Alf"]]},
	{"dt": "Dashboard Chart", "filters": [["module", "=", "Alf"]]},
	{"dt": "Dashboard", "filters": [["module", "=", "Alf"]]},
	{"dt": "Workspace", "filters": [["module", "=", "Alf"]]},
	{"dt": "Desktop Icon", "filters": [["module", "=", "Alf"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Alf"]]},
]

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"alf.tasks.all"
# 	],
# 	"daily": [
# 		"alf.tasks.daily"
# 	],
# 	"hourly": [
# 		"alf.tasks.hourly"
# 	],
# 	"weekly": [
# 		"alf.tasks.weekly"
# 	],
# 	"monthly": [
# 		"alf.tasks.monthly"
# 	],
# }

# Boot
# ----
boot_session = "alf.alf.boot.boot_session"

# Testing
# -------

# before_tests = "alf.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "alf.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "alf.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["alf.utils.before_request"]
# after_request = ["alf.utils.after_request"]

# Job Events
# ----------
# before_job = ["alf.utils.before_job"]
# after_job = ["alf.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"alf.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
