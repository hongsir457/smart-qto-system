@echo off
setlocal enabledelayedexpansion

REM 显示当前目录
echo Current directory: %CD%

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo Found virtual environment, activating...
    call venv\Scripts\activate.bat
) else if exist "..\venv\Scripts\activate.bat" (
    echo Found virtual environment in parent directory, activating...
    call ..\venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found
)

REM 设置环境变量
set PYTHONPATH=%CD%;%PYTHONPATH%
set FORKED_BY_MULTIPROCESSING=1

REM 显示Python路径
echo PYTHONPATH: %PYTHONPATH%

REM 检查Python是否可用
python --version
if errorlevel 1 (
    echo Error: Python not found
    pause
    exit /b 1
)

REM 检查必要的目录和文件
if not exist "app" (
    echo Error: app directory not found
    pause
    exit /b 1
)

if not exist "app\core\celery_app.py" (
    echo Error: celery_app.py not found
    pause
    exit /b 1
)

echo Starting Celery Worker...
python celery_worker.py

REM 如果发生错误，显示错误信息并暂停
if errorlevel 1 (
    echo Error: Celery Worker failed to start
    pause
    exit /b 1
) 