from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from api.connectors.base import PlatformConnector, SendResult
from api.connectors.feishu_auth import FeishuAuth
from api.models import Product


def _resolve_upload_path(url: str) -> Path | None:
    if not url.startswith("/uploads/"):
        return None
    fn = url.removeprefix("/uploads/")
    uploads_dir = Path(os.environ.get("APP_UPLOADS_DIR", Path(__file__).resolve().parent.parent / "uploads"))
    return uploads_dir / fn


@dataclass(frozen=True)
class FeishuConfig:
    base_url: str
    access_token: str | None = None
    app_id: str | None = None
    app_secret: str | None = None


@dataclass(frozen=True)
class FeishuConnector(PlatformConnector):
    cfg: FeishuConfig
    _auth: FeishuAuth | None = None

    async def _token(self) -> str:
        if self.cfg.access_token:
            return self.cfg.access_token
        if not self.cfg.app_id or not self.cfg.app_secret:
            raise RuntimeError("feishu_token_not_configured")
        if not self._auth:
            self._auth = FeishuAuth(
                base_url=self.cfg.base_url,
                app_id=self.cfg.app_id,
                app_secret=self.cfg.app_secret,
            )
        return await self._auth.get_tenant_access_token()

    async def send_text(self, external_conversation_id: str, text: str) -> SendResult:
        try:
            await self._send_message(
                receive_id_type="chat_id",
                receive_id=external_conversation_id,
                msg_type="text",
                content={"text": text},
            )
            return SendResult(ok=True)
        except Exception as e:
            return SendResult(ok=False, error=str(e))

    async def send_products(self, external_conversation_id: str, products: list[Product], text: str) -> SendResult:
        try:
            for p in products[:3]:
                if p.images:
                    img_url = p.images[0].url
                    pth = _resolve_upload_path(img_url)
                    if pth and pth.exists():
                        image_key = await self._upload_image(pth)
                        if image_key:
                            await self._send_message(
                                receive_id_type="chat_id",
                                receive_id=external_conversation_id,
                                msg_type="image",
                                content={"image_key": image_key},
                            )
            await self.send_text(external_conversation_id, text)
            return SendResult(ok=True)
        except Exception as e:
            return SendResult(ok=False, error=str(e))

    async def _upload_image(self, path: Path) -> str | None:
        url = self.cfg.base_url.rstrip("/") + "/open-apis/im/v1/images"
        headers = {"Authorization": f"Bearer {await self._token()}"}
        files = {
            "image_type": (None, "message"),
            "image": (path.name, path.read_bytes(), "application/octet-stream"),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=headers, files=files)
            res.raise_for_status()
            data = res.json()
        if int(data.get("code", 0)) != 0:
            return None
        return data.get("data", {}).get("image_key")

    async def _send_message(
        self,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: dict,
    ) -> None:
        url = (
            self.cfg.base_url.rstrip("/")
            + f"/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        )
        headers = {"Authorization": f"Bearer {await self._token()}"}
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
        if int(data.get("code", 0)) != 0:
            raise RuntimeError(data.get("msg") or "feishu_api_error")
