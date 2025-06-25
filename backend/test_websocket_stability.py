#!/usr/bin/env python3
"""
WebSocket连接稳定性测试
诊断和修复EPIPE错误
"""

import asyncio
import websockets
import json
import requests
import time
from datetime import datetime

async def test_websocket_connection():
    """测试WebSocket连接稳定性"""
    print("🧪 测试WebSocket连接稳定性...")
    
    try:
        # 1. 获取测试token
        print("1. 获取测试token...")
        auth_response = requests.post(
            'http://localhost:8000/api/v1/auth/test-login',
            json={"user_id": 2},
            timeout=10
        )
        
        if auth_response.status_code != 200:
            print(f"❌ 获取token失败: {auth_response.status_code}")
            return False
        
        token = auth_response.json().get('access_token')
        print("✅ Token获取成功")
        
        # 2. 建立WebSocket连接
        print("2. 建立WebSocket连接...")
        ws_url = f"ws://localhost:8000/api/v1/ws/tasks/2?token={token}"
        print(f"连接URL: {ws_url}")
        
        async with websockets.connect(
            ws_url,
            ping_interval=30,  # 每30秒发送ping
            ping_timeout=10,   # ping超时时间
            close_timeout=10   # 关闭超时时间
        ) as websocket:
            print("✅ WebSocket连接建立成功")
            
            # 3. 监听消息并测试稳定性
            message_count = 0
            start_time = time.time()
            
            try:
                # 发送测试消息
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }))
                print("📤 发送ping消息")
                
                # 持续监听消息
                while True:
                    try:
                        # 设置超时避免永久阻塞
                        message = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=70.0  # 比心跳间隔长一些
                        )
                        
                        message_count += 1
                        elapsed = time.time() - start_time
                        
                        try:
                            data = json.loads(message)
                            msg_type = data.get('type', 'unknown')
                            print(f"📨 收到消息 #{message_count}: {msg_type} (连接时长: {elapsed:.1f}s)")
                            
                            # 处理不同类型的消息
                            if msg_type == "connection_established":
                                print("🔗 连接确认消息")
                            elif msg_type == "heartbeat":
                                print("💗 心跳消息")
                            elif msg_type == "pong":
                                print("🏓 Pong响应")
                            elif msg_type == "task_update":
                                print(f"📋 任务更新: {data.get('task_id', 'unknown')}")
                            
                        except json.JSONDecodeError:
                            print(f"⚠️ 非JSON消息: {message[:100]}")
                        
                        # 测试5分钟后自动断开
                        if elapsed > 300:
                            print("⏰ 测试时间到，主动断开连接")
                            break
                            
                        # 每30秒发送一个测试消息
                        if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                            await websocket.send(json.dumps({
                                "type": "ping",
                                "timestamp": datetime.now().isoformat(),
                                "test_count": message_count
                            }))
                            print(f"📤 发送第 {int(elapsed)//30} 个测试ping")
                            
                    except asyncio.TimeoutError:
                        print("⏰ 接收消息超时，可能连接已断开")
                        break
                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"🔗 WebSocket连接关闭: {e}")
                        break
                    except Exception as e:
                        print(f"❌ 接收消息异常: {e}")
                        break
                        
            except Exception as e:
                print(f"❌ WebSocket通信异常: {e}")
                return False
                
        print(f"✅ WebSocket测试完成: 收到 {message_count} 条消息")
        return True
        
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket连接状态码错误: {e}")
        return False
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket连接被关闭: {e}")
        return False
    except Exception as e:
        print(f"❌ WebSocket连接异常: {e}")
        return False

async def test_websocket_reconnection():
    """测试WebSocket重连机制"""
    print("\n🔄 测试WebSocket重连机制...")
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        print(f"📡 连接尝试 {attempt + 1}/{max_retries}")
        
        try:
            success = await test_websocket_connection()
            if success:
                print("✅ 重连测试成功")
                return True
        except Exception as e:
            print(f"❌ 连接尝试 {attempt + 1} 失败: {e}")
        
        if attempt < max_retries - 1:
            print(f"⏳ 等待 {retry_delay} 秒后重试...")
            await asyncio.sleep(retry_delay)
    
    print("❌ 重连测试失败：所有尝试都失败了")
    return False

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 WebSocket连接稳定性测试")
    print("=" * 60)
    
    # 检查后端服务
    try:
        health_response = requests.get('http://localhost:8000/health', timeout=5)
        if health_response.status_code == 200:
            print("✅ 后端服务正常运行")
        else:
            print(f"⚠️ 后端服务状态异常: {health_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 后端服务不可达: {e}")
        return False
    
    # 运行WebSocket测试
    try:
        # 单次连接测试
        print("\n🧪 执行WebSocket连接测试...")
        success = asyncio.run(test_websocket_connection())
        
        if success:
            # 重连测试
            print("\n🔄 执行WebSocket重连测试...")
            reconnect_success = asyncio.run(test_websocket_reconnection())
            
            if reconnect_success:
                print("\n🎉 所有测试通过！WebSocket连接稳定性良好")
                return True
        
        print("\n💥 测试失败")
        return False
        
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        return False

if __name__ == "__main__":
    main() 