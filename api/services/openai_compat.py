from __future__ import annotations

import hashlib
import re
import json
from dataclasses import dataclass

import httpx


def _hash_embedding(text: str, dim: int = 256) -> list[float]:
    t = (text or "").strip().lower()
    if not t:
        return [0.0] * dim

    tokens = re.findall(r"[\u4e00-\u9fff]|[a-z0-9]+", t)
    if not tokens:
        tokens = list(t)

    out = [0.0] * dim
    for tok in tokens:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "big") % dim
        sign = 1.0 if (h[4] % 2 == 0) else -1.0
        out[idx] += sign
    norm = sum(x * x for x in out) ** 0.5
    if norm == 0:
        return out
    return [x / norm for x in out]


@dataclass(frozen=True)
class OpenAICompatConfig:
    base_url: str | None
    api_key: str | None
    chat_model: str | None
    embedding_model: str | None


@dataclass
class OpenAICompatClient:
    cfg: OpenAICompatConfig

    async def embed(self, text: str) -> list[float]:
        if not self.cfg.base_url or not self.cfg.api_key or not self.cfg.embedding_model:
            return _hash_embedding(text)

        url = self.cfg.base_url.rstrip("/") + "/v1/embeddings"
        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        payload = {"model": self.cfg.embedding_model, "input": text}
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
        emb = data["data"][0]["embedding"]
        return [float(x) for x in emb]

    async def chat_json(self, system: str, user: str, schema_hint: str) -> dict:
        if not self.cfg.base_url or not self.cfg.api_key or not self.cfg.chat_model:
            return {"ok": False, "reason": "llm_not_configured"}

        url = self.cfg.base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        content = f"{user}\n\n你必须只输出JSON，不要输出其他文字。JSON格式：{schema_hint}"
        payload = {
            "model": self.cfg.chat_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
        text = data["choices"][0]["message"]["content"]
        return _safe_json_parse(text)


def _safe_json_parse(text: str) -> dict:
    t = (text or "").strip()
    if not t:
        return {"ok": False, "reason": "empty"}
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    try:
        v = json.loads(t)
        return v if isinstance(v, dict) else {"ok": False, "reason": "not_object", "raw": v}
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", t)
    if not m:
        return {"ok": False, "reason": "invalid_json", "raw": text}
    try:
        v = json.loads(m.group(0))
        return v if isinstance(v, dict) else {"ok": False, "reason": "not_object", "raw": v}
    except Exception:
        return {"ok": False, "reason": "invalid_json", "raw": text}
