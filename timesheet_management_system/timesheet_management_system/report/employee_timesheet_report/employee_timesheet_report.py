import calendar
import csv
import io
from datetime import date, timedelta

import frappe
import requests
from frappe import _


def execute(filters=None):
	if not filters:
		return [], []

	employee = filters.get("employee")
	month = int(filters.get("month"))
	year = int(filters.get("year"))

	if not (employee and month and year):
		frappe.throw(_("Please select Employee, Month, and Year"))

	start_date = date(year, month, 1)
	end_date = date(year, month, calendar.monthrange(year, month)[1])

	holiday_lists = frappe.get_all(
		"Holiday List",
		filters={"from_date": [">=", f"{year}-01-01"], "to_date": ["<=", f"{year}-12-31"]},
		fields=["name"],
	)

	holiday_names = [h.name for h in holiday_lists]

	holiday_records = frappe.get_all(
		"Holiday", filters={"parent": ["in", holiday_names]}, fields=["holiday_date"]
	)

	holiday_dates = {h.holiday_date for h in holiday_records if h.holiday_date}

	timesheets = frappe.db.get_all(
		"Timesheet",
		filters={"employee": employee, "start_date": ["between", [start_date, end_date]], "docstatus": 1},
		fields=["name", "start_date", "total_hours"],
	)

	timesheet_details = frappe.db.get_all(
		"Timesheet Detail",
		filters={"parent": ["in", [t.name for t in timesheets]]},
		fields=["parent", "activity_type", "task"],
	)

	task_map = {}
	for d in timesheet_details:
		task_map[d.parent] = {"task": d.task, "activity_type": d.activity_type}

	data_by_date = {
		t.start_date: {"hours": t.total_hours, **task_map.get(t.name, {})} for t in timesheets if t.start_date
	}

	data = []
	total_hours = 0
	pending_dates = []
	holiday_count = 0

	current = start_date
	while current <= end_date:
		if current in holiday_dates:
			data.append([current, 0, "", "", "Holiday"])
			holiday_count += 1
		elif current in data_by_date:
			entry = data_by_date[current]
			hours = entry.get("hours", 0)
			task = entry.get("task", "")
			activity = entry.get("activity_type", "")
			data.append([current, hours, task, activity, "Filled"])
			total_hours += hours
		else:
			data.append([current, 0, "", "", "Pending"])
			pending_dates.append(current)
		current += timedelta(days=1)

	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
		{"label": _("Hours Worked"), "fieldname": "hours", "fieldtype": "Float", "width": 120},
		{"label": _("Task"), "fieldname": "task", "fieldtype": "Data", "width": 150},
		{"label": _("Activity Type"), "fieldname": "activity_type", "fieldtype": "Data", "width": 150},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]

	summary = [
		{"label": _("Total Hours"), "value": total_hours, "indicator": "Blue"},
		{"label": _("Pending Days"), "value": len(pending_dates), "indicator": "Red"},
		{"label": _("Holidays"), "value": holiday_count, "indicator": "Green"},
	]

	return columns, data, None, None, summary


@frappe.whitelist()
def generate_csv_weekly_pending_report():
	today = date.today()

	start_of_week = today - timedelta(days=today.weekday())
	end_of_week = start_of_week + timedelta(days=4)

	holiday_lists = frappe.get_all(
		"Holiday", filters={"holiday_date": ["between", [start_of_week, end_of_week]]}, pluck="holiday_date"
	)

	employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"])

	data = []

	for emp in employees:
		timesheets = frappe.get_all(
			"Timesheet",
			filters={
				"employee": emp.name,
				"start_date": ["between", [start_of_week, end_of_week]],
				"docstatus": 1,
			},
			fields=["start_date"],
		)
		filled_dates = {t.start_date for t in timesheets} if timesheets else set()

		missing_days = []
		current = start_of_week
		while current <= end_of_week:
			if current.weekday() < 5 and current not in holiday_lists and current not in filled_dates:
				missing_days.append(current)
			current += timedelta(days=1)

		if missing_days:
			pending_dates = ", ".join([d.strftime("%Y-%m-%d") for d in missing_days])
			data.append([emp.name, emp.employee_name, pending_dates])

	if not data:
		frappe.msgprint(_("All employees have submitted timesheets for this week!"))
		return

	output = io.StringIO()
	writer = csv.writer(output)
	writer.writerow(["Employee ID", "Employee Name", "Pending Dates"])
	writer.writerows(data)
	csv_data = output.getvalue()
	output.close()

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Pending_Timesheets_{start_of_week.strftime('%W_%Y')}.csv",
			"is_private": 1,
			"content": csv_data,
		}
	)
	file_doc.save(ignore_permissions=True)

	token = frappe.conf.get("telegram_bot_token")
	chat_id = frappe.conf.get("telegram_chat_id")

	if not token or not chat_id:
		frappe.log_error("Missing Telegram bot token or chat_id", "Telegram Config Error")
	else:
		try:
			url = f"https://api.telegram.org/bot{token}/sendDocument"
			files = {"document": (file_doc.file_name, csv_data.encode("utf-8"), "text/csv")}
			data = {"chat_id": chat_id, "caption": f"Pending Timesheets ({start_of_week} → {end_of_week})"}
			response = requests.post(url, data=data, files=files)
			response.raise_for_status()
		except Exception as e:
			frappe.log_error(f"Telegram send failed: {e}", "Telegram Error")

	return {
		"file_url": file_doc.file_url,
		"message": "Pending Timesheets CSV generated and sent to Telegram",
	}


@frappe.whitelist()
def send_weekly_timesheet_report():
	frappe.log("Enqueuing weekly timesheet report generation task")
	frappe.enqueue(
		"timesheet_management_system.report.employee_timesheet_report.employee_timesheet_report.generate_csv_weekly_pending_report",
		queue="long",
	)
