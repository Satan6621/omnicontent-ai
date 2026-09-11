from celery import shared_task

from app.services.scheduler_service import process_due_scheduled


@shared_task(name="omnicontent.process_due_scheduled")
def process_due_scheduled_task():
    """Content Scheduler: lanza renders/posts programados vencidos. Beat cada 60s."""
    return process_due_scheduled()