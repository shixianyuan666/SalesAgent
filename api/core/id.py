import secrets
from datetime import UTC, datetime


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(12)}"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
