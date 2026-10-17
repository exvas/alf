const VEHICLE_QTY_DOCTYPES = [
	"Purchase Receipt",
	"Purchase Invoice",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
];

VEHICLE_QTY_DOCTYPES.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			enforce_vehicle_qty(frm);
		},
	});

	frappe.ui.form.on(`${doctype} Item`, {
		item_code(frm, cdt, cdn) {
			check_vehicle_row(frm, cdt, cdn);
		},
		qty(frm, cdt, cdn) {
			check_vehicle_row(frm, cdt, cdn);
		},
	});
});

function is_vehicle_row(frm, row) {
	const vehicle_group = (frappe.boot && frappe.boot.alf_vehicle_item_group) || "Vehicles";
	return row.item_group === vehicle_group;
}

function check_vehicle_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row || !is_vehicle_row(frm, row)) {
		return;
	}

	if (flt(row.qty) !== 1) {
		frappe.model.set_value(cdt, cdn, "qty", 1);
		frappe.show_alert({
			message: __("A vehicle is one unit - Quantity set to 1. Add one row per vehicle."),
			indicator: "orange",
		});
	}
}

function enforce_vehicle_qty(frm) {
	(frm.doc.items || []).forEach((row) => {
		if (is_vehicle_row(frm, row) && flt(row.qty) !== 1) {
			frappe.model.set_value(row.doctype, row.name, "qty", 1);
		}
	});
}
