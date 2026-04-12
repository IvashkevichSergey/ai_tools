# Модуль для работы с SQLite базой данных задач.
# Содержит функции для подключения к базе данных и инициализации схемы таблицы tasks.

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"


def get_conn() -> sqlite3.Connection:
    """Открываем подключение к SQLite (по одному коннекту на вызов тула)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаём таблицу tasks, если её ещё нет."""
    conn = get_conn()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                title    TEXT NOT NULL,
                status   TEXT NOT NULL DEFAULT 'todo',
                priority INTEGER NOT NULL DEFAULT 1,
                due_date TEXT
            )
            """
        )
    conn.close()


# Один раз инициализируем схему
init_db()


