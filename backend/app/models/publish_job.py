from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PublishJob(Base):
    """Registro de una publicación (inmediata o programada) con estado por red.

    - scheduled_at = None → publicación inmediata (vía endpoint /publish)
    - datetime futuro → programada (la procesa el beat/worker)
    - per_network: {"mastodon": {"success": true, "url": ...}, ...}
    """
    __tablename__ = "publish_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    platforms: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    hashtags: Mapped[str] = mapped_column(Text, default="", server_default="")
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_data_uri: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending | processing | published | failed | partial | cancelled
    per_network: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dedupe_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(40), default="api", server_default="api")  # api | video_job | retry
    retry_of: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ApiKey(Base):
    """API keys multi-cliente. Cada cliente tiene su propio par nombre→hash con scopes."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # ["videos", "publish", ...] | ["*"]
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)