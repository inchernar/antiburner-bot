import logging
import sqlite3
import functools
from typing import Union
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
class Ticket:
    id: Union[int, None]
    text: str


def logged_handler():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            logging.info(5*"="+" New request " + 5*"=")

            update = args[0]
            context = args[1]

            logging.info(f"user id: {update.effective_user.id}")
            logging.info(f"user name: {update.effective_user.name}")
            logging.info(f"message: {update.message.text}")
            logging.info(f"'{func.__name__}' handler starts")

            await func(*args, **kwargs)

            logging.info(f"'{func.__name__}' handler finished")
        return wrapped
    return wrapper


def is_authorized():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            update = args[0]
            context = args[1]

            if update.effective_user.id == settings.ALLOWED_USER_ID:
                return await func(*args, **kwargs)

            logging.warning(f"Not authorized user {update.effective_user.id}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=r"¯\_(ツ)_/¯"
            )
            return
        return wrapped
    return wrapper


def trim_string(raw_string: str) -> str:
    return " ".join(raw_string.split())


def prepare_db() -> None:
    logging.info(f"DB preparing")

    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()

    query = trim_string("""
        CREATE
        TABLE if not exists
        tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            text TEXT
        )
    """)
    logging.info(f"{query=}")

    cur.execute(query)
    con.commit()
    logging.info(f"DB prepared")


def insert_ticket_into_db(ticket: Ticket) -> Union[int, None]:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()

    query = trim_string(f"""
        INSERT INTO tickets(text)
        VALUES(
            '{ticket.text}'
        )
    """)
    logging.info(f"{query=}")

    res = cur.execute(query)
    logging.info(f"New ticket with id {res.lastrowid} added")
    con.commit()
    return res.lastrowid


def select_ticket_from_db(ticket_id: int) -> Ticket:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()

    query = trim_string(f"""
        SELECT id, text FROM tickets
        WHERE id={ticket_id}
    """)
    logging.info(f"{query=}")

    rows = cur.execute(query)
    row = rows.fetchone()
    return Ticket(row[0], row[1])


def delete_ticket_from_db(ticket_id: int) -> None:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()

    query = trim_string(f"""
        DELETE
        FROM
        tickets
        WHERE id={ticket_id}
    """)
    logging.info(f"{query=}")

    cur.execute(query)
    logging.info(f"Ticket with id {ticket_id} removed")
    con.commit()


def select_all_tickets_from_db() -> list[Ticket]:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()

    query = trim_string("""
        SELECT id, text FROM tickets
    """)
    logging.info(f"{query=}")

    rows = cur.execute(query)
    return [Ticket(row[0], row[1]) for row in rows.fetchall()]


def make_board(tickets: list[Ticket], wide: bool = False) -> str:
    if wide:
        line_lenth = 51
    else:
        line_lenth = 40
    board = ["*TICKETS:*"]
    for ticket in tickets:

        board_line = ""
        postfix = ""
        ticket_link = rf"[/r{ticket.id}]"
        separator = " "
        ticket_text = ticket.text.split("\n")[0]

        if (len(ticket_link) + len(separator) + len(ticket_text)) > line_lenth:
            ticket_text = ticket_text[:line_lenth - \
                (len(ticket_link) + len(separator))]
            postfix = r"..."

        board_line = rf"\{ticket_link}{separator}`{ticket_text}{postfix}`"
        board.append(board_line)
    return "\n".join(board)


@logged_handler()
@is_authorized()
async def cmd_board(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    await context.bot.send_message(
        text=make_board(select_all_tickets_from_db()),
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


@logged_handler()
@is_authorized()
async def cmd_wide_board(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    await context.bot.send_message(
        text=make_board(select_all_tickets_from_db(), wide=True),
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


# @logged_handler()
# @is_authorized()
# async def cmd_ticket_read(
#         update: Update,
#         context: ContextTypes.DEFAULT_TYPE
#     ):
#     if not context.args:
#         logging.warning(f"'context.args' list is None object (empty)")
#         # @TODO send_message
#         return

#     ticket_id = int(context.args[0])
#     ticket = select_ticket_from_db(ticket_id)
#     # @TODO func format_ticket

#     await context.bot.send_message(
#         text=f"*{ticket.id}*\n{ticket.text}",
#         chat_id=update.message.chat_id,
#         parse_mode=ParseMode.MARKDOWN
#     )


@logged_handler()
@is_authorized()
async def cmd_ticket_delete(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    if not context.args:
        logging.warning(f"'context.args' list is None object (empty)")
        # @TODO send_message
        return

    removed_ticket_ids = []
    for ticket_id in context.args:
        try:
            # @TODO check ticket existence before deletion
            ticket_id = int(ticket_id)
            delete_ticket_from_db(ticket_id)
            removed_ticket_ids.append(ticket_id)
        except:
            continue

    format_ticket_ids = ", ".join([str(id) for id in removed_ticket_ids])
    await context.bot.send_message(
        text=rf"✅ Ticket(s) {format_ticket_ids} deleted!",
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.MARKDOWN
    )


@logged_handler()
@is_authorized()
async def common_message_handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    chat_id = update.message.chat_id
    received_message_text = update.message.text

    # @TODO replace by function like check_ticket_request
    # @TODO use regexp for match commands
    if received_message_text.startswith("/r"):
        try:
            # @TODO how to take command string
            ticket_id = int(received_message_text[2:].strip())
            ticket = select_ticket_from_db(ticket_id)
            # @TODO write func format_ticket
            await context.bot.send_message(
                text=trim_string(f"""
                    *Ticket [{ticket_id}]
                    [/u{ticket_id}]
                    [/d{ticket_id}]*
                """)+f"\n\n{ticket.text}",
                chat_id=chat_id,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        except:
            return
    elif received_message_text.startswith("/u"):
        return
    elif received_message_text.startswith("/d"):
        return

    ticket_id = insert_ticket_into_db(Ticket(None, received_message_text))

    await context.bot.send_message(
        text=rf"✅ Ticket \[/r{ticket_id}] added!",
        chat_id=chat_id,
        parse_mode=ParseMode.MARKDOWN
    )


if __name__ == '__main__':
    application = ApplicationBuilder().token(settings.TOKEN).build()

    prepare_db()
    application.add_handler(CommandHandler('board', cmd_board))
    application.add_handler(CommandHandler('wide_board', cmd_wide_board))
    # application.add_handler(CommandHandler('ticket_read', cmd_ticket_read))
    application.add_handler(CommandHandler('ticket_delete', cmd_ticket_delete))
    application.add_handler(
        MessageHandler(filters.TEXT, common_message_handler)
    )

    application.run_polling()
