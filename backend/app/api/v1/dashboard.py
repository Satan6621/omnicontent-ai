from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.db.session import get_db
from app.models import JobStatus, PublishJob, SocialPost, VideoJob
from app.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats, dependencies=[Depends(require_api_key)])
async def get_stats(db: Session = Depends(get_db)):
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    total_posts = db.execute(select(func.count(SocialPost.id))).scalar_one()
    total_videos = db.execute(select(func.count(VideoJob.id))).scalar_one()
    completed = db.execute(
        select(func.count(VideoJob.id)).where(VideoJob.status == JobStatus.COMPLETED)
    ).scalar_one()
    processing = db.execute(
        select(func.count(VideoJob.id)).where(VideoJob.status == JobStatus.PROCESSING)
    ).scalar_one()
    failed = db.execute(
        select(func.count(VideoJob.id)).where(VideoJob.status == JobStatus.FAILED)
    ).scalar_one()
    posts_week = db.execute(
        select(func.count(SocialPost.id)).where(SocialPost.created_at >= week_ago)
    ).scalar_one()
    videos_week = db.execute(
        select(func.count(VideoJob.id)).where(VideoJob.created_at >= week_ago)
    ).scalar_one()
    publishes_week = db.execute(
        select(func.count(PublishJob.id)).where(
            PublishJob.created_at >= week_ago,
            PublishJob.status.notin_(["cancelled"]),
        )
    ).scalar_one()

    return DashboardStats(
        total_posts=total_posts,
        total_videos=total_videos,
        videos_completed=completed,
        videos_processing=processing,
        videos_failed=failed,
        posts_last_7_days=posts_week,
        videos_last_7_days=videos_week,
        publishes_last_7_days=publishes_week,
    )