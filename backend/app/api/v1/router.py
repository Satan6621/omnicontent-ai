from fastapi import APIRouter

from app.api.v1 import analytics, apikeys, dashboard, posts, publish, videos, webhooks

api_v1_router = APIRouter()
api_v1_router.include_router(posts.router)
api_v1_router.include_router(videos.router)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(publish.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(apikeys.router)
api_v1_router.include_router(webhooks.router)