@echo off
echo ===================================
echo 智能QTO系统 - 服务重启脚本
echo ===================================

echo 1. 停止所有Python进程...
taskkill /F /IM python.exe 2>nul

echo 2. 等待3秒...
timeout /t 3 /nobreak >nul

echo 3. 激活虚拟环境...
call .\venv\Scripts\Activate.ps1

echo 4. 启动Redis服务...
start "Redis Server" cmd /k "cd /d %CD% && start_redis.bat"

echo 5. 等待Redis启动...
timeout /t 5 /nobreak >nul

echo 6. 启动Celery Worker...
start "Celery Worker" cmd /k "cd /d %CD%\backend && start_celery.bat"

echo 7. 启动FastAPI服务...
start "FastAPI Server" cmd /k "cd /d %CD%\backend && start_api.bat"

echo 8. 等待服务启动...
timeout /t 3 /nobreak >nul

echo ===================================
echo 服务重启完成！
echo ===================================
echo 访问地址：
echo - API服务: http://localhost:8000
echo - API文档: http://localhost:8000/docs
echo - 前端应用: http://localhost:3000
echo ===================================

pause 