# from turtle import onclick
# import frappe
# from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
# @frappe.whitelist()
# def create_summa_order_custom_fields():
#     custom_fields = {
#         "summa": [
#             {
#                 "fieldname": "is_timesheet_required",
#                 "label": "Is Timesheet Required",
#                 "fieldtype": "Button",
#                 "default": 0,
#             }
#         ]
#     }
#     create_custom_fields(custom_fields)

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


@frappe.whitelist()
def create_summa_order_custom_fields():
	custom_fields = {
		"summa": [
			{
				"fieldname": "is_timesheet_required",
				"label": "Is Timesheet Required",
				"fieldtype": "Button",
			}
		]
	}

	create_custom_fields(custom_fields)
	# frappe.msgprint("Custom field created successfully")


@frappe.whitelist(allow_guest=True)
def greet(name):
	frappe.msgprint(f"hello {name} from aerele")
	return "OK"
