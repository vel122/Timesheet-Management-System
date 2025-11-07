import json
from datetime import date, timedelta

import frappe
import requests


@frappe.whitelist(allow_guest=True)
def telegram_webhook():
	try:
		try:
			data = json.loads(frappe.request.data or "{}")
		except Exception:
			data = {}

		message = data.get("message", {})
		text = (message.get("text") or "").strip()
		chat_id = message.get("chat", {}).get("id")

		if not text or not chat_id:
			return "No message or chat_id found"

		bot_token = frappe.conf.get("telegram_bot_token")
		telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

		all_employees = frappe.get_all(
			"Employee", fields=["name", "employee_name"], filters={"status": "Active"}
		)

		today = date.today()
		start_of_week = today - timedelta(days=today.weekday())
		end_of_week = start_of_week + timedelta(days=4)

		timesheets = frappe.get_all(
			"Timesheet",
			filters={"start_date": ["between", [start_of_week, end_of_week]], "docstatus": 1},
			fields=["employee", "start_date", "total_hours"],
		)

		holiday_list = frappe.get_all(
			"Holiday",
			filters={"holiday_date": ["between", [start_of_week, end_of_week]]},
			pluck="holiday_date",
		)

		if text.lower() == "/employee":
			if all_employees:
				msg = "\n".join([f"{e.employee_name} (`{e.name}`)" for e in all_employees])
			else:
				msg = "No active employees found."
			payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
			requests.post(telegram_url, json=payload)
			return "OK"

		elif text.lower() == "/timesheet":
			report_date = today - timedelta(days=1)
			if report_date.weekday() == 6:  # Sunday
				report_date -= timedelta(days=2)
			elif report_date.weekday() == 5:  # Saturday
				report_date -= timedelta(days=1)
			elif report_date.weekday() == 0:  # Monday
				report_date -= timedelta(days=3)

			filled_timesheets = frappe.get_all(
				"Timesheet", filters={"start_date": report_date, "docstatus": 1}, fields=["employee"]
			)
			filled_emp_ids = {t.employee for t in filled_timesheets}

			draft_timesheets = frappe.get_all(
				"Timesheet", filters={"start_date": report_date, "docstatus": 0}, fields=["employee"]
			)
			draft_emp_ids = {t.employee for t in draft_timesheets}

			leave_applications = frappe.get_all(
				"Leave Application",
				filters={"from_date": ["<=", report_date], "to_date": [">=", report_date]},
				fields=["employee"],
			)
			leave_ids = {la.employee for la in leave_applications}

			holiday = frappe.db.exists("Holiday", {"holiday_date": report_date})

			filled_list, draft, pending, pending_on_leave = [], [], [], []

			for emp in all_employees:
				if emp.name in filled_emp_ids:
					filled_list.append(f"{emp.employee_name}")
				elif emp.name in draft_emp_ids:
					draft.append(f"{emp.employee_name}")
				elif emp.name in leave_ids:
					pending_on_leave.append(f"{emp.employee_name} (Leave Request Raised)")
				else:
					pending.append(f"{emp.employee_name}")

			msg = f"*Timesheet Summary for {report_date.strftime('%Y-%m-%d')}:*\n\n"
			if holiday:
				msg += "            *Today is a Holiday*\n\n"

			msg += "*Filled*\n" + ("\n".join(filled_list)) + "\n\n"
			if pending:
				msg += "*Not Filled*\n" + "\n".join(pending) + "\n\n"
			if draft:
				msg += "*Draft*\n" + "\n".join(draft) + "\n\n"
			if pending_on_leave:
				msg += "*Leave*\n" + "\n".join(pending_on_leave) + "\n\n"
			if not (filled_list or pending or draft or pending_on_leave):
				msg += "*Everyone has filled their timesheet!*"

			payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
			requests.post(telegram_url, json=payload)
			return "OK"

		elif text.lower() == "/weeklyhours":
			if not timesheets:
				msg = f"No timesheet data found for this week ({start_of_week} → {end_of_week})."
			else:
				msg = f"*Weekly Hours* ({start_of_week} → {end_of_week})\n"
				for emp in all_employees:
					total_hours = sum(t.total_hours for t in timesheets if t.employee == emp.name)
					msg += f"{emp.employee_name} — {total_hours:.1f} hrs\n"

			payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
			requests.post(telegram_url, json=payload)
			return "OK"

		elif text.upper() in [emp.name.upper() for emp in all_employees]:
			matched_emp = next((emp for emp in all_employees if emp.name.upper() == text.upper()), None)

			if matched_emp:
				emp_timesheets = [t for t in timesheets if t.employee == matched_emp.name]
				filled_days = {t.start_date for t in emp_timesheets}

				missing_days = []
				current = start_of_week
				while current <= end_of_week:
					if current.weekday() < 5 and current not in holiday_list and current not in filled_days:
						missing_days.append(current)
					current += timedelta(days=1)

				if emp_timesheets:
					total_hours = sum(t.total_hours for t in emp_timesheets)
					msg = (
						f"*Weekly Timesheet for {matched_emp.employee_name} -{matched_emp.name}*\n"
						f"*Total Hours Worked*: {total_hours:.1f} hrs\n"
					)
					if missing_days:
						msg += "\n*Pending Days:*\n" + "\n".join(
							[day.strftime("%Y-%m-%d") for day in missing_days]
						)
					else:
						msg += "\n*All timesheets filled this week!*"
				else:
					msg = (
						f"No timesheet records found for {matched_emp.employee_name} "
						f"({matched_emp.name}) this week."
					)
			else:
				msg = "Employee not found. Please check the Employee ID and try again."

			payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
			requests.post(telegram_url, json=payload)
			return "OK"

		else:
			if text.lower() == "/help":
				msg = (
					"*Available Commands:*\n"
					"/employee - List all active employees\n"
					"/timesheet - Show yesterday's timesheet summary\n"
					"/weeklyhours - Show weekly worked hours by employee\n"
					"/help - Show this help message\n"
				)
			else:
				msg = "Type /help to see available commands."

			payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
			requests.post(telegram_url, json=payload)
			return "OK"

	except Exception as e:
		frappe.log_error(f"Telegram webhook error: {e}", "Telegram Webhook")
		return f"Error: {e}"


