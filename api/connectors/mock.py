from __future__ import annotations

from dataclasses import dataclass

from api.connectors.base import PlatformConnector, SendResult
from api.models import Product


@dataclass(frozen=True)
class MockConnector(PlatformConnector):
    async def send_text(self, external_conversation_id: str, text: str) -> SendResult:
        return SendResult(ok=True)

    async def send_products(self, external_conversation_id: str, products: list[Product], text: str) -> SendResult:
        return SendResult(ok=True)

