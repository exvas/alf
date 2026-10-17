frappe.query_reports["Vehicle Reservation"] = {
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
			options: ["", "Purchased", "In Repair", "Ready for Sale", "Parked", "Reserved", "Delivered", "Sold"],
		},
		{
			fieldname: "vehicle",
			label: __("Vehicle"),
			fieldtype: "Link",
			options: "Vehicle",
		},
	],
};
