from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.db.session import get_db
from app.models import SocialPost
from app.schemas import PostCreateRequest, PostListResponse, PostResponse
from app.services import get_llm_service
from app.services.template_llm import TemplateLLMService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostResponse, dependencies=[Depends(require_api_key)])
async def create_post(req: PostCreateRequest, db: Session = Depends(get_db)):
    llm = get_llm_service()
    try:
        content, hashtags = await llm.generate_post(req.topic, req.platform, req.tone)
        provider = llm.provider_name
    except Exception:
        fallback = TemplateLLMService()
        content, hashtags = await fallback.generate_post(req.topic, req.platform, req.tone)
        provider = fallback.provider_name

    post = SocialPost(
        topic=req.topic,
        platform=req.platform,
        content=content,
        hashtags=hashtags,
        llm_provider=provider,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("", response_model=PostListResponse, dependencies=[Depends(require_api_key)])
async def list_posts(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 100)
    rows = db.execute(
        select(SocialPost).order_by(desc(SocialPost.created_at)).limit(limit).offset(offset)
    ).scalars().all()
    return PostListResponse(posts=[PostResponse.model_validate(r) for r in rows], count=len(rows))


@router.get("/{post_id}", response_model=PostResponse, dependencies=[Depends(require_api_key)])
async def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(SocialPost, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post
