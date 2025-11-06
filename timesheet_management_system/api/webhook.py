import frappe
import requests


def set_telegram_webhook():
	bot_token = frappe.conf.get("telegram_bot_token")
	site_url = "https://f35d34dc0ed0.ngrok-free.app"
	webhook_url = f"{site_url}/api/method/timesheet_management_system.api.telegram_bot.telegram_webhook"

	r = requests.get(f"https://api.telegram.org/bot{bot_token}/setWebhook?url={webhook_url}")
	frappe.msgprint(str(r.json()))
