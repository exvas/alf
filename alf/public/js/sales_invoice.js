frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.trade_in_vehicle) {
			frm.add_custom_button(
				__("Trade-in Vehicle"),
				() => frappe.set_route("Form", "Vehicle", frm.doc.trade_in_vehicle),
				__("View")
			);
		}
	},

	trade_in_vehicle(frm) {
		if (!frm.doc.trade_in_vehicle) {
			return;
		}

		frappe.db.get_doc("Vehicle", frm.doc.trade_in_vehicle).then((vehicle) => {
			if (vehicle.status === "Sold") {
				frappe.msgprint(__("Vehicle {0} is already sold and cannot be taken in as trade-in.", [vehicle.name]));
				frm.set_value("trade_in_vehicle", "");
			}
		});
	},

	is_vehicle_booking(frm) {
		if (frm.doc.is_vehicle_booking) {
			frm.dashboard.set_headline(__("This invoice only records the vehicle booking / advance."));
		}
	},
});
