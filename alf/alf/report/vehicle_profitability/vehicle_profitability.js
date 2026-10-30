frappe.query_reports["Vehicle Profitability"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "status",
			label: __("Vehicle Status"),
			fieldtype: "Select",
			options: [
				"",
				"Purchased",
				"In Repair",
				"Ready for Sale",
				"Parked",
				"Reserved",
				"Delivered",
				"Sold",
			],
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
	],
};
