from fastapi import APIRouter, Depends

from api.core.auth import AuthUser, require_auth
from api.models import AgentConfig
from api.repos.settings_repo import SettingsRepo


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/connectors")
async def get_connectors(user: AuthUser = Depends(require_auth)) -> dict:
    repo = SettingsRepo()
    cfg = repo.get_json("connectors", {})
    if isinstance(cfg, dict):
        masked = dict(cfg)
        feishu = masked.get("feishu")
        if isinstance(feishu, dict):
            feishu = dict(feishu)
            if "access_token" in feishu:
                feishu["access_token"] = None
            if "app_secret" in feishu:
                feishu["app_secret"] = None
            masked["feishu"] = feishu
        return {"connectors": masked}
    return {"connectors": {}}


@router.put("/connectors")
async def set_connectors(payload: dict, user: AuthUser = Depends(require_auth)) -> dict:
    repo = SettingsRepo()
    existing = repo.get_json("connectors", {})
    if not isinstance(existing, dict):
        existing = {}

    merged = dict(existing)
    for k, v in payload.items():
        if not isinstance(v, dict):
            merged[k] = v
            continue
        prev = merged.get(k)
        if not isinstance(prev, dict):
            prev = {}
        next_cfg = dict(prev)
        for ck, cv in v.items():
            if ck in ("access_token", "app_secret") and (cv is None or cv == ""):
                continue
            next_cfg[ck] = cv
        merged[k] = next_cfg

    repo.set_json("connectors", merged)
    return {"ok": True}


@router.get("/llm")
async def get_llm(user: AuthUser = Depends(require_auth)) -> dict:
    repo = SettingsRepo()
    v = repo.get_json("llm", {})
    if isinstance(v, dict) and "api_key" in v:
        v = {**v, "api_key": None}
    return {"llm": v}


@router.put("/llm")
async def set_llm(payload: dict, user: AuthUser = Depends(require_auth)) -> dict:
    repo = SettingsRepo()
    repo.set_json("llm", payload)
    return {"ok": True}


@router.get("/agent")
async def get_agent(user: AuthUser = Depends(require_auth)) -> dict:
    repo = SettingsRepo()
    raw = repo.get_json("agent", {})
    if not isinstance(raw, dict):
        raw = {}
    cfg = AgentConfig(**raw)
    return {"agent": cfg.model_dump()}


@router.put("/agent")
async def set_agent(payload: dict, user: AuthUser = Depends(require_auth)) -> dict:
    cfg = AgentConfig(**payload)
    repo = SettingsRepo()
    repo.set_json("agent", cfg.model_dump())
    return {"ok": True}
