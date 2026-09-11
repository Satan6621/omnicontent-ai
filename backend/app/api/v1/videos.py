from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_api_key
from app.db.session import get_db
from app.models import JobStatus, VideoJob
from app.schemas import (
    VideoCreateRequest,
    VideoEditRequest,
    VideoJobListResponse,
    VideoJobResponse,
    VideoScriptRequest,
)
from app.services.script_service import generate_script
from app.tasks.video_tasks import generate_ai_video_task

router = APIRouter(prefix="/videos", tags=["videos"])

settings = get_settings()


def _parse_dt(value: str | None) -> datetime | None:
    """Parsea datetime ISO-8601; '' o None → None."""
    if value is None or not str(value).strip():
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"datetime inválido (usa ISO-8601): {value}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _to_response(job: VideoJob) -> VideoJobResponse:
    resp = VideoJobResponse.model_validate(job)
    if job.storage_url and job.status == JobStatus.COMPLETED:
        resp.video_url = job.storage_url
    elif job.video_path and job.status == JobStatus.COMPLETED:
        norm = job.video_path.replace("\\", "/")
        if norm.startswith(f"{settings.media_root}/"):
            rel = norm[len(f"{settings.media_root}/"):]
        else:
            rel = "/".join(norm.split("/")[-2:])
        resp.video_url = f"{settings.public_media_base_url}/{rel}"
    return resp


@router.post("", response_model=VideoJobResponse, status_code=status.HTTP_202_ACCEPTED,
             dependencies=[Depends(require_api_key)])
async def create_video_job(req: VideoCreateRequest, db: Session = Depends(get_db)):
    """Crea un job de video. Si `script` viene, se usa directamente (F5).

    - scheduled_for futuro → el job queda PENDING y lo lanza el Content Scheduler.
    - sin scheduled_for → se encola el render inmediatamente.
    """
    if req.script is not None and not req.script.strip():
        raise HTTPException(status_code=400, detail="script no puede estar vacío")

    scheduled = _parse_dt(req.scheduled_for)
    job = VideoJob(
        prompt=req.prompt,
        script=req.script or "",
        status=JobStatus.PENDING,
        status_detail="Scheduled" if scheduled else "Queued",
        auto_publish=req.auto_publish,
        publish_platforms=list(req.publish_platforms),
        publish_content=req.publish_content,
        publish_hashtags=req.publish_hashtags,
        style_preset=req.style_preset or "cinematic",
        voice=req.voice,
        visual_style=req.visual_style,
        music_style=req.music_style,
        scheduled_for=scheduled,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if not scheduled:
        task = generate_ai_video_task.apply_async(
            kwargs={
                "job_id": job.id,
                "voice": req.voice,
                "visual_style": req.visual_style,
                "music_style": req.music_style,
                "style_preset": job.style_preset,
            }
        )
        job.celery_task_id = task.id
        db.commit()
        db.refresh(job)
    return _to_response(job)


# ── F5: draft mode — genera SOLO el script, sin render ──
@router.post("/draft", response_model=VideoJobResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_api_key)])
async def create_draft(req: VideoScriptRequest, db: Session = Depends(get_db)):
    """Genera el script/editado, sin ejecutar el pipeline de render. Luego el editor
    del frontend ajusta el texto y llama POST /videos con `script` para renderizar."""
    try:
        script = await generate_script(req.prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo generar el script: {e}")

    job = VideoJob(
        prompt=req.prompt,
        script=script,
        status=JobStatus.PENDING,
        status_detail="Script ready (edit before render)",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_response(job)


# ── F5: editar script/job antes de renderizar ──
@router.post("/{job_id}/edit", response_model=VideoJobResponse,
             dependencies=[Depends(require_api_key)])
async def edit_video_job(job_id: int, req: VideoEditRequest, db: Session = Depends(get_db)):
    job = db.get(VideoJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video job not found")
    if job.status not in (JobStatus.PENDING, JobStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede editar un job en estado {job.status.value}",
        )

    if req.script is not None:
        if not req.script.strip():
            raise HTTPException(status_code=400, detail="script no puede estar vacío")
        job.script = req.script
    if req.auto_publish is not None:
        job.auto_publish = req.auto_publish
    if req.publish_platforms is not None:
        job.publish_platforms = list(req.publish_platforms)
    if req.publish_content is not None:
        job.publish_content = req.publish_content
    if req.publish_hashtags is not None:
        job.publish_hashtags = req.publish_hashtags
    if req.style_preset is not None:
        job.style_preset = req.style_preset
    if req.visual_style is not None:
        job.visual_style = req.visual_style  # type: ignore[attr-defined]
    if req.music_style is not None:
        job.music_style = req.music_style  # type: ignore[attr-defined]
    if req.voice is not None:
        job.voice = req.voice  # type: ignore[attr-defined]
    if req.scheduled_for is not None:
        job.scheduled_for = _parse_dt(req.scheduled_for)
    job.status_detail = "Edited, ready to render"
    db.commit()
    db.refresh(job)
    return _to_response(job)


@router.get("", response_model=VideoJobListResponse, dependencies=[Depends(require_api_key)])
async def list_video_jobs(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 100)
    rows = db.execute(
        select(VideoJob).order_by(desc(VideoJob.created_at)).limit(limit).offset(offset)
    ).scalars().all()
    return VideoJobListResponse(
        jobs=[_to_response(j) for j in rows], count=len(rows)
    )


@router.get("/{job_id}", response_model=VideoJobResponse, dependencies=[Depends(require_api_key)])
async def get_video_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(VideoJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video job not found")
    return _to_response(job)


# ── F5: disparar render de un job ya con script (draft → render) ──
@router.post("/{job_id}/render", response_model=VideoJobResponse,
             status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_api_key)])
async def render_video_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(VideoJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video job not found")
    if not job.script or not job.script.strip():
        raise HTTPException(status_code=400, detail="El job no tiene script; edítalo primero")
    if job.status not in (JobStatus.PENDING, JobStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede renderizar un job en estado {job.status.value}",
        )

    job.status = JobStatus.PENDING
    job.progress = 0
    job.status_detail = "Queued for render"
    job.error = None
    db.commit()

    task = generate_ai_video_task.apply_async(
        kwargs={
            "job_id": job.id,
            "voice": job.voice,
            "visual_style": job.visual_style,
            "music_style": job.music_style,
            "style_preset": job.style_preset,
        }
    )
    job.celery_task_id = task.id
    db.commit()
    db.refresh(job)
    return _to_response(job)


@router.post("/{job_id}/retry", response_model=VideoJobResponse,
             status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_api_key)])
async def retry_video_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(VideoJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video job not found")
    if job.status not in (JobStatus.FAILED,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot retry a job in status {job.status.value}",
        )
    job.status = JobStatus.PENDING
    job.progress = 0
    job.error = None
    job.status_detail = "Re-queued"
    db.commit()

    task = generate_ai_video_task.apply_async(
        kwargs={
            "job_id": job.id,
            "voice": job.voice,
            "visual_style": job.visual_style,
            "music_style": job.music_style,
            "style_preset": job.style_preset,
        }
    )
    job.celery_task_id = task.id
    db.commit()
    db.refresh(job)
    return _to_response(job)