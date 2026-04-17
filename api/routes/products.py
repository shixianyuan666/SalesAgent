import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from api.core.auth import AuthUser, require_auth
from api.core.id import new_id
from api.models import Product, ProductCreate, ProductStatus, ProductUpdate
from api.repos.product_repo import ProductRepo
from api.repos.settings_repo import SettingsRepo
from api.services.openai_compat import OpenAICompatClient, OpenAICompatConfig


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products(
    user: AuthUser = Depends(require_auth),
    query: str | None = Query(default=None),
    status: ProductStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    repo = ProductRepo()
    items, total = repo.list_products(query=query, status=status, page=page, page_size=page_size)
    return {"items": [i.model_dump() for i in items], "total": total}


@router.post("", response_model=Product)
async def create_product(
    data: ProductCreate,
    user: AuthUser = Depends(require_auth),
) -> Product:
    repo = ProductRepo()
    return repo.create_product(data)


@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: str,
    user: AuthUser = Depends(require_auth),
) -> Product:
    repo = ProductRepo()
    product = repo.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Not found")
    return product


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    user: AuthUser = Depends(require_auth),
) -> Product:
    repo = ProductRepo()
    updated = repo.update_product(product_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Not found")
    return updated


@router.post("/{product_id}/images")
async def upload_images(
    product_id: str,
    files: list[UploadFile] = File(...),
    user: AuthUser = Depends(require_auth),
) -> dict:
    repo = ProductRepo()
    product = repo.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Not found")

    uploads_dir = Path(os.environ.get("APP_UPLOADS_DIR", Path(__file__).resolve().parent.parent / "uploads"))
    uploads_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for f in files:
        suffix = Path(f.filename or "").suffix[:16]
        fn = f"{new_id('upload')}{suffix}"
        out_path = uploads_dir / fn
        content = await f.read()
        out_path.write_bytes(content)
        saved.append(fn)

    images = repo.add_images(product_id, saved)
    return {"images": [i.model_dump() for i in images]}


@router.delete("/{product_id}/images/{image_id}")
async def delete_image(
    product_id: str,
    image_id: str,
    user: AuthUser = Depends(require_auth),
) -> dict:
    repo = ProductRepo()
    ok = repo.delete_image(product_id, image_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.post("/reindex")
async def reindex(
    user: AuthUser = Depends(require_auth),
) -> dict:
    settings = SettingsRepo().get_json("llm", {})
    if not isinstance(settings, dict):
        settings = {}

    client = OpenAICompatClient(
        OpenAICompatConfig(
            base_url=str(settings.get("base_url")) if settings.get("base_url") else None,
            api_key=str(settings.get("api_key")) if settings.get("api_key") else None,
            chat_model=str(settings.get("chat_model")) if settings.get("chat_model") else None,
            embedding_model=str(settings.get("embedding_model"))
            if settings.get("embedding_model")
            else None,
        )
    )

    repo = ProductRepo()
    products = repo.list_active_products_basic()
    updated = 0
    for p in products:
        text = " ".join([p.title, p.description or "", " ".join(p.tags or [])]).strip()
        emb = await client.embed(text)
        repo.set_product_embedding(p.id, emb)
        updated += 1

    return {"ok": True, "updated": updated}
