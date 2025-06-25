@echo off
cd /d "%~dp0"
echo 启动智能工程量清单系统后端...

echo 正在启动 FastAPI 服务器...
start /b python -m uvicorn app.main:app --reload --port 8000

echo 等待服务器启动...
timeout /t 3

echo 正在启动 Celery Worker...
start /b celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo

echo 后端服务已启动完成！
echo FastAPI: http://localhost:8000
echo 文档: http://localhost:8000/docs
pause 