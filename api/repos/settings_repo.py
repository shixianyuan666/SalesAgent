from __future__ import annotations

from dataclasses import dataclass

from api.core.db import get_conn, json_dump, json_load
from api.core.id import now_iso


@dataclass(frozen=True)
class SettingsRepo:
    def get_json(self, key: str, default: object) -> object:
        with get_conn() as conn:
            row = conn.execute("SELECT value_json FROM settings WHERE key = ?", (key,)).fetchone()
            if not row:
                return default
            return json_load(row["value_json"], default)

    def set_json(self, key: str, value: object) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                  value_json = excluded.value_json,
                  updated_at = excluded.updated_at
                """,
                (key, json_dump(value), now_iso()),
            )

