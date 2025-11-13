# import frappe
# from telegram import Bot, Update
# from telegram.ext import Filters, MessageHandler, Updater

# from timesheet_management_system.timesheet_management_system.modules.generate_file import (
#     generate_missing_timesheet_excel,
# )


# def handle_message(update: Update,context):
#     """
#     The Updater connects your bot to Telegram and listens for new messages.
#     This function handles user input and triggers the right action.
#     """
#     text = update.message.text.lower()
#     # chat_id = update.message.chat_id

#     if "/timesheet" or "timesheet" in text:
#         update.message.reply_text("⏳ Generating missing timesheet report...")
#         if not hasattr(frappe.local, "flags"):
#             frappe.local.flags = frappe._dict(in_test=False)
#         file_path = generate_missing_timesheet_excel()
#         print(file_path)
#         if not file_path:
#             update.message.reply_text("✅ All timesheets are up to date. No missing timesheets found.")
#             return
#         with open(file_path, "rb") as file:
#             update.message.reply_document(file, caption="📄 Missing Timesheet Report")


#     elif "/employee" in text:
#         update.message.reply_text("👤 You selected Employee process.")
#     else:
#         update.message.reply_text("Please type '/timesheet' or '/employee' 🙏")

# def test_function():
#     bot_token = "8205803864:AAFyzXA-QwCXRuuzNwFB0ctIVIL0g4nyrvo"
#     updater = Updater(bot_token)
#     dp = updater.dispatcher
#     dp.add_handler(MessageHandler(Filters.text & ~Filters.command,handle_message))
#     print("🤖 Bot started. Send 'timesheet' or 'employee' to test.")
#     updater.start_polling() #It starts an infinite loop in the background — constantly checking for new messages every few seconds.
#     updater.idle() #It waits for you to press Ctrl+C to safely stop polling.

import os

import frappe
from telegram import Update
from telegram.ext import Filters, MessageHandler, Updater

from timesheet_management_system.timesheet_management_system.modules.generate_file import (
	generate_missing_timesheet_excel,
	get_employee_list,
)


def setup_frappe():
	"""
	Automatically connect to the first available Frappe site.
	Works both locally and on the server.
	"""
	if frappe.db:
		return

	current_path = os.path.abspath(os.path.dirname(__file__))
	while current_path != "/" and not os.path.exists(os.path.join(current_path, "sites")):
		current_path = os.path.dirname(current_path)

	sites_path = os.path.join(current_path, "sites")

	if not os.path.exists(sites_path):
		raise Exception("Could not find 'sites' folder. Please run this from within a Frappe bench.")

	for name in os.listdir(sites_path):
		site_config_path = os.path.join(sites_path, name, "site_config.json")
		if os.path.exists(site_config_path):
			frappe.init(site=name)
			frappe.connect()
			return

	raise Exception("No valid site found in sites directory.")


def handle_message(update: Update, context):
	text = update.message.text.lower()
	setup_frappe()
	# if text.startswith("/"):
	#     text = text.split()[1:]
	# print("Received message:", text)

	if text == "/timesheet":
		update.message.reply_text("⏳ Generating missing timesheet report...")

		file_path = generate_missing_timesheet_excel()

		if not file_path:
			update.message.reply_text("All timesheets are up to date. No missing timesheets found.")
		if file_path.startswith("/files/"):
			site_path = frappe.get_site_path("public", "files")
			file_name = file_path.replace("/files/", "")
			absolute_path = os.path.join(site_path, file_name)
		else:
			absolute_path = file_path
		if os.path.exists(absolute_path):
			with open(absolute_path, "rb") as file:
				update.message.reply_document(file, caption="Missing Timesheet Report")
		else:
			update.message.reply_text(
				"File not found on server. Something went wrong while generating the report."
			)
			print(f"File not found: {absolute_path}")

	elif "/employee" in text:
		update.message.reply_text("👤 You selected Employee process.")
		emp = get_employee_list()

		if emp:
			# Handle both dict and string returns safely
			if isinstance(emp[0], dict):
				emp = [e.get("name") for e in emp]
				update.message.reply_text(f"👤 Employee List: {', '.join(emp)}")
			else:
				update.message.reply_text("⚠️ No employees found.")
		else:
			update.message.reply_text("Please type '/timesheet' or '/employee'")

	frappe.destroy()


def test_function():
	bot_token = "8205803864:AAFyzXA-QwCXRuuzNwFB0ctIVIL0g4nyrvo"
	updater = Updater(bot_token)
	dp = updater.dispatcher
	dp.add_handler(MessageHandler(Filters.command, handle_message))
	print("🤖 Bot started. Send 'timesheet' or 'employee' to test.")
	updater.start_polling()
	updater.idle()


if __name__ == "__main__":
	test_function()
