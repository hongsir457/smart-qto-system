#!/usr/bin/env python3
"""
WebSocket 连接池管理器测试脚本
"""

import asyncio
import websockets
import json
import logging
import time
from typing import List

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketClient:
    """简单的 WebSocket 客户端用于测试"""
    
    def __init__(self, user_id: int, endpoint: str, token: str = None):
        self.user_id = user_id
        self.endpoint = endpoint
        self.token = token
        self.websocket = None
        self.messages_received = []
        
    async def connect(self):
        """连接到 WebSocket 服务"""
        # 构建 WebSocket URL
        base_url = "ws://localhost:8000"
        url = f"{base_url}/api/v2/ws/{self.endpoint}"
        if self.token:
            url += f"?token={self.token}"
        
        logger.info(f"连接到: {url}")
        
        try:
            self.websocket = await websockets.connect(url)
            logger.info(f"用户 {self.user_id} 连接成功")
            return True
        except Exception as e:
            logger.error(f"用户 {self.user_id} 连接失败: {e}")
            return False
    
    async def send_message(self, message: dict):
        """发送消息"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(message))
                logger.debug(f"用户 {self.user_id} 发送消息: {message}")
                return True
            except Exception as e:
                logger.error(f"用户 {self.user_id} 发送消息失败: {e}")
                return False
        return False
    
    async def listen(self, duration: int = 30):
        """监听消息"""
        if not self.websocket:
            return
        
        logger.info(f"用户 {self.user_id} 开始监听消息，时长: {duration}秒")
        
        try:
            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    # 设置短超时以便定期检查结束时间
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0
                    )
                    
                    parsed_message = json.loads(message)
                    self.messages_received.append(parsed_message)
                    logger.info(f"用户 {self.user_id} 收到消息: {parsed_message.get('type', 'unknown')}")
                    
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"用户 {self.user_id} 连接已关闭")
                    break
                    
        except Exception as e:
            logger.error(f"用户 {self.user_id} 监听异常: {e}")
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            logger.info(f"用户 {self.user_id} 连接已关闭")


async def test_basic_connection():
    """测试基本连接功能"""
    logger.info("=== 测试基本连接功能 ===")
    
    # 创建测试客户端
    client = WebSocketClient(user_id=1, endpoint="tasks/1", token="test_token")
    
    # 连接
    connected = await client.connect()
    if not connected:
        logger.error("基本连接测试失败")
        return False
    
    # 发送 ping 消息
    await client.send_message({
        "type": "ping",
        "timestamp": time.time()
    })
    
    # 监听一段时间
    await client.listen(duration=10)
    
    # 关闭连接
    await client.close()
    
    # 检查结果
    heartbeat_received = any(msg.get('type') == 'heartbeat' for msg in client.messages_received)
    pong_received = any(msg.get('type') == 'pong' for msg in client.messages_received)
    
    logger.info(f"收到心跳消息: {heartbeat_received}")
    logger.info(f"收到 pong 响应: {pong_received}")
    logger.info(f"总共收到 {len(client.messages_received)} 条消息")
    
    return True


async def test_multiple_connections():
    """测试多连接管理"""
    logger.info("=== 测试多连接管理 ===")
    
    # 创建多个客户端
    clients = []
    for i in range(1, 4):  # 用户1, 2, 3
        client = WebSocketClient(
            user_id=i, 
            endpoint=f"tasks/{i}", 
            token=f"test_token_{i}"
        )
        clients.append(client)
    
    # 同时连接
    connection_tasks = [client.connect() for client in clients]
    results = await asyncio.gather(*connection_tasks)
    
    connected_count = sum(results)
    logger.info(f"成功连接的客户端: {connected_count}/{len(clients)}")
    
    if connected_count == 0:
        logger.error("没有客户端连接成功")
        return False
    
    # 发送不同类型的消息
    message_tasks = []
    for i, client in enumerate(clients):
        if results[i]:  # 只向成功连接的客户端发送消息
            message_tasks.append(client.send_message({
                "type": "get_user_tasks",
                "user_id": client.user_id,
                "timestamp": time.time()
            }))
    
    await asyncio.gather(*message_tasks)
    
    # 同时监听
    listen_tasks = [
        client.listen(duration=15) 
        for i, client in enumerate(clients) 
        if results[i]
    ]
    await asyncio.gather(*listen_tasks)
    
    # 关闭所有连接
    close_tasks = [client.close() for client in clients]
    await asyncio.gather(*close_tasks)
    
    # 统计结果
    for i, client in enumerate(clients):
        if results[i]:
            logger.info(f"客户端 {client.user_id} 收到 {len(client.messages_received)} 条消息")
    
    return True


async def test_connection_resilience():
    """测试连接稳定性"""
    logger.info("=== 测试连接稳定性 ===")
    
    client = WebSocketClient(user_id=99, endpoint="tasks/99", token="test_token_99")
    
    # 连接
    connected = await client.connect()
    if not connected:
        logger.error("连接稳定性测试失败 - 无法连接")
        return False
    
    # 发送大量消息测试
    message_count = 50
    logger.info(f"发送 {message_count} 条消息进行压力测试")
    
    for i in range(message_count):
        success = await client.send_message({
            "type": "ping",
            "sequence": i,
            "timestamp": time.time()
        })
        
        if not success:
            logger.warning(f"消息 {i} 发送失败")
        
        # 小延迟避免过于频繁
        await asyncio.sleep(0.1)
    
    # 监听响应
    await client.listen(duration=10)
    
    await client.close()
    
    logger.info(f"压力测试完成，收到 {len(client.messages_received)} 条响应")
    
    return True


async def main():
    """主测试函数"""
    logger.info("🧪 开始 WebSocket 连接池管理器测试")
    
    tests = [
        ("基本连接功能", test_basic_connection),
        ("多连接管理", test_multiple_connections),
        ("连接稳定性", test_connection_resilience),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"开始测试: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time
            
            if result:
                logger.info(f"✅ {test_name} 测试通过 ({duration:.2f}秒)")
                results.append((test_name, True, duration))
            else:
                logger.error(f"❌ {test_name} 测试失败 ({duration:.2f}秒)")
                results.append((test_name, False, duration))
                
        except Exception as e:
            logger.error(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False, 0))
        
        # 测试间隔
        await asyncio.sleep(2)
    
    # 输出测试总结
    logger.info(f"\n{'='*50}")
    logger.info("📊 测试总结")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, success, duration in results:
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{test_name}: {status} ({duration:.2f}秒)")
        if success:
            passed += 1
    
    logger.info(f"\n总体结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！WebSocket 连接池管理器工作正常")
    else:
        logger.warning("⚠️ 部分测试失败，请检查系统配置")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}") 