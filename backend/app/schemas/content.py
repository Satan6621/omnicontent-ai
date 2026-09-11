from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import JobStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── SocialPost ─────────────────────────────────────────────
class PostCreateRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=480)
    platform: str = Field(default="generic", max_length=40)
    tone: str = Field(default="professional", max_length=40)


class PostResponse(ORMModel):
    id: int
    topic: str
    platform: str
    content: str
    hashtags: str
    llm_provider: str
    created_at: datetime


class PostListResponse(BaseModel):
    posts: list[PostResponse]
    count: int


# ── VideoJob ───────────────────────────────────────────────
class VideoCreateRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)
    voice: str | None = Field(default=None, max_length=60)
    visual_style: str = Field(default="cinematic", max_length=60)
    music_style: str | None = Field(default=None, max_length=20)  # None | ambient | lofi | upbeat


class VideoJobResponse(ORMModel):
    id: int
    prompt: str
    script: str
    status: JobStatus
    progress: int
    status_detail: str
    video_path: str | None
    video_url: str | None = None
    duration_seconds: int | None
    error: str | None
    created_at: datetime


class VideoJobListResponse(BaseModel):
    jobs: list[VideoJobResponse]
    count: int


# ── Publicación (puente a AutoSocial) ──────────────────────
class PublishRequest(BaseModel):
    content: str = Field(min_length=1, max_length=6000)
    platforms: list[str] = Field(min_length=1)
    hashtags: str = Field(default="", max_length=600)
    video_url: str | None = Field(default=None, max_length=1000)
    image_data_uri: str | None = Field(default=None)


class PublishResponse(BaseModel):
    results: dict
    requested: int
    succeeded: int
    errors: list[str]


# ── Dashboard ──────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_posts: int
    total_videos: int
    videos_completed: int
    videos_processing: int
    videos_failed: int
    posts_last_7_days: int
    videos_last_7_days: int
