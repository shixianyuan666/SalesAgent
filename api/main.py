import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.core.db import init_db
from api.routes.auth import router as auth_router
from api.routes.products import router as products_router
from api.routes.settings import router as settings_router
from api.routes.memory import router as memory_router
from api.routes.conversations import router as conversations_router
from api.routes.webhooks import router as webhooks_router


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()

    uploads_dir = Path(os.environ.get("APP_UPLOADS_DIR", Path(__file__).resolve().parent / "uploads"))
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    app.include_router(auth_router)
    app.include_router(products_router)
    app.include_router(settings_router)
    app.include_router(memory_router)
    app.include_router(conversations_router)
    app.include_router(webhooks_router)

    @app.get("/api/health")
    async def health() -> dict:
        return {"success": True, "message": "ok"}

    return app


app = create_app()
