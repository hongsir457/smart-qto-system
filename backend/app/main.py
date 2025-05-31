from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings
from app.api.v1.api import api_router
from app.database import Base, engine
import time
import asyncio

class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # 设置超时时间为5分钟
            timeout = 300
            result = await asyncio.wait_for(call_next(request), timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"error": "请求超时，请稍后重试"}
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加超时中间件
app.add_middleware(TimeoutMiddleware)

# 注册API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to Smart QTO System API"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Smart QTO System API is running",
        "version": settings.VERSION
    }

# 在FastAPI启动时自动创建所有数据库表，防止无表报错。
Base.metadata.create_all(bind=engine) 