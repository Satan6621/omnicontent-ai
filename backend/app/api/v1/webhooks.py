from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.db.session import get_db
from app.models import WebhookSubscription
from app.schemas import (
    WEBHOOK_EVENT_TYPES,
    WebhookCreateRequest,
    WebhookResponse,
    WebhookUpdateRequest,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("", response_model=list[WebhookResponse], dependencies=[Depends(require_api_key)])
async def list_webhooks(db: Session = Depends(get_db)):
    """Lista las suscripciones de webhook salientes."""
    rows = db.execute(
        select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc())
    ).scalars().all()
    return list(rows)


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_api_key)])
async def create_webhook(req: WebhookCreateRequest, db: Session = Depends(get_db)):
    """Registra una URL externa que recibirá POST al ocurrir `event_type`."""
    if req.event_type not in WEBHOOK_EVENT_TYPES:
        raise HTTPException(status_code=400, detail=f"event_type no soportado: {req.event_type}")
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url debe empezar con http:// o https://")

    row = WebhookSubscription(
        url=req.url,
        event_type=req.event_type,
        active=req.active,
        secret=req.secret or None,
        headers=req.headers or None,
        description=req.description,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{webhook_id}", response_model=WebhookResponse, dependencies=[Depends(require_api_key)])
async def update_webhook(webhook_id: int, req: WebhookUpdateRequest, db: Session = Depends(get_db)):
    row = db.get(WebhookSubscription, webhook_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    if req.url is not None:
        if not req.url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="url debe empezar con http:// o https://")
        row.url = req.url
    if req.event_type is not None:
        if req.event_type not in WEBHOOK_EVENT_TYPES:
            raise HTTPException(status_code=400, detail=f"event_type no soportado: {req.event_type}")
        row.event_type = req.event_type
    if req.active is not None:
        row.active = req.active
    if req.secret is not None:
        row.secret = req.secret or None
    if req.headers is not None:
        row.headers = req.headers or None
    if req.description is not None:
        row.description = req.description

    db.commit()
    db.refresh(row)
    return row


@router.post("/{webhook_id}/test", response_model=WebhookResponse, dependencies=[Depends(require_api_key)])
async def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Envía un payload de prueba al webhook y registra el resultado."""
    import asyncio

    row = db.get(WebhookSubscription, webhook_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    if not row.active:
        raise HTTPException(status_code=400, detail="Webhook inactivo")

    from datetime import datetime, timezone

    from app.services.webhook_service import _send_one

    payload = {
        "event": row.event_type,
        "test": True,
        "message": "Prueba de webhook OmniContent AI",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _send_one(row, payload)
    db.refresh(row)
    return row


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_api_key)])
async def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    row = db.get(WebhookSubscription, webhook_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    db.execute(delete(WebhookSubscription).where(WebhookSubscription.id == webhook_id))
    db.commit()