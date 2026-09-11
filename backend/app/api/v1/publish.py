from datetime import datetime
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.db.session import get_db
from app.models import PublishJob
from app.schemas import (
    PublishJobListResponse,
    PublishRequest,
    PublishResponse,
)
from app.services import publish_service

router = APIRouter(prefix="/publish", tags=["publish"])


def _parse_scheduled(scheduled_at: str | None) -> datetime | None:
    """Parsea fecha ISO (p.ej. 2026-09-15T18:30:00Z o -05:00)."""
    if not scheduled_at:
        return None
    try:
        dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="scheduled_at inválido (usa ISO-8601)")
    from datetime import timezone

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("", response_model=PublishResponse, dependencies=[Depends(require_api_key)])
async def publish_to_socials(req: PublishRequest, db: Session = Depends(get_db)):
    """Publica contenido en redes (inmediato o programado) vía AutoSocial.

    - scheduled_at presente y futuro → se programa (F1)
    - sin scheduled_at → publicación inmediata con dedup (E4)
    """
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content no puede estar vacío")

    scheduled = _parse_scheduled(req.scheduled_at)
    job = await asyncio.to_thread(
        publish_service.do_publish,
        content=req.content.strip(),
        platforms=[p for p in req.platforms],
        hashtags=req.hashtags,
        video_url=req.video_url,
        image_data_uri=req.image_data_uri,
        scheduled_at=scheduled,
        source="api",
    )

    # dedup: ya existía → retornarlo como resultado
    resp_results: dict = job.per_network or {}
    resp_errors: list[str] = [job.error] if job.error else []
    succeeded = 0
    for plat, outcome in resp_results.items():
        if isinstance(outcome, dict) and outcome.get("success"):
            succeeded += 1
    if scheduled:
        resp_results = {}
        resp_errors = []

    return PublishResponse(
        results=resp_results,
        requested=len(req.platforms),
        succeeded=succeeded if not scheduled else 0,
        errors=resp_errors,
        job_id=job.id,
    )


@router.get("/jobs", response_model=PublishJobListResponse, dependencies=[Depends(require_api_key)])
async def list_publish_jobs(limit: int = 20, offset: int = 0, status_filter: str | None = None,
                           db: Session = Depends(get_db)):
    """Historial de publicaciones (F6: analytics, F7: estado por red)."""
    limit = min(max(limit, 1), 100)
    q = select(PublishJob)
    if status_filter:
        q = q.where(PublishJob.status == status_filter)
    rows = db.execute(q.order_by(desc(PublishJob.created_at)).limit(limit).offset(offset)).scalars().all()
    return PublishJobListResponse(jobs=rows, count=len(rows))


@router.get("/jobs/{job_id}", response_model=PublishJobListResponse,
            dependencies=[Depends(require_api_key)])
async def get_publish_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(PublishJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publish job not found")
    return PublishJobListResponse(jobs=[job], count=1)


@router.post("/jobs/{job_id}/retry", response_model=PublishResponse,
             status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_api_key)])
async def retry_publish_job(job_id: int, db: Session = Depends(get_db)):
    """Reintenta publicaciones fallidas (F7). Solo fallidas o parciales."""
    job = db.get(PublishJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publish job not found")
    if job.status not in ("failed", "partial"):
        raise HTTPException(status_code=409, detail=f"Job {job_id} no es reintentable (status={job.status})")

    new_job = await asyncio.to_thread(publish_service.retry_publish, job_id)
    if new_job is None:
        raise HTTPException(status_code=400, detail="No hay redes fallidas para reintentar")

    # El job nuevo se creó/dio commit en una sesión propia; recargarlo por id con la sesión del endpoint
    db.rollback()  # reinicia el estado transaccional
    refreshed = db.get(PublishJob, new_job.id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Publish job not found")

    results = refreshed.per_network or {}
    succeeded = sum(1 for o in results.values() if isinstance(o, dict) and o.get("success"))
    errors = [f"{k}: {v.get('error', 'error')}" for k, v in results.items()
              if isinstance(v, dict) and not v.get("success")]
    return PublishResponse(
        results=results,
        requested=len(refreshed.platforms),
        succeeded=succeeded,
        errors=errors,
        job_id=refreshed.id,
    )


@router.post("/process-due", response_model=dict, dependencies=[Depends(require_api_key)])
async def trigger_process_due():
    """Procesa publicaciones programadas vencidas manualmente (o el worker lo hace solo)."""
    processed = await asyncio.to_thread(publish_service.process_due_publishes)
    return {"processed": processed, "count": len(processed)}