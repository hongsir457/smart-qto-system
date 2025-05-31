@echo off
echo 智能工程量计算系统 - Celery Worker 启动脚本
echo ================================================

echo 1. 设置正确的 API Key...
REM 请将下面的 YOUR_COMPLETE_API_KEY 替换为您完整的 API key (以V6M6结尾)
set OPENAI_API_KEY=sk-proj-YOUR_COMPLETE_API_KEY_ENDING_WITH_V6M6

echo    当前 API Key 末尾4位: %OPENAI_API_KEY:~-4%
echo.

echo 2. 激活虚拟环境...
if exist "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
    echo    虚拟环境已激活
) else (
    echo    警告: 未找到虚拟环境
)
echo.

echo 3. 切换到 backend 目录...
cd backend
echo    当前目录: %CD%
echo.

echo 4. 设置环境变量...
set PYTHONPATH=%CD%;%PYTHONPATH%
set FORKED_BY_MULTIPROCESSING=1
echo    环境变量已设置
echo.

echo 5. 验证 API Key...
python -c "import os; key=os.getenv('OPENAI_API_KEY'); print(f'API Key 配置检查: 末尾4位 = {key[-4:] if key else \"未设置\"}')"
echo.

echo 6. 启动 Celery Worker...
echo    使用模块路径: app.core.celery_app
echo    启动参数: --loglevel=info --pool=solo
echo.
celery -A app.core.celery_app worker --loglevel=info --pool=solo

echo.
echo Celery Worker 已停止
pause 