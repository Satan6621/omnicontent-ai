"""Universal Outgoing Webhooks: dispara POST HTTP asíncronos a endpoints externos (n8n, Make…).

Los suscriptores se manejan vía la tabla WebhookSubscription. Cada evento relevante
(job COMPLETED / FAILED, publish done / failed) llama `dispatch_event()` que ejecuta
todos los suscriptores activos para ese event_type (no bloquea el worker).
"""
import asyncio
import hashlib
import hmac
import json
import logging
import threading
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import WebhookSubscription

logger = logging.getLogger("omnicontent")

# Eventos soportados
EVENT_VIDEO_COMPLETED = "video.completed"
EVENT_VIDEO_FAILED = "video.failed"
EVENT_PUBLISH_SUCCEEDED = "publish.succeeded"
EVENT_PUBLISH_FAILED = "publish.failed"


def _sign_body(body_bytes: bytes, secret: str) -> str:
    """HMAC-SHA256 del body para verificación en el receptor (X-Omni-Signature)."""
    return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()


def _load_subscriptions(db, event_type: str) -> list[WebhookSubscription]:
    return db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.event_type == event_type,
            WebhookSubscription.active.is_(True),
        )
    ).scalars().all()


def _record_outcome(sub_id: int, ok: bool, error: str | None = None) -> None:
    db = SessionLocal()
    try:
        fresh = db.get(WebhookSubscription, sub_id)
        if fresh is not None:
            fresh.last_status = "delivered" if ok else "failed"
            fresh.last_sent_at = datetime.now(timezone.utc)
            fresh.last_error = error
            db.commit()
    except Exception:
        pass
    finally:
        db.close()


async def _send_one(sub: WebhookSubscription, payload: dict) -> None:
    import httpx

    try:
        body = json.dumps(payload, default=str).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "OmniContent-AI/2.0"}
        for k, v in (sub.headers or {}).items():
            headers.setdefault(str(k), str(v))
        if sub.secret:
            headers["X-Omni-Signature"] = _sign_body(body, sub.secret)

        timeout = httpx.Timeout(15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(sub.url, content=body, headers=headers)
        ok = resp.status_code < 400
        _record_outcome(sub.id, ok, None if ok else f"HTTP {resp.status_code}: {resp.text[:300]}")
    except Exception as e:  # webhooks son best-effort
        logger.warning("webhook %s -> %s failed: %s", sub.event_type, sub.url, e)
        _record_outcome(sub.id, False, str(e)[:500])


def dispatch_event(event_type: str, payload: dict) -> list[str]:
    """Envía el payload a todos los suscriptores activos del evento. Retorna URLs destino."""
    try:
        db = SessionLocal()
        try:
            subs = _load_subscriptions(db, event_type)
        finally:
            db.close()
        if not subs:
            return []

        targets = [s.url for s in subs]
        for s in subs:
            try:
                asyncio.get_running_loop().create_task(_send_one(s, payload))
            except RuntimeError:
                # Sin event loop (contexto sync): lanzar en un hilo dedicado
                threading.Thread(target=lambda: asyncio.run(_send_one(s, payload)), daemon=True).start()
        return targets
    except Exception as e:
        logger.warning("dispatch_event %s error: %s", event_type, e)
        return []