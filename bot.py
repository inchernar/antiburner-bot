from telegram import Update
from telegram.ext import Updater
from telegram.ext import CallbackContext
from telegram.ext import Filters
from telegram.ext import MessageHandler
import logging

import settings


logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                    level=logging.INFO)


def common_answer(update: Update, context: CallbackContext) -> None:
    logging.info(f"from chat {update.effective_chat.id} message: {update.message.text}")
    context.bot.send_message(chat_id=update.effective_chat.id, text="pong")

message_handler = MessageHandler(Filters.text, common_answer)

updater = Updater(token=settings.TOKEN)
dispatcher = updater.dispatcher
dispatcher.add_handler(message_handler)
updater.start_polling()
