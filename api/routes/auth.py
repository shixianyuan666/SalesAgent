import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.core.auth import issue_token


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginBody) -> dict:
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin")

    if body.username != username or body.password != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": issue_token(sub=body.username)}

