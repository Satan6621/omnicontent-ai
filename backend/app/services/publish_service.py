"""Servicio centralizado de publicación (F1, F3, F7, E4).

- Consume AutoSocial /publish o /schedule
- Registra PublishJob en DB (estado por red)
- Deduplicación por dedupe_key (E4)
- Retry por red (F7)
"""
import hashlib
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.publish_job import PublishJob


def _auto_url(suffix: str) -> str:
    s = get_settings()
    base = s.autosocial_url.rstrip("/")
    path = getattr(s, f"autosocial_{suffix}_path", f"/{suffix}")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def _auto_headers() -> dict:
    s = get_settings()
    return {"X-API-Key": s.autosocial_api_key, "Content-Type": "application/json"}


def _make_dedupe_key(content: str, platforms: list[str], video_url: str | None, hour_window: int = 4) -> str | None:
    """Genera dedupe_key agrupando por content hash + platforms + ventana de horas."""
    if not content.strip():
        return None
    now = datetime.now(timezone.utc)
    window = now.replace(minute=(now.minute // hour_window) * hour_window, second=0, microsecond=0)
    raw = f"{hashlib.md5(content.strip().encode()).hexdigest()}|{'|'.join(sorted(platforms))}|{video_url or ''}|{window.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


def do_publish(
    content: str,
    platforms: list[str],
    hashtags: str = "",
    video_url: str | None = None,
    image_data_uri: str | None = None,
    scheduled_at: datetime | None = None,
    source: str = "api",
    retry_of: int | None = None,
    exclude_networks: list[str] | None = None,
) -> PublishJob:
    """Publica contenido y registra el resultado en DB. Retorna el PublishJob."""
    settings = get_settings()
    db = SessionLocal()
    try:
        # ── dedup (E4) ──
        dedupe_key = _make_dedupe_key(content, platforms, video_url)
        if dedupe_key and not retry_of:
            existing = db.query(PublishJob).filter(
                PublishJob.dedupe_key == dedupe_key,
                PublishJob.status.in_(["published", "processing", "pending"]),
            ).first()
            if existing:
                return existing  # ya publicado/reciente

        # ── crear registro ──
        job = PublishJob(
            content=content,
            platforms=platforms,
            hashtags=hashtags,
            video_url=video_url,
            image_data_uri=image_data_uri,
            status="pending" if scheduled_at else "processing",
            scheduled_at=scheduled_at,
            dedupe_key=dedupe_key,
            source=source,
            retry_of=retry_of,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if scheduled_at:
            return job  # el worker lo procesará después

        # ── publicar ahora ──
        result = _execute_publish(content, platforms, hashtags, video_url, image_data_uri, exclude_networks)
        job.per_network = result["results"]
        succeeded = result["succeeded"]
        requested = result["requested"]
        job.status = "published" if succeeded == requested else ("partial" if succeeded > 0 else "failed")
        job.error = "; ".join(result["errors"]) if result["errors"] else None
        job.published_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return job
    finally:
        db.close()


def retry_publish(job_id: int, failed_only: bool = True) -> PublishJob | None:
    """Reintenta publicación fallida (F7). Si failed_only=True, solo reintentar las redes fallidas."""
    db = SessionLocal()
    try:
        original = db.get(PublishJob, job_id)
        if not original:
            return None
        if original.status not in ("failed", "partial"):
            return original  # no se puede reintentar

        # Determinar qué redes reintentar
        failed_nets = []
        if failed_only and original.per_network:
            for net, data in original.per_network.items():
                if isinstance(data, dict) and not data.get("success"):
                    failed_nets.append(net)
        else:
            failed_nets = list(original.platforms)

        if not failed_nets:
            return original

        return do_publish(
            content=original.content,
            platforms=failed_nets,
            hashtags=original.hashtags,
            video_url=original.video_url,
            image_data_uri=original.image_data_uri,
            source="retry",
            retry_of=original.id,
            exclude_networks=None,
        )
    finally:
        db.close()


def _execute_publish(
    content: str,
    platforms: list[str],
    hashtags: str,
    video_url: str | None,
    image_data_uri: str | None,
    exclude_networks: list[str] | None = None,
) -> dict:
    """Llama a AutoSocial y retorna dict con results/errors/succeeded/requested."""
    full_content = content.strip()
    if hashtags:
        full_content = f"{full_content}\n\n{hashtags.strip()}"

    # Normalizar video_url a URL absoluta
    if video_url and not video_url.startswith("http"):
        s = get_settings()
        clean = video_url.replace(chr(92), "/")
        # Si es un path absoluto del contenedor, quedarse con la parte relativa al media root
        if "/media/" in clean:
            clean = clean.split("/media/", 1)[1]
        elif clean.startswith("/"):
            clean = clean.lstrip("/")
        video_url = f"{s.public_media_base_url.rstrip('/')}/{clean.lstrip('/')}"

    effective_platforms = [p for p in platforms if not exclude_networks or p not in exclude_networks]
    if not effective_platforms:
        return {"results": {}, "requested": 0, "succeeded": 0, "errors": []}

    payload: dict = {"content": full_content, "platforms": effective_platforms}
    if video_url:
        payload["video_url"] = video_url
    if image_data_uri:
        payload["image"] = image_data_uri

    try:
        timeout = httpx.Timeout(300.0)
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                _auto_url("publish"),
                headers=_auto_headers(),
                json=payload,
            )
    except Exception as e:
        return {
            "results": {},
            "requested": len(effective_platforms),
            "succeeded": 0,
            "errors": [f"AutoSocial unreachable: {e}"],
        }

    if resp.status_code != 200:
        return {
            "results": {},
            "requested": len(effective_platforms),
            "succeeded": 0,
            "errors": [f"AutoSocial HTTP {resp.status_code}"],
        }

    data = resp.json()
    results: dict = data.get("results", {})
    errors: list[str] = []
    succeeded = 0
    for plat, outcome in results.items():
        if isinstance(outcome, dict) and outcome.get("success"):
            succeeded += 1
        else:
            msg = outcome.get("error", "error") if isinstance(outcome, dict) else str(outcome)
            errors.append(f"{plat}: {msg}")

    return {
        "results": results,
        "requested": len(effective_platforms),
        "succeeded": succeeded,
        "errors": errors,
    }


def process_due_publishes() -> list[int]:
    """Procesa publicaciones programadas vencidas (F1). Llamado por Celery beat/worker."""
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        due = db.query(PublishJob).filter(
            PublishJob.status == "pending",
            PublishJob.scheduled_at.is_not(None),  # noqa: E711
            PublishJob.scheduled_at <= now,
        ).limit(20).all()

        processed_ids = []
        for job in due:
            job.status = "processing"
            db.commit()
            try:
                result = _execute_publish(
                    job.content, job.platforms, job.hashtags,
                    job.video_url, job.image_data_uri,
                )
                job.per_network = result["results"]
                succeeded = result["succeeded"]
                requested = result["requested"]
                job.status = "published" if succeeded == requested else ("partial" if succeeded > 0 else "failed")
                job.error = "; ".join(result["errors"]) if result["errors"] else None
                job.published_at = datetime.now(timezone.utc)
                processed_ids.append(job.id)
            except Exception as e:
                job.status = "failed"
                job.error = str(e)[:500]
                processed_ids.append(job.id)
            db.commit()
        return processed_ids
    finally:
        db.close()
