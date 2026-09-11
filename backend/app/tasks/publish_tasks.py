from celery import shared_task

from app.services import publish_service


@shared_task(name="omnicontent.process_due_publishes")
def process_due_publishes_task():
    """Procesa publicaciones programadas vencidas. Ejecutado por beat cada 60s (F1)."""
    processed = publish_service.process_due_publishes()
    return {"processed": processed, "count": len(processed)}