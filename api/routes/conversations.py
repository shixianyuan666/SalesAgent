from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.connectors.registry import ConnectorRegistry
from api.core.auth import AuthUser, require_auth
from api.models import ConversationStatus, MessagePayloadProducts, MessagePayloadText
from api.repos.conversation_repo import ConversationRepo
from api.repos.product_repo import ProductRepo


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    user: AuthUser = Depends(require_auth),
    platform: str | None = Query(default=None),
    status: ConversationStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    repo = ConversationRepo()
    items, total = repo.list_conversations(platform=platform, status=status, page=page, page_size=page_size)
    return {"items": [i.model_dump() for i in items], "total": total}


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: AuthUser = Depends(require_auth),
) -> dict:
    repo = ConversationRepo()
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    messages = repo.list_messages(conversation_id)
    return {"conversation": conv.model_dump(), "messages": [m.model_dump() for m in messages]}


class SendBody(BaseModel):
    type: str
    text: str | None = None
    product_ids: list[str] | None = None


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendBody,
    user: AuthUser = Depends(require_auth),
) -> dict:
    repo = ConversationRepo()
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")

    registry = ConnectorRegistry()
    connector = registry.get(conv.platform)

    if body.type == "text":
        if not body.text:
            raise HTTPException(status_code=422, detail="text required")
        payload = MessagePayloadText(type="text", text=body.text)
        repo.add_message(conversation_id, direction="outbound", sender_id=user.sub, payload=payload)
        repo.set_status(conversation_id, "human")
        await connector.send_text(conv.external_conversation_id, body.text)
        return {"ok": True}

    if body.type == "products":
        ids = body.product_ids or []
        if not ids:
            raise HTTPException(status_code=422, detail="product_ids required")
        prod_repo = ProductRepo()
        products = []
        for pid in ids[:3]:
            p = prod_repo.get_product(pid)
            if p:
                products.append(p)
        payload = MessagePayloadProducts(type="products", product_ids=[p.id for p in products], text=body.text)
        repo.add_message(conversation_id, direction="outbound", sender_id=user.sub, payload=payload)
        repo.set_status(conversation_id, "human")

        text = body.text or ""
        if not text:
            lines = ["我这边给你推荐这些："]
            for idx, p in enumerate(products, start=1):
                lines.append(f"{idx}. {p.title} {p.external_url}".strip())
            text = "\n".join(lines)

        await connector.send_products(conv.external_conversation_id, products, text)
        return {"ok": True}

    raise HTTPException(status_code=422, detail="invalid type")

