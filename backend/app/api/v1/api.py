from fastapi import APIRouter
from app.api.v1.endpoints import drawings, auth, chatgpt_analysis, playground, websocket
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(drawings.router, prefix="/drawings", tags=["drawings"])
api_router.include_router(chatgpt_analysis.router, prefix="/chatgpt-analysis", tags=["智能分析"])
api_router.include_router(playground.router, prefix="/playground", tags=["AI Playground"])
api_router.include_router(websocket.router, prefix="/websocket", tags=["websocket"]) 