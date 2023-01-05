import logging
import sqlite3
from dataclasses import dataclass
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder
from telegram.ext import ContextTypes
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

import settings

logging.basicConfig(
	format='[%(asctime)s] %(levelname)s: %(message)s',
	level=logging.INFO
)


@dataclass
class Task:
	id: int
	text: str


async def _is_authorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
	if update.effective_user.id in settings.ALLOWED_USERS:
		return True

	# await context.bot.send_message(
	# 	text=f"Ты не авторизован\!",
	# 	chat_id=update.message.chat_id,
	# 	parse_mode=ParseMode.MARKDOWN_V2
	# )
	logging.warning(f"Not authorized user {update.effective_user.id}")
	return False


def _prepare_db():
	con = sqlite3.connect(settings.SQLITE3_DB_NAME)
	cur = con.cursor()
	cur.execute("CREATE TABLE if not exists backlog(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, text TEXT)")


def _add_task(task: Task) -> int:
	con = sqlite3.connect(settings.SQLITE3_DB_NAME)
	cur = con.cursor()
	query = f"INSERT INTO backlog(text) VALUES('{task.text}')"
	logging.info(f"{query=}")
	res = cur.execute(query)
	logging.info(f"New record with id {res.lastrowid} added")
	con.commit()
	return res.lastrowid


def _receive_tasks() -> list[Task]:
	con = sqlite3.connect(settings.SQLITE3_DB_NAME)
	cur = con.cursor()
	rows = cur.execute("SELECT id, text FROM backlog")
	return [Task(row[0], row[1]) for row in rows.fetchall()]


def _format_backlog(tasks: list[Task]) -> str:
	backlog = ["*BACKLOG:*\n"]
	for task in tasks:
		postfix = ""
		text = task.text
		if len(text.split("\n")) > 1:
			postfix = "..."
			text = text.split("\n")[0]
		if len(text) > 70:
			postfix = "..."
			text = text[:70]
		backlog.append(f"\[{task.id}] {text+postfix}\n")
	return "".join(backlog)


async def backlog_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat_id = update.message.chat_id
	user_id = update.effective_user.id
	received_message_id = update.message.message_id

	if not await _is_authorized(update, context):
		return

	formated_backlog = _format_backlog(_receive_tasks())
	logging.info(f"{formated_backlog=}")

	await context.bot.send_message(
		text=formated_backlog,
		chat_id=chat_id,
		parse_mode=ParseMode.MARKDOWN,
		disable_web_page_preview=True
	)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat_id = update.message.chat_id
	user_id = update.effective_user.id
	username = update.effective_user.name
	received_message_text = update.message.text

	if not await _is_authorized(update, context):
		return

	logging.info(f"Message from {user_id=} {username=}")
	logging.info(f"Data: {received_message_text}")

	task_id = _add_task(Task(None, received_message_text))

	await context.bot.send_message(
		text=f"✅ Task [{task_id}] added!",
		chat_id=chat_id,
		parse_mode=ParseMode.MARKDOWN
	)


if __name__ == '__main__':
	_prepare_db()
	application = ApplicationBuilder().token(settings.TOKEN).build()

	application.add_handler(CommandHandler('backlog', backlog_command_handler))
	application.add_handler(MessageHandler(filters.TEXT, message_handler))

	application.run_polling()
