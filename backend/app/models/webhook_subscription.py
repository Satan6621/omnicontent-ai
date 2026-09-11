from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookSubscription(Base):
    """Suscripciones a webhooks salientes.

    - event_type: 'job.completed' | 'job.failed' | 'publish.published' | 'publish.failed'
    - url: endpoint HTTP de destino (p.ej. instancia local de n8n)
    - secret: firma HMAC-SHA256 opcional (X-Omni-Signature)
    - active: si está habilitada
    """
    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    secret: Mapped[str | None] = mapped_column(String(500), nullable=True)
    headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # headers extra (p.ej. Authorization)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")

    last_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # delivered | failed
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )