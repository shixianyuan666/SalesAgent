import base64
import json
import os
from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from time import time

from fastapi import Header, HTTPException


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * ((4 - (len(s) % 4)) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _secret() -> str:
    return os.environ.get("JWT_SECRET", "dev-secret")


def issue_token(sub: str, ttl_seconds: int = 60 * 60 * 24) -> str:
    payload = {"sub": sub, "iat": int(time()), "exp": int(time()) + ttl_seconds}
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac_new(_secret().encode("utf-8"), body.encode("utf-8"), sha256).digest()
    return f"{body}.{_b64url_encode(sig)}"


def verify_token(token: str) -> dict | None:
    if "." not in token:
        return None
    body, sig = token.split(".", 1)
    try:
        expected = hmac_new(_secret().encode("utf-8"), body.encode("utf-8"), sha256).digest()
        actual = _b64url_decode(sig)
    except Exception:
        return None
    if len(expected) != len(actual) or not compare_digest(expected, actual):
        return None
    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if int(payload.get("exp", 0)) < int(time()):
        return None
    return payload


@dataclass(frozen=True)
class AuthUser:
    sub: str


async def require_auth(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return AuthUser(sub=str(payload["sub"]))
