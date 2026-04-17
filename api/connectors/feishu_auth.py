from __future__ import annotations

from dataclasses import dataclass
from time import time

import httpx


@dataclass
class FeishuAuth:
    base_url: str
    app_id: str
    app_secret: str

    _token: str | None = None
    _expire_at: float = 0.0

    async def get_tenant_access_token(self) -> str:
        now = time()
        if self._token and now < self._expire_at - 30:
            return self._token

        url = self.base_url.rstrip("/") + "/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()

        if int(data.get("code", 0)) != 0:
            raise RuntimeError(data.get("msg") or "feishu_auth_error")

        token = str(data.get("tenant_access_token") or "")
        expire = int(data.get("expire") or 0)
        if not token or expire <= 0:
            raise RuntimeError("feishu_auth_invalid_response")

        self._token = token
        self._expire_at = now + expire
        return token

