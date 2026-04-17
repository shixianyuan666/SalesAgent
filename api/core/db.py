import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _db_path() -> Path:
    data_dir = Path(
        os.environ.get("APP_DATA_DIR", Path(__file__).resolve().parent.parent / "data")
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "app.db"


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
      PRAGMA foreign_keys = ON;

      CREATE TABLE IF NOT EXISTS product (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        sku TEXT,
        description TEXT,
        tags_json TEXT NOT NULL DEFAULT '[]',
        embedding_json TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        external_url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS product_image (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(product_id) REFERENCES product(id) ON DELETE CASCADE
      );

      CREATE TABLE IF NOT EXISTS conversation (
        id TEXT PRIMARY KEY,
        platform TEXT NOT NULL,
        external_conversation_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'auto',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE UNIQUE INDEX IF NOT EXISTS idx_conversation_unique
      ON conversation(platform, external_conversation_id);

      CREATE TABLE IF NOT EXISTS message (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        direction TEXT NOT NULL,
        sender_id TEXT,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(conversation_id) REFERENCES conversation(id) ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS idx_message_conversation_id ON message(conversation_id);

      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS user_memory (
        user_id TEXT PRIMARY KEY,
        preferences_json TEXT NOT NULL DEFAULT '{}',
        summary_text TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS user_memory_event (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES user_memory(user_id) ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS idx_user_memory_event_user_id ON user_memory_event(user_id);
      """
        )


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def json_load(value: str | None, default: object) -> object:
    if not value:
        return default
    return json.loads(value)


def json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
