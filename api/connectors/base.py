from __future__ import annotations

from dataclasses import dataclass

from api.models import Product


@dataclass(frozen=True)
class SendResult:
    ok: bool
    error: str | None = None


class PlatformConnector:
    async def send_text(self, external_conversation_id: str, text: str) -> SendResult:
        raise NotImplementedError

    async def send_products(self, external_conversation_id: str, products: list[Product], text: str) -> SendResult:
        raise NotImplementedError

