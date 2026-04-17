from fastapi import APIRouter, Depends, HTTPException, Query

from api.core.auth import AuthUser, require_auth
from api.repos.memory_repo import MemoryRepo


router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/users")
async def list_users(
    user: AuthUser = Depends(require_auth),
    query: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    repo = MemoryRepo()
    items, total = repo.list_users(query=query, page=page, page_size=page_size)
    return {"items": [i.model_dump() for i in items], "total": total}


@router.get("/users/{user_id}")
async def get_user_memory(
    user_id: str,
    user: AuthUser = Depends(require_auth),
) -> dict:
    repo = MemoryRepo()
    mem = repo.get(user_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Not found")
    return {"memory": mem.model_dump()}


@router.delete("/users/{user_id}")
async def clear_user_memory(
    user_id: str,
    user: AuthUser = Depends(require_auth),
) -> dict:
    repo = MemoryRepo()
    ok = repo.clear(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}

