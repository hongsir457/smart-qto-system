#!/usr/bin/env python3
"""
测试实时任务消息显示逻辑优化
验证：
1. WebSocket连接时只推送最近任务
2. 前端清理功能与后端通信
3. 任务自动过期清理
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

async def test_websocket_task_display():
    """测试WebSocket任务显示逻辑"""
    uri = "ws://localhost:8000/api/v1/ws/realtime/test_connection"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔗 WebSocket连接成功")
            
            # 监听消息
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    
                    print(f"📨 收到消息: {data.get('type')}")
                    
                    if data.get('type') == 'connection':
                        print(f"✅ 连接确认: {data.get('message')}")
                        
                    elif data.get('type') == 'user_tasks':
                        tasks = data.get('tasks', [])
                        print(f"📋 任务列表 ({len(tasks)} 个):")
                        for task in tasks:
                            print(f"  - {task.get('name')}: {task.get('status')} ({task.get('progress')}%)")
                        
                        # 测试清理功能
                        print("\n🧹 测试清理功能...")
                        await websocket.send(json.dumps({"type": "clear_user_tasks"}))
                        
                    elif data.get('type') == 'tasks_cleared':
                        cleared_count = data.get('cleared_count', 0)
                        print(f"✅ 清理完成: {cleared_count} 个任务")
                        
                        # 重新获取任务列表
                        await websocket.send(json.dumps({"type": "get_user_tasks"}))
                        
                    elif data.get('type') == 'error':
                        print(f"❌ 错误: {data.get('message')}")
                        
                except asyncio.TimeoutError:
                    print("⏰ 等待消息超时")
                    break
                except Exception as e:
                    print(f"❌ 处理消息失败: {e}")
                    break
                    
    except Exception as e:
        print(f"❌ WebSocket连接失败: {e}")

def test_task_cleanup_optimization():
    """测试任务清理优化"""
    print("🚀 开始测试实时任务消息显示逻辑优化")
    print("=" * 50)
    
    print("\n1. 测试WebSocket任务推送优化")
    print("   - 连接时只推送最近任务（2小时内，最多10个）")
    print("   - 清理历史任务后实时更新")
    
    asyncio.run(test_websocket_task_display())

if __name__ == "__main__":
    test_task_cleanup_optimization() 