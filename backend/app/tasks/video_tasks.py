from app.core.celery_app import celery_app
from app.tasks.video_engine import process_video_job

__all__ = ["process_video_job"]


@celery_app.task(name="tasks.generate_ai_video", bind=True, max_retries=2)
def generate_ai_video_task(self, job_id: int, voice: str | None = None, visual_style: str = "cinematic",
                           music_style: str | None = None, style_preset: str = "cinematic") -> dict:
    return process_video_job(job_id, voice, visual_style, music_style, style_preset)
