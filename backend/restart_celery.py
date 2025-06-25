#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重启Celery并验证PaddleOCR
"""
import os
import sys
import time
import subprocess

def main():
    print("🔄 重启Celery Worker以应用代码更新")
    print("=" * 60)
    
    # 停止可能运行的Celery进程
    print("1. 查找并停止现有Celery进程...")
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/F', '/IM', 'celery.exe'], capture_output=True)
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
        else:  # Unix-like
            subprocess.run(['pkill', '-f', 'celery'], capture_output=True)
    except:
        pass
    
    print("2. 等待进程清理...")
    time.sleep(3)
    
    print("3. 重启Celery Worker...")
    print("   请手动执行以下命令：")
    print("   celery -A app.core.celery_app worker --loglevel=info --concurrency=1")
    print("")
    print("4. 然后运行验证脚本：")
    print("   python test_final_paddleocr_verification.py")
    print("")
    print("✅ 重启指导完成")

if __name__ == "__main__":
    main() 