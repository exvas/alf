frappe.ui.form.on("Vehicle Expense", {
	refresh(frm) {
		if (frm.doc.journal_entry) {
			frm.add_custom_button(
				__("Journal Entry"),
				() => frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry),
				__("View")
			);
		}

		if (frm.is_new() || frm.doc.__islocal) {
			frm.trigger("set_filters");
		}
	},

	set_filters(frm) {
		frm.set_query("expense_account", () => ({
			filters: { company: frm.doc.company, is_group: 0, root_type: "Expense" },
		}));
		frm.set_query("paid_from", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},

	company(frm) {
		frm.set_value("cost_center", "");
		frm.set_value("expense_account", "");
		frm.set_value("paid_from", "");
	},

	vehicle(frm) {
		if (!frm.doc.vehicle) {
			return;
		}

		frappe.db.get_doc("Vehicle", frm.doc.vehicle).then((vehicle) => {
			frm.set_value("company", vehicle.company);
			frm.set_value("vehicle_status", vehicle.status);
		});
	},
});
