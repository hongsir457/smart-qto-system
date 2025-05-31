@echo off
echo 启动Celery Worker...

REM 激活虚拟环境（批处理文件应该使用 .bat 而不是 .ps1）
if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo 警告: 未找到虚拟环境
)

REM 切换到 backend 目录
cd backend

REM 设置环境变量
set PYTHONPATH=%CD%;%PYTHONPATH%
set FORKED_BY_MULTIPROCESSING=1

echo 当前目录: %CD%
echo 正在启动Celery Worker进程...

REM 使用标准 Celery 命令而不是自定义脚本
celery -A app.core.celery_app worker --loglevel=info --pool=solo

pause 