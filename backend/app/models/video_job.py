from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobStatus

if TYPE_CHECKING:
    from app.models.user import User


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    script: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[JobStatus] = mapped_column(
        default=JobStatus.PENDING, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status_detail: Mapped[str] = mapped_column(Text, default="", server_default="")
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Auto-publicación al completar (F2) ──
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    publish_platforms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    publish_content: Mapped[str] = mapped_column(Text, default="", server_default="")
    publish_hashtags: Mapped[str] = mapped_column(Text, default="", server_default="")

    user: Mapped["User | None"] = relationship(back_populates="video_jobs")
