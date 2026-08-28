"""Módulo Telegram — encaminha mensagens ao engine."""

import asyncio
import os

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from shared.popse_common.engine_client import send_chat

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    user_id = f"telegram:{update.effective_user.id}"
    reply = await send_chat(update.message.text, user_id, "telegram")
    await update.message.reply_text(reply)


def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.run_polling()


if __name__ == "__main__":
    main()
