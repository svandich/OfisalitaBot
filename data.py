import sqlite3
import time

import config.db
from config.logger import logger


def init() -> None:
    """
    Connects to SQLite database and creates tables if they don't exist
    """
    conn = sqlite3.connect(config.db.db_file_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS ConfigFlags ("
        "chat_id INTEGER NOT NULL, "
        "key VARCHAR(255) NOT NULL, "
        "value TEXT NOT NULL, "
        "updated_at INTEGER NOT NULL, "
        "PRIMARY KEY(chat_id, key)"
        ");"
    )
    logger.info("SQLite initialized")


def connect() -> sqlite3.Connection:
    """
    Connects to SQLite database and returns the connection
    """
    return sqlite3.connect(config.db.db_file_path)


class ConfigFlags:
    """
    Simple persistent key/value store for bot configuration flags.

    Values are stored as TEXT; helpers are provided for booleans.
    """

    @staticmethod
    def get(chat_id: int, key: str, default: str | None = None) -> str | None:
        with connect() as conn:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT value FROM ConfigFlags WHERE chat_id = ? AND key = ?",
                [chat_id, key],
            ).fetchone()
            if row is None:
                return default
            return row[0]

    @staticmethod
    def set(chat_id: int, key: str, value: str) -> None:
        updated_at = int(time.time())
        with connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO ConfigFlags (chat_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                [chat_id, key, value, updated_at],
            )

    @staticmethod
    def get_bool(chat_id: int, key: str, default: bool = False) -> bool:
        raw = ConfigFlags.get(chat_id, key, default=None)
        if raw is None:
            return default
        normalized = str(raw).strip().lower()
        return normalized in ("1", "true", "t", "yes", "y", "on")

    @staticmethod
    def set_bool(chat_id: int, key: str, enabled: bool) -> None:
        ConfigFlags.set(chat_id, key, "true" if enabled else "false")

    @staticmethod
    def list_all(chat_id: int) -> list[tuple[str, str]]:
        """
        Lists all persisted configuration flags from the database.
        """
        with connect() as conn:
            cur = conn.cursor()
            rows = cur.execute(
                "SELECT key, value FROM ConfigFlags WHERE chat_id = ? ORDER BY key ASC",
                [chat_id],
            ).fetchall()
            return rows
    
    @staticmethod
    def get_all_chat_ids() -> list[int]:
        with connect() as conn:
            return [row[0] for row in conn.execute("SELECT DISTINCT chat_id FROM ConfigFlags").fetchall()]
