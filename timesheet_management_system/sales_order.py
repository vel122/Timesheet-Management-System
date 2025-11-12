import frappe

# custom_on_click


def custom_on_click(doc, method):
	if doc.custom_on_click == 1:
		frappe.throw("Button clicked")
