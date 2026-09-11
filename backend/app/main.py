from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_v1_router
from app.core.config import get_settings
from app.db.session import engine
from app.db.base import Base
from app.models import User, SocialPost, VideoJob  # noqa: F401 — register tables

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

app.mount("/media", StaticFiles(directory=settings.media_root), name="media")


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
    }
