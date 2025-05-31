@echo off
echo 正在启动 Celery Worker...

REM 切换到 backend 目录
cd backend

REM 检查虚拟环境
if exist "..\venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call ..\venv\Scripts\activate.bat
) else (
    echo 警告: 未找到虚拟环境
)

REM 设置环境变量
set PYTHONPATH=%CD%;%PYTHONPATH%
set FORKED_BY_MULTIPROCESSING=1

echo 当前目录: %CD%
echo 启动 Celery Worker...

REM 使用正确的模块路径启动 Celery
celery -A app.core.celery_app worker --loglevel=info --pool=solo

pause 