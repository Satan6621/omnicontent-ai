"""Content Scheduler: procesa contenido programado que vence ahora.

- PublishJob.scheduled_at  → publicar vía publish_service (ya existía)
- VideoJob.scheduled_for   → lanzar render del video (nuevo en este esquema)
- SocialPost.scheduled_for → actualizar published_at al vencerse (los posts de texto
  se generan al crear; el scheduler solo marca su momento de publicación)
"""
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import JobStatus, SocialPost, VideoJob
from app.tasks.video_tasks import generate_ai_video_task


def process_due_scheduled() -> dict:
    """Rutina de verificación: contenido cuyo hook está vencido."""
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        # 1) Videos programados listos para renderizarse
        due_videos = db.execute(
            select(VideoJob).where(
                VideoJob.scheduled_for.isnot(None),
                VideoJob.scheduled_for <= now,
                VideoJob.status == JobStatus.PENDING,
            ).limit(10)
        ).scalars().all()

        launched_videos: list[int] = []
        for job in due_videos:
            job.scheduled_for = None  # ya no necesita el scheduler
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
            launched_videos.append(job.id)

        # 2) SocialPosts con scheduled_for vencido: marcar published_at si falta
        due_posts = db.execute(
            select(SocialPost).where(
                SocialPost.scheduled_for.isnot(None),
                SocialPost.scheduled_for <= now,
                SocialPost.published_at.is_(None),
            ).limit(50)
        ).scalars().all()
        now_iso = datetime.now(timezone.utc)
        marked_posts: list[int] = []
        for p in due_posts:
            p.published_at = now_iso
            p.scheduled_for = None
            marked_posts.append(p.id)
        if marked_posts:
            db.commit()

        return {
            "videos_launched": launched_videos,
            "posts_marked_published": marked_posts,
            "now": now.isoformat(),
        }
    finally:
        db.close()