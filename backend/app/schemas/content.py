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
    music_style: str | None = Field(default=None, max_length=20)
    style_preset: str = Field(default="cinematic", max_length=40)

    # F5: script override (para editar antes de render)
    script: str | None = Field(default=None, max_length=10000)

    # F1: render programado
    scheduled_for: str | None = Field(default=None, max_length=60)

    # F2: publicar al completar
    auto_publish: bool = False
    publish_platforms: list[str] = Field(default_factory=list)
    publish_content: str = Field(default="", max_length=6000)
    publish_hashtags: str = Field(default="", max_length=600)


class VideoScriptRequest(BaseModel):
    """Solo genera el script (F5: draft mode)."""
    prompt: str = Field(min_length=5, max_length=4000)


class VideoEditRequest(BaseModel):
    """Edita el script o parámetros antes de renderizar (F5)."""
    script: str | None = None
    auto_publish: bool | None = None
    publish_platforms: list[str] | None = None
    publish_content: str | None = None
    publish_hashtags: str | None = None
    visual_style: str | None = None
    music_style: str | None = None
    voice: str | None = None
    style_preset: str | None = None
    scheduled_for: str | None = Field(default=None, max_length=60)  # datetime ISO | "" | null


class VideoJobResponse(ORMModel):
    id: int
    prompt: str
    script: str
    status: JobStatus
    progress: int
    status_detail: str
    video_path: str | None
    video_url: str | None = None
    storage_url: str | None = None
    duration_seconds: int | None
    error: str | None
    auto_publish: bool
    publish_platforms: list
    style_preset: str = "cinematic"
    scheduled_for: datetime | None = None
    published_at: datetime | None = None
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
    # F1: publicación programada
    scheduled_at: str | None = Field(default=None, max_length=60)


class PublishJobResponse(ORMModel):
    id: int
    content: str
    platforms: list
    hashtags: str
    video_url: str | None
    status: str
    per_network: dict | None
    error: str | None
    scheduled_at: datetime | None
    published_at: datetime | None
    source: str
    created_at: datetime


class PublishJobListResponse(BaseModel):
    jobs: list[PublishJobResponse]
    count: int


class PublishResponse(BaseModel):
    results: dict
    requested: int
    succeeded: int
    errors: list[str]
    job_id: int | None = None


# ── Analytics ──────────────────────────────────────────────
class AnalyticsEngagement(BaseModel):
    likes: int
    reposts: int
    replies: int
    url: str | None = None


class PlatformAnalytics(BaseModel):
    total_published: int
    total_succeeded: int
    total_failed: int
    per_platform: dict[str, dict]
    engagement: list[dict]


class AnalyticsResponse(BaseModel):
    period_days: int
    publish_summary: PlatformAnalytics
    top_posts: list[PublishJobResponse]


# ── Dashboard ──────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_posts: int
    total_videos: int
    videos_completed: int
    videos_processing: int
    videos_failed: int
    posts_last_7_days: int
    videos_last_7_days: int
    publishes_last_7_days: int


# ── API Keys ───────────────────────────────────────────────
class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=lambda: ["*"])


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    scopes: list
    active: bool
    created_at: datetime
    last_used_at: datetime | None
    key_preview: str = Field(default="", description="Últimos 8 chars del key")


class ApiKeyCreateResponse(BaseModel):
    id: int
    name: str
    scopes: list
    key: str = Field(description="El key completo, solo disponible al crear")


# ── Outgoing Webhooks (integración n8n/Make) ───────────────
WEBHOOK_EVENT_TYPES = [
    "video.completed",
    "video.failed",
    "publish.succeeded",
    "publish.failed",
]


class WebhookCreateRequest(BaseModel):
    url: str = Field(min_length=5, max_length=2000)
    event_type: str = Field(min_length=3, max_length=60)
    active: bool = True
    secret: str | None = Field(default=None, max_length=500)
    headers: dict | None = None
    description: str = Field(default="", max_length=2000)


class WebhookUpdateRequest(BaseModel):
    url: str | None = Field(default=None, max_length=2000)
    event_type: str | None = Field(default=None, max_length=60)
    active: bool | None = None
    secret: str | None = Field(default=None, max_length=500)
    headers: dict | None = None
    description: str | None = Field(default=None, max_length=2000)


class WebhookResponse(ORMModel):
    id: int
    url: str
    event_type: str
    active: bool
    headers: dict | None
    description: str
    last_status: str | None
    last_sent_at: datetime | None
    last_error: str | None
    created_at: datetime