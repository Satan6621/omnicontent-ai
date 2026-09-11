from fastapi import APIRouter

from app.api.v1 import dashboard, posts, publish, videos

api_v1_router = APIRouter()
api_v1_router.include_router(posts.router)
api_v1_router.include_router(videos.router)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(publish.router)
