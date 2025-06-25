#!/usr/bin/env python3
"""
重新处理失败图纸的脚本
"""

import os
import sys
import uuid

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.drawing import Drawing
from app.tasks.drawing_tasks import process_drawing_celery_task
from app.services.real_time_task_manager import task_manager

def retry_failed_drawings():
    """重新处理失败的图纸"""
    print("🔄 开始重新处理失败的图纸")
    
    db = SessionLocal()
    try:
        # 获取失败的图纸
        failed_drawings = db.query(Drawing).filter(
            Drawing.status == "failed",
            Drawing.s3_key.isnot(None)
        ).limit(3).all()
        
        print(f"📋 找到 {len(failed_drawings)} 个失败的图纸")
        
        for drawing in failed_drawings:
            print(f"\n🔄 重新处理图纸 {drawing.id}: {drawing.filename}")
            print(f"📁 S3键: {drawing.s3_key}")
            print(f"❌ 原错误: {drawing.error_message}")
            
            try:
                # 重置图纸状态
                drawing.status = "pending"
                drawing.error_message = None
                db.commit()
                
                # 创建新的任务ID
                task_id = str(uuid.uuid4())
                
                # 创建任务管理器任务
                task_manager.create_task(
                    task_id=task_id,
                    name=f"重试图纸处理：{drawing.filename}",
                    user_id=drawing.user_id,
                    metadata={
                        "drawing_id": drawing.id,
                        "file_name": drawing.filename,
                        "operation": "retry_process",
                        "s3_key": drawing.s3_key
                    }
                )
                
                # 启动 Celery 任务
                celery_task = process_drawing_celery_task.delay(drawing.id, task_id)
                
                print(f"✅ 已提交重试任务: {celery_task.id}")
                print(f"📋 任务管理器ID: {task_id}")
                
            except Exception as e:
                print(f"❌ 重试提交失败: {e}")
                
    finally:
        db.close()

def reset_drawing_status():
    """重置特定图纸状态为pending，方便重新处理"""
    print("\n🔄 重置图纸状态")
    
    db = SessionLocal()
    try:
        # 获取失败的图纸
        failed_drawings = db.query(Drawing).filter(
            Drawing.status == "failed",
            Drawing.s3_key.isnot(None)
        ).all()
        
        for drawing in failed_drawings:
            drawing.status = "pending"
            drawing.error_message = None
            print(f"🔄 重置图纸 {drawing.id}: {drawing.filename}")
        
        db.commit()
        print(f"✅ 已重置 {len(failed_drawings)} 个图纸状态")
        
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 失败图纸重试工具")
    print("=" * 50)
    
    choice = input("选择操作:\n1. 重新处理失败图纸\n2. 只重置状态\n请输入(1/2): ").strip()
    
    if choice == "1":
        retry_failed_drawings()
    elif choice == "2":
        reset_drawing_status()
    else:
        print("❌ 无效选择")
        return
    
    print("\n" + "=" * 50)
    print("🎯 操作完成")

if __name__ == "__main__":
    main() 