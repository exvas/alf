frappe.ui.form.on("Sales Order Item", {
	vehicle(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.vehicle) {
			return;
		}

		frappe.db.get_doc("Vehicle", row.vehicle).then((vehicle) => {
			if (!vehicle.serial_no) {
				frappe.msgprint(
					__("Vehicle {0} has no Serial No, so it cannot be reserved.", [row.vehicle])
				);
				return;
			}
			if (["Sold", "Delivered"].includes(vehicle.status)) {
				frappe.msgprint(
					__("Vehicle {0} is already {1} and cannot be reserved.", [
						row.vehicle,
						__(vehicle.status),
					])
				);
				return;
			}

			if (vehicle.item_code && vehicle.item_code !== row.item_code) {
				frappe.model.set_value(cdt, cdn, "item_code", vehicle.item_code);
				if (vehicle.item_name) {
					frappe.model.set_value(cdt, cdn, "item_name", vehicle.item_name);
				}
				if (vehicle.stock_uom) {
					frappe.model.set_value(cdt, cdn, "uom", vehicle.stock_uom);
				}
			}

			frappe.model.set_value(cdt, cdn, "reserve_stock", 1);
			frappe.model.set_value(cdt, cdn, "qty", 1);
			if (vehicle.warehouse) {
				frappe.model.set_value(cdt, cdn, "warehouse", vehicle.warehouse);
			}
		});
	},
});
