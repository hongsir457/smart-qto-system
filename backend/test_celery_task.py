#!/usr/bin/env python3
"""
Celery任务测试脚本
"""
import time
from ....tasks.drawing_tasks import process_drawing_celery_task, process_component_detection_task

def test_celery_tasks():
    print("开始测试Celery异步任务...")
    
    try:
        # 测试完整处理任务
        print("1. 测试完整处理任务...")
        task1 = process_drawing.delay(1, 1, "full_processing")
        print(f"   任务ID: {task1.id}")
        print(f"   任务状态: {task1.status}")
        
        # 测试OCR任务
        print("2. 测试OCR任务...")
        task2 = process_drawing.delay(1, 1, "ocr_only")
        print(f"   任务ID: {task2.id}")
        print(f"   任务状态: {task2.status}")
        
        # 测试构件识别任务
        print("3. 测试构件识别任务...")
        task3 = process_component_detection_task.delay(1, 1)
        print(f"   任务ID: {task3.id}")
        print(f"   任务状态: {task3.status}")
        
        print("所有任务已提交到Celery队列！")
        print("请在Celery Worker日志中查看处理进度。")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == "__main__":
    test_celery_tasks() 