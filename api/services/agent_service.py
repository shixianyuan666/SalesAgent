from __future__ import annotations

from dataclasses import dataclass

from api.agent.graph import run_agent
from api.connectors.registry import ConnectorRegistry
from api.models import MessagePayloadProducts, MessagePayloadText
from api.repos.conversation_repo import ConversationRepo
from api.repos.product_repo import ProductRepo


@dataclass(frozen=True)
class AgentService:
    async def handle_inbound(
        self,
        platform: str,
        external_conversation_id: str,
        user_id: str,
        text: str,
    ) -> dict:
        convo_repo = ConversationRepo()
        conv = convo_repo.get_or_create(platform=platform, external_conversation_id=external_conversation_id)
        convo_repo.add_message(
            conv.id,
            direction="inbound",
            sender_id=user_id,
            payload=MessagePayloadText(type="text", text=text),
        )

        result = await run_agent(user_id=user_id, text=text)

        registry = ConnectorRegistry()
        connector = registry.get(platform)

        if result.product_ids:
            prod_repo = ProductRepo()
            products = []
            for pid in result.product_ids:
                p = prod_repo.get_product(pid)
                if p:
                    products.append(p)
            convo_repo.add_message(
                conv.id,
                direction="outbound",
                sender_id="agent",
                payload=MessagePayloadProducts(
                    type="products", product_ids=[p.id for p in products], text=result.reply_text
                ),
            )
            await connector.send_products(conv.external_conversation_id, products, result.reply_text)
        else:
            convo_repo.add_message(
                conv.id,
                direction="outbound",
                sender_id="agent",
                payload=MessagePayloadText(type="text", text=result.reply_text),
            )
            await connector.send_text(conv.external_conversation_id, result.reply_text)

        if result.need_human:
            convo_repo.set_status(conv.id, "needs_human")
        else:
            convo_repo.set_status(conv.id, "auto")

        return {
            "conversation_id": conv.id,
            "reply_text": result.reply_text,
            "product_ids": result.product_ids,
            "need_human": result.need_human,
        }

