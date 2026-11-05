// Show the selected ledger's balance (as on the posting date) in the accounts grid.
frappe.provide("alf.journal_entry");

alf.journal_entry.set_account_balances = function (frm, rows) {
	rows = (rows || frm.doc.accounts || []).filter((row) => row.account);
	if (!rows.length || frm.doc.docstatus !== 0) {
		return;
	}

	return frappe.call({
		method: "alf.alf.journal_entry.get_account_balances",
		args: {
			accounts: rows.map((row) => row.account),
			date: frm.doc.posting_date,
			company: frm.doc.company,
		},
		callback(r) {
			const balances = r.message || {};
			rows.forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, "account_balance", balances[row.account] || 0);
			});
		},
	});
};

frappe.ui.form.on("Journal Entry", {
	onload_post_render(frm) {
		// New / duplicated / system-created drafts arrive with accounts already filled.
		if (frm.is_new()) {
			alf.journal_entry.set_account_balances(frm);
		}
	},

	posting_date(frm) {
		alf.journal_entry.set_account_balances(frm);
	},
});

frappe.ui.form.on("Journal Entry Account", {
	account(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.account) {
			frappe.model.set_value(cdt, cdn, "account_balance", 0);
			return;
		}
		alf.journal_entry.set_account_balances(frm, [row]);
	},
});
