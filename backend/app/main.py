import json
import logging
import os
import sys
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_v1_router
from app.core.config import get_settings
from app.db.session import engine
from app.db.base import Base
from app.models import User, SocialPost, VideoJob  # noqa: F401 — register tables

settings = get_settings()

# ── E6: Logging estructurado (JSON en producción) ──────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log, default=str)


def _setup_logging():
    level = logging.DEBUG if settings.debug else logging.INFO
    if settings.log_json or settings.app_env == "production":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    handler.setLevel(level)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


_setup_logging()
logger = logging.getLogger("omnicontent")

# ── E6: Sentry (opcional) ─────────────────────────────────
if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
        )
    except Exception:
        pass

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
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


# ── E6: Request logging middleware ─────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = int((time.time() - start) * 1000)
    logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, ms)
    return response


async def _run_due_publisher_loop():
    """F1: en modo eager (sin Celery/Redis real), un loop ligero procesa las publicaciones
    programadas cada 60s. Con Celery real lo hace el beat, y este loop no se ejecuta."""
    if not settings.celery_task_always_eager:
        return
    logger.info("Eager mode: auto-publishing loop ON (scheduled posts every 60s)")
    while True:
        try:
            from app.services import publish_service as _ps

            processed = await asyncio.to_thread(_ps.process_due_publishes)
            if processed:
                logger.info("process_due published %d job(s): %s", len(processed), processed)
        except Exception:
            logger.exception("process_due error")
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup() -> None:
    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    Base.metadata.create_all(bind=engine)
    asyncio.create_task(_run_due_publisher_loop())


app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

# Static files: only serve if media_root exists (dev only, not prod ephemeral)
_media = Path(settings.media_root)
if _media.exists():
    app.mount("/media", StaticFiles(directory=settings.media_root), name="media")


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "version": "2.0.0",
    }