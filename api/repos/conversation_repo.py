from __future__ import annotations

from dataclasses import dataclass

from pydantic import TypeAdapter

from api.core.db import get_conn, json_dump, json_load
from api.core.id import new_id, now_iso
from api.models import Conversation, ConversationStatus, Message, MessageDirection, MessagePayload


@dataclass(frozen=True)
class ConversationRepo:
    def get_or_create(self, platform: str, external_conversation_id: str) -> Conversation:
        now = now_iso()
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM conversation
                WHERE platform = ? AND external_conversation_id = ?
                """,
                (platform, external_conversation_id),
            ).fetchone()
            if not row:
                cid = new_id("conv")
                conn.execute(
                    """
                    INSERT INTO conversation (id, platform, external_conversation_id, status, created_at, updated_at)
                    VALUES (?, ?, ?, 'auto', ?, ?)
                    """,
                    (cid, platform, external_conversation_id, now, now),
                )
                row = conn.execute("SELECT * FROM conversation WHERE id = ?", (cid,)).fetchone()
        return self._row_to_conv(row)

    def set_status(self, conversation_id: str, status: ConversationStatus) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE conversation SET status = ?, updated_at = ? WHERE id = ?",
                (status, now_iso(), conversation_id),
            )

    def list_conversations(
        self,
        platform: str | None,
        status: ConversationStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Conversation], int]:
        where = []
        params: list[object] = []
        if platform:
            where.append("platform = ?")
            params.append(platform)
        if status:
            where.append("status = ?")
            params.append(status)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        offset = (page - 1) * page_size

        with get_conn() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(1) AS cnt FROM conversation {where_sql}", params
            ).fetchone()
            total = int(total_row["cnt"]) if total_row else 0
            rows = conn.execute(
                f"""
                SELECT *
                FROM conversation
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        return ([self._row_to_conv(r) for r in rows], total)

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM conversation WHERE id = ?", (conversation_id,)).fetchone()
        if not row:
            return None
        return self._row_to_conv(row)

    def add_message(
        self,
        conversation_id: str,
        direction: MessageDirection,
        sender_id: str | None,
        payload: MessagePayload,
    ) -> Message:
        mid = new_id("msg")
        now = now_iso()
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO message (id, conversation_id, direction, sender_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mid, conversation_id, direction, sender_id, json_dump(payload.model_dump()), now),
            )
            conn.execute(
                "UPDATE conversation SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        return Message(
            id=mid,
            conversation_id=conversation_id,
            direction=direction,
            sender_id=sender_id,
            payload=payload,
            created_at=now,
        )

    def list_messages(self, conversation_id: str) -> list[Message]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM message WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            ).fetchall()

        out: list[Message] = []
        adapter = TypeAdapter(MessagePayload)
        for r in rows:
            payload_raw = json_load(r["payload_json"], {})
            payload = adapter.validate_python(payload_raw)
            out.append(
                Message(
                    id=str(r["id"]),
                    conversation_id=str(r["conversation_id"]),
                    direction=str(r["direction"]),
                    sender_id=str(r["sender_id"]) if r["sender_id"] is not None else None,
                    payload=payload,
                    created_at=str(r["created_at"]),
                )
            )
        return out

    def _row_to_conv(self, row) -> Conversation:
        return Conversation(
            id=str(row["id"]),
            platform=str(row["platform"]),
            external_conversation_id=str(row["external_conversation_id"]),
            status=str(row["status"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
