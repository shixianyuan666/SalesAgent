import json

from fastapi import APIRouter, HTTPException, Request

from api.repos.settings_repo import SettingsRepo
from api.services.agent_service import AgentService


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/mock")
async def mock_webhook(payload: dict) -> dict:
    user_id = str(payload.get("user_id") or "mock_user")
    conversation_id = str(payload.get("conversation_id") or "mock_conv")
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text required")
    svc = AgentService()
    return await svc.handle_inbound(
        platform="mock",
        external_conversation_id=conversation_id,
        user_id=user_id,
        text=text,
    )


@router.post("/feishu")
async def feishu_webhook(request: Request) -> dict:
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    cfg = SettingsRepo().get_json("connectors", {})
    feishu_cfg = cfg.get("feishu") if isinstance(cfg, dict) else None
    verify_token = (
        str(feishu_cfg.get("verify_token"))
        if isinstance(feishu_cfg, dict) and feishu_cfg.get("verify_token")
        else None
    )
    if verify_token:
        token = payload.get("token") if isinstance(payload, dict) else None
        if token != verify_token:
            raise HTTPException(status_code=401, detail="invalid token")

    if "challenge" in payload:
        return {"challenge": payload.get("challenge")}

    event = payload.get("event") if isinstance(payload, dict) else None
    if not isinstance(event, dict):
        raise HTTPException(status_code=200, detail="ignored")

    message = event.get("message")
    sender = event.get("sender")
    if not isinstance(message, dict) or not isinstance(sender, dict):
        raise HTTPException(status_code=200, detail="ignored")

    if sender.get("sender_type") == "app":
        return {"ok": True}

    chat_id = message.get("chat_id")
    content = message.get("content")
    if not chat_id or not content:
        raise HTTPException(status_code=200, detail="ignored")

    sender_id = None
    sender_id_obj = sender.get("sender_id")
    if isinstance(sender_id_obj, dict):
        sender_id = sender_id_obj.get("open_id") or sender_id_obj.get("user_id")

    user_id = str(sender_id or "unknown")

    text = ""
    try:
        content_json = json.loads(content)
        text = str(content_json.get("text") or "").strip()
    except Exception:
        text = str(content).strip()

    if not text:
        raise HTTPException(status_code=200, detail="ignored")

    svc = AgentService()
    await svc.handle_inbound(
        platform="feishu",
        external_conversation_id=str(chat_id),
        user_id=user_id,
        text=text,
    )

    return {"ok": True}
