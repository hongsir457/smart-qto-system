@echo off
cd /d %~dp0
title Redis Server

REM 检查是否以管理员权限运行
NET SESSION >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo 已以管理员权限运行
) ELSE (
    echo 请以管理员权限运行此脚本
    pause
    exit
)

REM 检查Redis是否已安装
redis-server --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Redis已正确安装
) ELSE (
    echo Redis未安装或未添加到PATH中
    echo 请访问 https://github.com/microsoftarchive/redis/releases 下载并安装Redis
    echo 安装时请确保勾选"Add the Redis installation folder to the PATH environment variable"
    pause
    exit
)

REM 检查Redis服务器是否已在运行
redis-cli ping >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Redis服务器已在运行
    pause
    exit
)

echo 正在启动Redis服务器...
start "" redis-server
timeout /t 2 >nul

REM 验证Redis服务器是否成功启动
redis-cli ping >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Redis服务器已成功启动
) ELSE (
    echo Redis服务器启动失败
)

pause 