def generate_reminder_message():
	today = date.today()
	report_date = today

	all_employees = frappe.get_all("Employee", fields=["name", "employee_name"], filters={"status": "Active"})

	filled_timesheets = frappe.get_all(
		"Timesheet", filters={"start_date": report_date, "docstatus": 1}, fields=["employee"]
	)
	filled_emp_ids = {t.employee for t in filled_timesheets}

	leave_applications = frappe.get_all(
		"Leave Application",
		filters={
			"from_date": ["<=", report_date],
			"to_date": [">=", report_date],
		},
		fields=["employee"],
	)
	leave_ids = {l.employee for l in leave_applications}

	if frappe.db.exists("Holiday", {"holiday_date": report_date}):
		frappe.log_error(f"Today ({report_date}) is a holiday — no reminders sent.", "Timesheet Reminder")
		return

	pending = []
	for emp in all_employees:
		if emp.name not in filled_emp_ids and emp.name not in leave_ids:
			pending.append(emp.employee_name)

	if not pending:
		frappe.log_error("All employees have filled their timesheet for today ", "Timesheet Reminder")
		return

	bot_token = frappe.conf.get("telegram_bot_token")
	chat_id = frappe.conf.get("telegram_chat_id")

	if not bot_token or not chat_id:
		frappe.log_error("Missing Telegram bot token or chat_id in site_config.json", "Timesheet Reminder")
		return

	telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

	pending_list_text = "\n".join([f"• {emp}" for emp in pending])
	msg = (
		f"*Timesheet Reminder for {report_date.strftime('%Y-%m-%d')}*\n\n"
		f"The following employees have *not filled* their timesheet yet:\n\n"
		f"{pending_list_text}\n\n"
	)

	payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
	requests.post(telegram_url, json=payload)
	return "OK"


@frappe.whitelist()
def send_reminder():
	frappe.enqueue("timesheet_management_system.api.telegram_bot.generate_reminder_message", queue="long")


def generate_day_reminders():
	msg = "*Please Fill Your Timesheet at the End of the Day*"

	bot_token = frappe.conf.get("telegram_bot_token")
	chat_id = frappe.conf.get("telegram_chat_id")

	telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

	payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
	requests.post(telegram_url, json=payload)
	return "OK"


def send_daily_reminders():
	frappe.enqueue("timesheet_management_system.api.telegram_bot.generate_day_reminders", queue="long")
