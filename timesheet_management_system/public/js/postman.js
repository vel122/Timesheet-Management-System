// frappe.ui.form.on('summa', {
//     is_timesheet_required: function(frm) {
//         frappe.call({
//             method: 'timesheet_management_system.postman.create_summa_order_custom_fields',
//             args: {},
//             onlclick: function (r) {
//                 if (r.message) {
//                     frappe.msgprint("Custom fields created successfully");
//                 }

//             }
//         });
//     }
// });

frappe.ui.form.on("summa", {
	is_timesheet_required: function (frm) {
		frappe.throw(__("Button clicked!"));
	},
});
