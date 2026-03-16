import os
import requests

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.bot.models import BotResponse

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def telegram_send_message(chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    r = requests.post(url, json=payload)

    return r.json()


