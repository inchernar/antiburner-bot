import sqlite3
from dataclasses import dataclass

import settings


# Task
@dataclass
class OldModel:
    id: int
    text: str

# Ticket
@dataclass
class NewModel:
    id: int
    text: str


def create_new_table():
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()
    query = f"""
        CREATE
        TABLE if not exists
        tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            text TEXT
        )
    """
    cur.execute(query)
    con.commit()


def retrieve_data_from_old_table() -> list[OldModel]:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()
    query = f"""
        SELECT id, text FROM backlog
    """
    rows = cur.execute(query)

    return [OldModel(row[0], row[1]) for row in rows.fetchall()]


def load_data_into_new_table(data: list[OldModel]) -> None:
    con = sqlite3.connect(settings.SQLITE3_DB_NAME)
    cur = con.cursor()
    query = f"""
        INSERT
        INTO
        tickets (id, text)
        VALUES
        {",".join([f"({r.id}, '{r.text}')" for r in data])}
    """
    rows = cur.execute(query)
    con.commit()


def migrate():
    create_new_table()
    data = retrieve_data_from_old_table()
    load_data_into_new_table(data)


if __name__ == '__main__':
    migrate()