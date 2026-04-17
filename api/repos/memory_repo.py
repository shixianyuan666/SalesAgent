from __future__ import annotations

from dataclasses import dataclass

from api.core.db import get_conn, json_dump, json_load
from api.core.id import new_id, now_iso
from api.models import Memory


@dataclass(frozen=True)
class MemoryRepo:
    def get(self, user_id: str) -> Memory | None:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM user_memory WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return None
            preferences = json_load(row["preferences_json"], {})
            if not isinstance(preferences, dict):
                preferences = {}
            return Memory(
                user_id=str(row["user_id"]),
                preferences=preferences,
                summary_text=str(row["summary_text"] or ""),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )

    def upsert(self, user_id: str, preferences: dict[str, object], summary_text: str) -> Memory:
        now = now_iso()
        with get_conn() as conn:
            existing = conn.execute(
                "SELECT user_id FROM user_memory WHERE user_id = ?", (user_id,)
            ).fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO user_memory (user_id, preferences_json, summary_text, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, json_dump(preferences), summary_text, now, now),
                )
            else:
                conn.execute(
                    """
                    UPDATE user_memory
                    SET preferences_json = ?, summary_text = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (json_dump(preferences), summary_text, now, user_id),
                )
            row = conn.execute("SELECT * FROM user_memory WHERE user_id = ?", (user_id,)).fetchone()
        return Memory(
            user_id=str(row["user_id"]),
            preferences=preferences,
            summary_text=str(row["summary_text"] or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def append_event(self, user_id: str, event_type: str, payload: dict[str, object]) -> None:
        now = now_iso()
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO user_memory_event (id, user_id, type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (new_id("memevt"), user_id, event_type, json_dump(payload), now),
            )

    def list_users(self, query: str | None, page: int, page_size: int) -> tuple[list[Memory], int]:
        where = []
        params: list[object] = []
        if query:
            where.append("(user_id LIKE ? OR summary_text LIKE ? OR preferences_json LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q])
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        offset = (page - 1) * page_size

        with get_conn() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(1) AS cnt FROM user_memory {where_sql}", params
            ).fetchone()
            total = int(total_row["cnt"]) if total_row else 0
            rows = conn.execute(
                f"""
                SELECT * FROM user_memory
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        items: list[Memory] = []
        for r in rows:
            preferences = json_load(r["preferences_json"], {})
            if not isinstance(preferences, dict):
                preferences = {}
            items.append(
                Memory(
                    user_id=str(r["user_id"]),
                    preferences=preferences,
                    summary_text=str(r["summary_text"] or ""),
                    created_at=str(r["created_at"]),
                    updated_at=str(r["updated_at"]),
                )
            )
        return items, total

    def clear(self, user_id: str) -> bool:
        with get_conn() as conn:
            row = conn.execute("SELECT user_id FROM user_memory WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM user_memory WHERE user_id = ?", (user_id,))
        return True

