from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_api_key
from app.db.session import get_db
from app.models import JobStatus, VideoJob
from app.schemas import VideoCreateRequest, VideoJobListResponse, VideoJobResponse
from app.tasks.video_tasks import generate_ai_video_task

router = APIRouter(prefix="/videos", tags=["videos"])

settings = get_settings()


def _to_response(job: VideoJob) -> VideoJobResponse:
    resp = VideoJobResponse.model_validate(job)
    if job.video_path and job.status == JobStatus.COMPLETED:
        norm = job.video_path.replace("\\", "/")
        # video_path puede ser "media/videos/job_X/job_X.mp4" → servir desde /media/**
        if norm.startswith(f"{settings.media_root}/"):
            rel = norm[len(f"{settings.media_root}/"):]
        else:
            rel = "/".join(norm.split("/")[-2:])  # job_X/job_X.mp4
        resp.video_url = f"{settings.public_media_base_url}/{rel}"
    return resp


@router.post("", response_model=VideoJobResponse, status_code=status.HTTP_202_ACCEPTED,
             dependencies=[Depends(require_api_key)])
async def create_video_job(req: VideoCreateRequest, db: Session = Depends(get_db)):
    job = VideoJob(prompt=req.prompt, status=JobStatus.PENDING, status_detail="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    task = generate_ai_video_task.apply_async(
        kwargs={
            "job_id": job.id,
            "voice": req.voice,
            "visual_style": req.visual_style,
            "music_style": req.music_style,
        }
    )
    job.celery_task_id = task.id
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
        kwargs={"job_id": job.id, "voice": None, "visual_style": "cinematic"}
    )
    job.celery_task_id = task.id
    db.commit()
    db.refresh(job)
    return _to_response(job)
