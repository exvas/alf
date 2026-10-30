const HIDDEN_FIELDS = [
	"rejected_warehouse",
	"is_subcontracted",
	"supplier_warehouse",
	"is_old_subcontracting_flow",
	"subcontracting_receipt",
	"raw_material_details",
	"scan_barcode",
	"shipping_rule",
	"incoterm",
	"project",
	"cost_center",
];

frappe.ui.form.on("Purchase Receipt", {
	refresh(frm) {
		hide_fields(frm);

		if (frm.doc.docstatus !== 0) {
			return;
		}

		add_grid_vin_button(frm);
	},
});

function hide_fields(frm) {
	HIDDEN_FIELDS.forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "hidden", 1);
		}
	});
}

function add_grid_vin_button(frm) {
	const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
	if (!grid || !grid.wrapper) {
		return;
	}

	const footer = grid.wrapper.find(".grid-buttons");
	if (!footer.length || footer.find(".alf-add-vin-btn").length) {
		return;
	}

	$(
		`<button type="button" class="btn btn-xs btn-secondary alf-add-vin-btn">
			${__("Add VIN")}
		</button>`
	)
		.on("click", () => open_vin_dialog(frm))
		.appendTo(footer);
}

function open_vin_dialog(frm) {
	const rows = (frm.doc.items || [])
		.filter((row) => row.item_code)
		.map((row) => ({
			item_row: row.name,
			item_code: row.item_code,
			qty: row.qty,
			vin: (row.serial_no || "").split("\n").filter(Boolean).join("\n"),
		}));

	if (!rows.length) {
		frappe.msgprint(__("Add at least one item row first."));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Update VIN"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "vin_hint",
				options: `<p class="text-muted small">${__(
					"Enter the VIN (chassis number) printed on the vehicle."
				)}</p>`,
			},
			{
				fieldname: "vins",
				fieldtype: "Table",
				label: __("Items"),
				in_place_edit: true,
				cannot_add_rows: true,
				cannot_delete_rows: true,
				data: rows,
				fields: [
					{
						fieldname: "vin",
						fieldtype: "Data",
						label: __("VIN"),
						in_list_view: 1,
						in_place_edit: 1,
						columns: 5,
					},
					{
						fieldname: "item_code",
						fieldtype: "Link",
						options: "Item",
						label: __("Item Code"),
						in_list_view: 1,
						read_only: 1,
						columns: 3,
					},
					{
						fieldname: "qty",
						fieldtype: "Float",
						label: __("Qty"),
						in_list_view: 1,
						read_only: 1,
						columns: 1,
					},
				],
			},
		],
		primary_action_label: __("Update VINs"),
		primary_action(values) {
			apply_vins(frm, dialog, values.vins);
		},
	});

	dialog.show();
	dialog.fields_dict.vins.grid.refresh();
}

function apply_vins(frm, dialog, vins) {
	const updates = [];
	const problems = [];
	const all_vins = [];

	(vins || []).forEach((entry) => {
		const row = (frm.doc.items || []).find((item) => item.name === entry.item_row);
		if (!row) {
			return;
		}

		const vins_for_row = String(entry.vin || "")
			.split(/[\n,]+/)
			.map((value) => value.trim())
			.filter(Boolean);

		if (!vins_for_row.length) {
			updates.push({ row, vins: [] });
			return;
		}

		if (vins_for_row.length !== flt(row.qty)) {
			problems.push(
				__("Row #{0} ({1}): {2} VIN(s) entered for Qty {3}.", [
					row.idx,
					row.item_code,
					vins_for_row.length,
					row.qty,
				])
			);
		}

		const seen = new Set();
		vins_for_row.forEach((value) => {
			if (seen.has(value)) {
				problems.push(__("Row #{0}: {1} is entered twice.", [row.idx, value]));
			}
			seen.add(value);
			all_vins.push(value);
		});

		updates.push({ row, vins: vins_for_row });
	});

	const write = () => {
		updates.forEach(({ row, vins: row_vins }) => {
			frappe.model.set_value(row.doctype, row.name, "use_serial_batch_fields", 1);
			frappe.model.set_value(row.doctype, row.name, "serial_no", row_vins.join("\n"));
		});

		frm.refresh_field("items");
		frm.dirty();
		dialog.hide();
		frappe.show_alert({
			message: __("VIN updated on {0} row(s).", [updates.length]),
			indicator: "green",
		});

		if (problems.length) {
			frappe.msgprint({
				title: __("Check these rows"),
				indicator: "orange",
				message: problems.join("<br>"),
			});
		}
	};

	if (!all_vins.length) {
		write();
		return;
	}

	frappe.call({
		method: "alf.alf.custom.check_vin_duplicates",
		args: { vins: all_vins },
		callback: (response) => {
			const duplicates = response.message || [];
			if (duplicates.length) {
				problems.push(
					__("Already used in stock or returned in this document: {0}", [
						duplicates.join(", "),
					])
				);
			}
			write();
		},
	});
}
