import logging
import sqlite3
import functools
from typing import Union
from dataclasses import dataclass
from telegram import Update
from telegram.ext import filters
from telegram.ext import ContextTypes
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import ApplicationBuilder
from telegram.constants import ParseMode

import settings


logging.basicConfig(
    filename=settings.LOFGILE,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    level=logging.INFO
)


@dataclass
class Ticket:
    id: Union[int, None]
    text: str


READ_TICKET_COMMAND = "/r"
UPDATE_TICKET_COMMAND = "/u"
DELETE_TICKET_COMMAND = "/d"


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
    con.close()
    logging.info(f"DB prepared")


def insert_ticket_into_db(ticket: Ticket) -> Union[int, None]:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()

    query = trim_string(f"""
        INSERT INTO tickets(text)
        VALUES(
            ?
        )
    """)
    # logging.info(f"{query=}")

    res = cur.execute(query, (ticket.text,))
    logging.info(f"New ticket with id {res.lastrowid} added")
    con.commit()
    con.close()
    return res.lastrowid


def select_ticket_from_db(ticket_id: int) -> Union[Ticket, None]:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()

    query = trim_string(f"""
        SELECT id, text FROM tickets
        WHERE id={ticket_id}
    """)
    logging.info(f"{query=}")

    rows = cur.execute(query)
    row = rows.fetchone()
    con.close()
    if row is None:
        return None
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
    con.close()


def select_all_tickets_from_db() -> list[Ticket]:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()

    query = trim_string("""
        SELECT id, text FROM tickets
    """)
    logging.info(f"{query=}")

    rows = cur.execute(query).fetchall()
    con.close()
    if rows is None:
        return []
    return [Ticket(row[0], row[1]) for row in rows]


def render_ticket(ticket: Ticket) -> str:
    text=trim_string(rf"""
        Ticket {ticket.id}
        *[/u_{ticket.id}]
        [/d_{ticket.id}]*
    """)+f"\n\n{ticket.text}"
    return text


def render_board(tickets: list[Ticket], wide: bool = False) -> str:
    if wide:
        line_lenth = 51
    else:
        line_lenth = 40
    board = ["*TICKETS:*"]
    for ticket in tickets:

        board_line = ""
        postfix = ""
        ticket_link = rf"[/r_{ticket.id}]"
        separator = " "
        ticket_text = ticket.text.split("\n")[0]

        if (len(ticket_link) + len(separator) + \
                len(ticket_text)) > line_lenth:
            postfix = r"..."
            ticket_text = ticket_text[:line_lenth - \
                (len(ticket_link) + len(separator))]

        board_line = rf"*{ticket_link}*{separator}`{ticket_text}{postfix}`"
        board.append(board_line)
    return "\n".join(board)


@logged_handler()
@is_authorized()
async def cmd_start(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    return


@logged_handler()
@is_authorized()
async def cmd_board(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    tickets = select_all_tickets_from_db()
    text = render_board(tickets)

    await context.bot.send_message(
        text=text,
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
        text=render_board(select_all_tickets_from_db(), wide=True),
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


@logged_handler()
@is_authorized()
async def cmd_create_ticket(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    chat_id = update.message.chat_id
    received_message_text = update.message.text_markdown
    ticket_id = insert_ticket_into_db(Ticket(None, received_message_text))
    text = rf"✅ Ticket *[/r_{ticket_id}]* added!"

    await context.bot.send_message(
        text=text,
        chat_id=chat_id,
        parse_mode=ParseMode.MARKDOWN
    )


@logged_handler()
@is_authorized()
async def cmd_read_ticket(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    # "/r_238 NEO Sports" -> "238 NEO Sports"
    arg = update.message.text_markdown[\
        update.message.text_markdown.index("_")+1:].strip()
    # "238 NEO Sports" -> ['238', 'NEO Sports']
    args = arg.split(None, 1)

    # arg validation
    try:
        ticket_id = int(args[0])
    except ValueError as e:
        logging.info(f"arg({args[0]}) is incorrect value!")
        await context.bot.send_message(
            text="ERROR ticket id is incorrect value!",
            chat_id=update.message.chat_id,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    ticket = select_ticket_from_db(ticket_id)
    if ticket:
        text = render_ticket(ticket)
    else:
        text = "Specified ticket does not exist!"

    await context.bot.send_message(
        text=text,
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.MARKDOWN
    )


@logged_handler()
@is_authorized()
async def cmd_update_ticket(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    await context.bot.send_message(
        text="Functionality is being developed...",
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.MARKDOWN
    )


@logged_handler()
@is_authorized()
async def cmd_delete_ticket(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
    # "/r_238 NEO Sports" -> "238 NEO Sports"
    arg = update.message.text_markdown[\
        update.message.text_markdown.index("_")+1:].strip()
    # "238 NEO Sports" -> ['238', 'NEO Sports']
    args = arg.split(None, 1)

    # arg validation
    try:
        ticket_id = int(args[0])
    except ValueError as e:
        logging.info(f"arg({args[0]}) is incorrect value!")
        await context.bot.send_message(
            text="ERROR ticket id is incorrect value!",
            chat_id=update.message.chat_id,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    delete_ticket_from_db(ticket_id)
    text = rf"✅ Ticket {ticket_id} deleted!"

    await context.bot.send_message(
        text=text,
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.MARKDOWN
    )


if __name__ == '__main__':
    application = ApplicationBuilder().token(settings.TOKEN).build()

    prepare_db()

    application.add_handler(CommandHandler('start', cmd_start))
    application.add_handler(CommandHandler('board', cmd_board))
    application.add_handler(CommandHandler('wide_board', cmd_wide_board))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, cmd_create_ticket
    ))
    application.add_handler(MessageHandler(
        filters.Regex(rf"^{READ_TICKET_COMMAND}_"), cmd_read_ticket
    ))
    application.add_handler(MessageHandler(
        filters.Regex(rf"^{UPDATE_TICKET_COMMAND}_"), cmd_update_ticket
    ))
    application.add_handler(MessageHandler(
        filters.Regex(rf"^{DELETE_TICKET_COMMAND}_"), cmd_delete_ticket
    ))

    application.run_polling()
