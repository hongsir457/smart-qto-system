@echo off
echo ========================================
echo 启动智能工程量计算系统 (含 AI Playground)
echo ========================================

echo.
echo 1. 检查环境...
cd /d "%~dp0"

echo.
echo 2. 启动后端服务...
cd backend
start "后端API服务" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo 3. 等待后端启动...
timeout /t 5 /nobreak > nul

echo.
echo 4. 启动前端服务...
cd ..\frontend
start "前端开发服务" cmd /k "npm run dev"

echo.
echo 5. 等待前端启动...
timeout /t 10 /nobreak > nul

echo.
echo ========================================
echo 系统启动完成！
echo ========================================
echo.
echo 访问地址:
echo - 前端应用: http://localhost:3000
echo - 后端API: http://localhost:8000
echo - API文档: http://localhost:8000/docs
echo.
echo 功能说明:
echo - 图纸管理: http://localhost:3000/drawings
echo - AI Playground: http://localhost:3000/playground
echo.
echo 注意事项:
echo 1. 请确保已配置 OpenAI API 密钥
echo 2. 请确保 Redis 服务正在运行
echo 3. 请确保数据库连接正常
echo.
echo 按任意键退出...
pause > nul 