#!/usr/bin/env python3

import asyncio
import websockets
import json
import time

async def test_websocket_with_token():
    """测试带token的WebSocket连接"""
    connection_id = f"upload_{int(time.time())}_test"
    # 模拟前端的token（实际使用中应该是有效的JWT）
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzQ5NDA5MzUzfQ.test"
    uri = f"ws://localhost:8000/ws/realtime/{connection_id}?token={token}"
    
    print(f"🔗 测试连接: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功!")
            
            # 等待连接消息
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 连接消息: {welcome_data}")
            
            # 测试ping-pong
            ping_msg = {"type": "ping", "timestamp": time.time()}
            await websocket.send(json.dumps(ping_msg))
            print(f"📤 发送ping: {ping_msg}")
            
            pong_msg = await websocket.recv()
            pong_data = json.loads(pong_msg)
            print(f"📥 收到pong: {pong_data}")
            
            # 测试任务订阅
            subscribe_msg = {"type": "subscribe_task", "task_id": "test_task_123"}
            await websocket.send(json.dumps(subscribe_msg))
            print(f"📤 发送订阅: {subscribe_msg}")
            
            subscribe_response = await websocket.recv()
            subscribe_data = json.loads(subscribe_response)
            print(f"📥 订阅响应: {subscribe_data}")
            
            print("✅ 所有测试通过!")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

async def test_websocket_without_token():
    """测试不带token的WebSocket连接"""
    connection_id = f"guest_{int(time.time())}_test"
    uri = f"ws://localhost:8000/ws/realtime/{connection_id}"
    
    print(f"🔗 测试无token连接: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ 无token连接成功!")
            
            # 等待连接消息
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 连接消息: {welcome_data}")
            
            print("✅ 访客模式测试通过!")
            
    except Exception as e:
        print(f"❌ 访客模式测试失败: {e}")

if __name__ == "__main__":
    print("🧪 开始WebSocket完整性测试...\n")
    
    print("=== 测试1: 带Token连接 ===")
    asyncio.run(test_websocket_with_token())
    
    print("\n=== 测试2: 无Token连接 ===")
    asyncio.run(test_websocket_without_token())
    
    print("\n🎉 测试完成!") 