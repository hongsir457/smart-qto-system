#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸任务核心处理器
负责主要的Celery任务逻辑和流程控制
"""

import os
import sys
import logging
import tempfile
import asyncio
import time
import json
from typing import Dict, Any, List
from pathlib import Path

from celery import Task
from sqlalchemy.orm import Session

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.database import get_celery_db_session
from app.models.drawing import Drawing
from app.models.user import User
from app.core.celery_app import celery_app
from app.services.s3_service import S3Service
from app.services.file_processor import FileProcessor
from app.services.unified_quantity_engine import UnifiedQuantityEngine
from app.services.ocr.paddle_ocr import PaddleOCRService
from app.tasks.real_time_task_manager import RealTimeTaskManager, TaskStatus, TaskStage
from app.services.s3_service import s3_service
from app.services.file_processor import FileProcessor
from app.services.vision_scanner import VisionScannerService
from app.database import SessionLocal
from app.tasks.task_status_pusher import track_progress
from app.tasks import task_manager

logger = logging.getLogger(__name__)

class CallbackTask(Task):
    """回调任务基类"""
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"任务成功: {task_id}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"任务失败: {task_id}, 错误: {exc}")

class DrawingTasksCore:
    """图纸任务核心处理器"""
    
    def __init__(self):
        """初始化核心处理器"""
        self.file_processor = None
        self.quantity_engine = None
        self.vision_scanner = None
        
        # 初始化服务组件
        try:
            self.file_processor = FileProcessor()
        except Exception as e:
            logger.warning(f"⚠️ 文件处理器初始化失败: {e}")
        
        try:
            self.quantity_engine = UnifiedQuantityEngine()
        except Exception as e:
            logger.warning(f"⚠️ 工程量引擎初始化失败: {e}")
        
        try:
            self.vision_scanner = VisionScannerService()
        except Exception as e:
            logger.warning(f"⚠️ Vision扫描器初始化失败: {e}")

    @celery_app.task(bind=True, base=CallbackTask, name='process_drawing_upload')
    def process_drawing_celery_task(self, db_drawing_id: int, task_id: str):
        """
        统一文件处理任务 - 支持DWG/PDF/图片三种文件类型
        
        Args:
            self: Celery任务实例
            db_drawing_id: 数据库中的图纸ID
            task_id: 实时任务ID
        """
        
        logger.info(f"🚀 开始Celery统一文件处理任务: 图纸ID={db_drawing_id}, 任务ID={task_id}")
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        local_file_path = None
        temp_files = []
        
        try:
            with get_celery_db_session() as db:
                # 阶段1: 任务初始化
                loop.run_until_complete(
                    task_manager.update_task_status(
                        task_id, TaskStatus.PROCESSING, TaskStage.INITIALIZING,
                        progress=5, message="Celery Worker 正在初始化任务..."
                    )
                )
                
                # 1️⃣ 获取图纸信息
                drawing = db.query(Drawing).filter(Drawing.id == db_drawing_id).first()
                if not drawing:
                    raise ValueError(f"找不到图纸记录: ID={db_drawing_id}")
                
                logger.info(f"📄 处理图纸: {drawing.filename} (类型: {drawing.file_type})")
                
                # 阶段2: 文件下载
                loop.run_until_complete(
                    task_manager.update_task_status(
                        task_id, TaskStatus.PROCESSING, TaskStage.FILE_PROCESSING,
                        progress=10, message="Celery Worker 正在下载文件..."
                    )
                )
                
                # 2️⃣ 从S3下载文件
                logger.info(f"📥 从双重存储下载文件: {drawing.filename}")
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{drawing.file_type}")
                temp_file.close()
                local_file_path = temp_file.name
                
                success = s3_service.download_file(drawing.s3_key, local_file_path)
                if not success:
                    raise Exception(f"文件下载失败: {drawing.s3_key}")
                
                logger.info(f"✅ 文件下载成功: {local_file_path}")
                
                # 阶段3: 文件处理和转换
                loop.run_until_complete(
                    task_manager.update_task_status(
                        task_id, TaskStatus.PROCESSING, TaskStage.FILE_PROCESSING,
                        progress=20, message="Celery Worker 正在处理文件..."
                    )
                )
                
                # 3️⃣ 文件处理和转换
                logger.info(f"🔄 开始文件处理: {drawing.file_type}")
                
                # 委托给图像处理器
                from .drawing_image_processor import DrawingImageProcessor
                image_processor = DrawingImageProcessor(self)
                
                file_result = image_processor.process_file(
                    local_file_path, drawing, task_id, loop
                )
                
                if not file_result["success"]:
                    raise Exception(f"文件处理失败: {file_result.get('error', '未知错误')}")
                
                temp_files = file_result.get("temp_files", [])
                source_type = file_result.get("source_type", "unknown")
                
                # 后续处理逻辑...
                # 使用双轨协同分析
                logger.info("🔍 开始双轨协同分析...")
                
                # 委托给结果管理器
                from .drawing_result_manager import DrawingResultManager
                result_manager = DrawingResultManager(self)
                
                analysis_result = result_manager.perform_dual_track_analysis(
                    temp_files, drawing, task_id, loop
                )
                
                if not analysis_result["success"]:
                    logger.warning(f"⚠️ 分析失败: {analysis_result.get('error', '未知错误')}")
                
                # 更新数据库状态
                drawing.status = 'completed'
                drawing.component_count = len(analysis_result.get("components", []))
                db.commit()
                
                # 更新实时任务状态
                loop.run_until_complete(
                    task_manager.update_task_status(
                        task_id, TaskStatus.SUCCESS, TaskStage.COMPLETED,
                        progress=100, message="任务处理完成"
                    )
                )
                
                return {
                    'status': 'success',
                    'drawing_id': db_drawing_id,
                    'source_type': source_type,
                    'pipeline_type': 'Dual-Track Analysis',
                    'components_count': len(analysis_result.get("components", [])),
                    'processed_images': len(temp_files),
                    'ai_model': 'GPT-4o',
                    'summary': analysis_result.get("summary", {}),
                    'message': 'Dual-Track Analysis处理流程成功完成'
                }
                
        except Exception as e:
            logger.error(f"❌ 任务处理失败: {e}", exc_info=True)
            
            # 更新数据库中的图纸状态为失败
            with get_celery_db_session() as db:
                drawing = db.query(Drawing).filter(Drawing.id == db_drawing_id).first()
                if drawing:
                    drawing.status = 'failed'
                    drawing.error_message = str(e)
                    db.commit()

            # 更新实时任务状态为失败
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id,
                    TaskStatus.FAILURE,
                    TaskStage.FAILED,
                    progress=0,
                    message=f"任务处理失败: {e}",
                    error_message=str(e)
                )
            )
        
        finally:
            if 'loop' in locals() and loop:
                loop.close()
            
            # 清理临时文件
            logger.info("🧹 开始清理临时文件...")
            try:
                # 清理本地下载的文件
                if local_file_path and os.path.exists(local_file_path):
                    os.unlink(local_file_path)
                    logger.info(f"🗑️ 已清理本地文件: {local_file_path}")
                
                # 清理文件处理产生的临时文件
                if temp_files and self.file_processor:
                    self.file_processor.cleanup_temp_files(temp_files)
                    
            except Exception as cleanup_error:
                logger.warning(f"清理临时文件失败: {cleanup_error}")

    @celery_app.task(bind=True, base=CallbackTask, name='batch_process_drawings')
    def batch_process_drawings_celery_task(self, drawing_tasks: list):
        """
        批量处理图纸任务
        
        Args:
            self: Celery任务实例
            drawing_tasks: 图纸任务列表
        """
        
        logger.info(f"🚀 开始批量处理图纸任务: {len(drawing_tasks)} 个任务")
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for i, task_data in enumerate(drawing_tasks):
            try:
                db_drawing_id = task_data.get('drawing_id')
                task_id = task_data.get('task_id')
                
                logger.info(f"📄 处理批量任务 {i+1}/{len(drawing_tasks)}: 图纸ID={db_drawing_id}")
                
                # 调用单个图纸处理任务
                result = self.process_drawing_celery_task(db_drawing_id, task_id)
                
                if result.get('status') == 'success':
                    successful_count += 1
                    results.append({
                        'drawing_id': db_drawing_id,
                        'task_id': task_id,
                        'status': 'success',
                        'result': result
                    })
                else:
                    failed_count += 1
                    results.append({
                        'drawing_id': db_drawing_id,
                        'task_id': task_id,
                        'status': 'failed',
                        'error': result.get('error', '处理失败')
                    })
                    
            except Exception as e:
                logger.error(f"❌ 批量任务处理失败: {e}")
                failed_count += 1
                results.append({
                    'drawing_id': task_data.get('drawing_id'),
                    'task_id': task_data.get('task_id'),
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"✅ 批量处理完成: 成功 {successful_count}, 失败 {failed_count}")
        
        return {
            'status': 'completed',
            'total_tasks': len(drawing_tasks),
            'successful_count': successful_count,
            'failed_count': failed_count,
            'results': results
        }

    def get_status(self) -> Dict[str, Any]:
        """获取核心处理器状态"""
        return {
            'version': 'DrawingTasksCore v2.0.0',
            'file_processor_available': self.file_processor is not None,
            'quantity_engine_available': self.quantity_engine is not None,
            'vision_scanner_available': self.vision_scanner is not None,
            'celery_tasks_registered': True
        }

    def cleanup(self):
        """清理资源"""
        logger.info("🧹 DrawingTasksCore 资源清理完成") 