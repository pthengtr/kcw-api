import os
import requests

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.bot.models import BotResponse

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def to_telegram_message(resp: BotResponse):
    if resp.actions:
        keyboard = [
            [InlineKeyboardButton(a.label, callback_data=f"{a.type}:{a.value}")]
            for a in resp.actions
        ]
        return resp.text, InlineKeyboardMarkup(keyboard)

    return resp.text, None


def send_telegram_message(chat_id: int, text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup.to_dict()

    requests.post(url, json=payload)


def answer_callback_query(callback_id: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"

    requests.post(url, json={"callback_query_id": callback_id})