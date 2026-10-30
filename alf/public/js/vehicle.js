frappe.ui.form.on("Vehicle", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frm.doc.serial_no && frm.doc.status !== "Sold" && frm.doc.status !== "Delivered") {
			frm.add_custom_button(__("Reserved Stock"), () => show_reservations(frm), __("Stock"));
		}

		if (!frm.is_dirty() && frm.doc.status && frm.doc.status !== "Sold") {
			frm.add_custom_button(
				__("Mark Ready for Sale"),
				() => set_status(frm, "Ready for Sale"),
				__("Stock")
			);
			frm.add_custom_button(__("Mark Parked"), () => set_status(frm, "Parked"), __("Stock"));
			frm.add_custom_button(
				__("Mark In Repair"),
				() => set_status(frm, "In Repair"),
				__("Stock")
			);
		}

		if (frm.doc.sales_order) {
			frm.add_custom_button(
				__("Sales Order"),
				() => frappe.set_route("Form", "Sales Order", frm.doc.sales_order),
				__("View")
			);
		}
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(
				__("Sales Invoice"),
				() => frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice),
				__("View")
			);
		}
		if (frm.doc.purchase_receipt) {
			frm.add_custom_button(
				__("Purchase Receipt"),
				() => frappe.set_route("Form", "Purchase Receipt", frm.doc.purchase_receipt),
				__("View")
			);
		}

		if (frm.doc.status === "Reserved") {
			frm.dashboard.set_headline(
				__("{0}", [__("Reserved against Sales Order {0}", [frm.doc.sales_order || "-"])])
			);
		}
	},

	last_odometer(frm) {
		if (!frm.doc.mileage) {
			frm.set_value("mileage", frm.doc.last_odometer);
		}
	},
});

function set_status(frm, status) {
	frappe.confirm(__("Set vehicle {0} to {1}?", [frm.doc.name, __(status)]), () => {
		frm.set_value("status", status);
		frm.save("Update");
	});
}

function show_reservations(frm) {
	frappe.route_options = {
		voucher_type: frm.doc.sales_order ? "Sales Order" : null,
		voucher_no: frm.doc.sales_order || null,
	};
	frappe.set_route("query-report", "Vehicle Reservation");
}
