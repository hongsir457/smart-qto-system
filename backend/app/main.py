from dotenv import load_dotenv
load_dotenv()

import logging
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1.api import api_router
from app.database import Base, engine
from app.models import drawing # 确保模型被加载
from app.tasks import task_manager # 导入 task_manager 实例

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "websocket" in request.scope["type"]:
            return await call_next(request)
        try:
            return await asyncio.wait_for(call_next(request), timeout=300)
        except asyncio.TimeoutError:
            return JSONResponse(status_code=504, content={"error": "Request timed out"})
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时的逻辑
    logger.info("🚀 启动智能工程量清单系统...")
    logger.info("✅ TaskManager Redis监听器已在初始化时自动启动")
    logger.info("🌐 WebSocket endpoints are registered via ws_router.")
    
    # 启动 WebSocket V2 连接池管理器
    try:
        from app.services.websocket_service_v2 import get_websocket_service_v2
        websocket_service_v2 = get_websocket_service_v2()
        await websocket_service_v2.start()
        logger.info("✅ WebSocket 连接池管理器已启动")
    except Exception as e:
        logger.error(f"❌ WebSocket 连接池管理器启动失败: {e}")
    
    logger.info("👍 System startup process is complete.")
    yield
    # 应用关闭时的逻辑
    logger.info("🛑 正在关闭智能工程量清单系统...")
    
    # 停止 WebSocket V2 服务
    try:
        await websocket_service_v2.stop()
        logger.info("✅ WebSocket 连接池管理器已停止")
    except Exception as e:
        logger.error(f"❌ WebSocket 连接池管理器停止失败: {e}")
    
    logger.info("✅ System shut down safely.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# 1. 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 2. 添加其他中间件
app.add_middleware(TimeoutMiddleware)

# 3. 注册主要的 REST API 路由（包含WebSocket路由）
app.include_router(api_router, prefix=settings.API_V1_STR)

# 5. 配置静态文件服务
uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# 6. 数据库表创建
# 注意：在生产环境中，更推荐使用 Alembic 进行数据库迁移管理
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Welcome to Smart QTO System API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": settings.VERSION}

if __name__ == "__main__":
    import uvicorn
    # 使用 reload=True 以便在开发时自动重载
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 