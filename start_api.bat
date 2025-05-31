@echo off
echo 启动FastAPI服务器...
call .\venv\Scripts\Activate.ps1
cd backend
echo 正在启动FastAPI服务器（开发模式）...
echo 服务器地址：http://localhost:8000
echo API文档：http://localhost:8000/docs
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause 