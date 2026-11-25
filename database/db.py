import sqlite3
import os
from pathlib import Path

from database.models import (
    USERS_SCHEMA,
    PLANTS_SCHEMA,
    SCANS_SCHEMA,
    SCAN_PREDICTIONS_SCHEMA,
    USER_SETTINGS_SCHEMA,
    REMINDERS_SCHEMA,
    CHAT_SCHEMA,
)


DATA_DIR = Path(
    os.environ.get(
        "APP_DATA_DIR",
        Path(__file__).resolve().parent.parent / "instance",
    )
)
DB_PATH = DATA_DIR / "app.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.executescript(USERS_SCHEMA)
        connection.executescript(PLANTS_SCHEMA)
        connection.executescript(SCANS_SCHEMA)
        connection.executescript(SCAN_PREDICTIONS_SCHEMA)
        connection.executescript(USER_SETTINGS_SCHEMA)
        connection.executescript(REMINDERS_SCHEMA)
        connection.executescript(CHAT_SCHEMA)
