from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_api_key
from app.db.session import get_db
from app.models import PublishJob
from app.schemas import AnalyticsEngagement, AnalyticsResponse, PlatformAnalytics

router = APIRouter(prefix="/analytics", tags=["analytics"])

settings = get_settings()


@router.get("", response_model=AnalyticsResponse, dependencies=[Depends(require_api_key)])
async def get_analytics(period_days: int = 7, db: Session = Depends(get_db)):
    """Analíticas de publicaciones (F6): resumen local + engagement vía AutoSocial."""
    since = datetime.now(timezone.utc) - timedelta(days=min(max(period_days, 1), 90))

    # ── resumen local de publish_jobs ──
    rows = db.execute(
        select(PublishJob).where(
            PublishJob.created_at >= since,
            PublishJob.status.notin_(["cancelled"]),
        )
    ).scalars().all()

    per_platform: dict[str, dict] = {}
    for r in rows:
        for plat in (r.platforms or []):
            agg = per_platform.setdefault(plat, {"published": 0, "failed": 0, "last": None})
            if r.status == "published":
                agg["published"] += 1
            elif r.status in ("failed", "partial"):
                agg["failed"] += 1
            if r.published_at:
                if agg["last"] is None or r.published_at > agg["last"]:
                    agg["last"] = r.published_at.isoformat()

    summary = PlatformAnalytics(
        total_published=sum(1 for r in rows if r.status == "published"),
        total_succeeded=sum(
            1 for r in rows if isinstance(r.per_network, dict)
            for o in r.per_network.values() if isinstance(o, dict) and o.get("success")
        ),
        total_failed=sum(1 for r in rows if r.status in ("failed", "partial")),
        per_platform=per_platform,
        engagement=[],
    )

    # ── engagement vía AutoSocial ──
    engagement: list[dict] = []
    if settings.autosocial_api_key and not settings.autosocial_api_key.startswith("change-me"):
        try:
            import httpx

            url = f"{settings.autosocial_url.rstrip('/')}{settings.autosocial_engagement_path}"
            timeout = httpx.Timeout(30.0)
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, headers={"X-API-Key": settings.autosocial_api_key})
            if resp.status_code == 200:
                engagement = resp.json().get("engagement", [])
        except Exception:
            pass
    summary.engagement = engagement

    # ── posts recientes ──
    top = db.execute(
        select(PublishJob).order_by(PublishJob.published_at.desc().nullslast()).limit(10)
    ).scalars().all()

    return AnalyticsResponse(
        period_days=period_days,
        publish_summary=summary,
        top_posts=top,
    )