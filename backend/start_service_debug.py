#!/usr/bin/env python3
"""
诊断并启动后端服务
解决WebSocket连接问题
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"📁 当前目录: {current_dir}")
    
    # 检查关键文件
    main_file = current_dir / "app" / "main.py"
    if main_file.exists():
        print("✅ 找到 app/main.py")
    else:
        print("❌ 缺少 app/main.py")
        return False
        
    # 检查Python版本
    print(f"🐍 Python版本: {sys.version}")
    
    return True

def kill_existing_processes():
    """停止现有的Python进程"""
    print("🛑 停止现有进程...")
    try:
        # 在Windows上使用taskkill
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                      capture_output=True, check=False)
        print("✅ 进程清理完成")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ 进程清理异常: {e}")

def start_service():
    """启动后端服务"""
    print("🚀 启动后端服务...")
    
    try:
        # 启动uvicorn服务
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ]
        
        print(f"📋 执行命令: {' '.join(cmd)}")
        
        # 在新的进程中启动服务
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        print(f"✅ 服务进程已启动，PID: {process.pid}")
        
        # 等待服务启动
        print("⏳ 等待服务启动...")
        time.sleep(8)
        
        return process
        
    except Exception as e:
        print(f"❌ 启动服务失败: {e}")
        return None

def test_service():
    """测试服务是否正常运行"""
    print("🧪 测试服务连接...")
    
    try:
        # 测试健康检查端点
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ 健康检查通过")
            print(f"📊 响应内容: {response.text}")
            return True
        else:
            print(f"❌ 健康检查失败，状态码: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务，可能还在启动中")
        return False
    except Exception as e:
        print(f"❌ 测试服务异常: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("🎯 智能工程量清单系统 - 后端服务启动诊断")
    print("=" * 50)
    
    # 检查环境
    if not check_environment():
        print("❌ 环境检查失败")
        return False
    
    # 停止现有进程
    kill_existing_processes()
    
    # 启动服务
    process = start_service()
    if not process:
        print("❌ 服务启动失败")
        return False
    
    # 测试服务
    service_ok = test_service()
    if service_ok:
        print("🎉 后端服务启动成功！")
        print("📍 服务地址: http://localhost:8000")
        print("📍 API文档: http://localhost:8000/docs")
        print("📍 WebSocket测试: ws://localhost:8000/api/v1/ws/tasks/2")
        print("\n💡 服务正在后台运行，您现在可以使用前端连接了")
        return True
    else:
        print("❌ 服务测试失败")
        # 停止进程
        if process:
            process.terminate()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n🔧 建议检查:")
        print("1. 确保在 backend 目录中运行此脚本")
        print("2. 检查端口8000是否被其他程序占用")
        print("3. 检查Python环境和依赖包是否正确安装")
        sys.exit(1) 