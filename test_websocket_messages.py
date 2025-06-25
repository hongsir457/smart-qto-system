#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试WebSocket实时消息推送功能
"""

import asyncio
import json
import logging
import sys
import os

# 添加后端目录到Python路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

from backend.app.tasks import task_manager, TaskStatus, TaskStage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_task_message_push():
    """测试任务消息推送"""
    logger.info("🧪 开始测试任务消息推送...")
    
    # 创建测试任务
    task_id = task_manager.create_task(
        name="测试消息推送任务",
        user_id=1,  # 假设用户ID为1
        metadata={"test": True}
    )
    
    logger.info(f"✅ 创建测试任务: {task_id}")
    
    # 模拟任务处理过程
    stages = [
        (TaskStatus.STARTED, TaskStage.INITIALIZING, 10, "任务开始初始化..."),
        (TaskStatus.PROCESSING, TaskStage.FILE_PROCESSING, 30, "正在处理文件..."),
        (TaskStatus.PROCESSING, TaskStage.OCR_PROCESSING, 50, "正在进行OCR识别..."),
        (TaskStatus.PROCESSING, TaskStage.GPT_ANALYSIS, 70, "正在进行AI分析..."),
        (TaskStatus.PROCESSING, TaskStage.QUANTITY_CALCULATION, 90, "正在计算工程量..."),
        (TaskStatus.SUCCESS, TaskStage.COMPLETED, 100, "任务完成！")
    ]
    
    for status, stage, progress, message in stages:
        await task_manager.update_task_status(
            task_id=task_id,
            status=status,
            stage=stage,
            progress=progress,
            message=message
        )
        
        logger.info(f"📤 发送消息: {stage.value} - {progress}% - {message}")
        
        # 等待1秒钟，模拟真实处理过程
        await asyncio.sleep(1)
    
    logger.info("🎉 测试完成！请检查前端实时任务消息页面是否收到了这些消息。")

async def test_error_message():
    """测试错误消息推送"""
    logger.info("🧪 开始测试错误消息推送...")
    
    # 创建会失败的测试任务
    task_id = task_manager.create_task(
        name="测试错误消息任务",
        user_id=1,
        metadata={"test_error": True}
    )
    
    await task_manager.update_task_status(
        task_id=task_id,
        status=TaskStatus.STARTED,
        stage=TaskStage.INITIALIZING,
        progress=10,
        message="任务开始..."
    )
    
    await asyncio.sleep(1)
    
    await task_manager.update_task_status(
        task_id=task_id,
        status=TaskStatus.PROCESSING,
        stage=TaskStage.FILE_PROCESSING,
        progress=50,
        message="处理文件中..."
    )
    
    await asyncio.sleep(1)
    
    # 模拟任务失败
    await task_manager.update_task_status(
        task_id=task_id,
        status=TaskStatus.FAILURE,
        stage=TaskStage.FAILED,
        progress=50,
        message="任务处理失败",
        error_message="模拟的错误：文件格式不支持"
    )
    
    logger.info("💥 错误消息测试完成！")

async def main():
    """主测试函数"""
    try:
        logger.info("🚀 开始WebSocket消息推送测试...")
        
        # 等待2秒，确保服务启动完成
        await asyncio.sleep(2)
        
        # 测试正常消息推送
        await test_task_message_push()
        
        # 等待3秒
        await asyncio.sleep(3)
        
        # 测试错误消息推送
        await test_error_message()
        
        logger.info("✅ 所有测试完成！")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 