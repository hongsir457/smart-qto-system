import os
import traceback
import time
import gc
import json
import base64
import gzip
import uuid
import tempfile
import shutil
from typing import Optional, Tuple
from urllib.parse import urlparse, unquote
import requests
from celery import Celery
from PIL import Image
import logging
import asyncio

from app.database import SessionLocal, with_db_retry, SafeDBSession
from app.models.drawing import Drawing
from app.services.dwg_processor import DWGProcessor
from app.services.quantity import QuantityCalculator
from app.services.component_detection import ComponentDetector
from app.core.config import settings
from app.core.celery_app import celery_app  # 使用统一的Celery实例
from sqlalchemy.orm import Session
from app.models import user, drawing as drawing_model
from app.models.drawing import Drawing
from app.services.quantity import QuantityCalculator
from app.services.component_detection import ComponentDetector
from app.services.recognition_to_quantity_converter import RecognitionToQuantityConverter
import cv2
import numpy as np
from ultralytics import YOLO
import pytesseract
from pathlib import Path
import mimetypes
import re

# 添加AI OCR导入
from app.services.ai_ocr import extract_text_with_ai
# 新增: 导入ChatGPT分析器
from app.services.chatgpt_quantity_analyzer import ChatGPTQuantityAnalyzer
# 新增: 导入fitz (PyMuPDF)
import fitz

# 设置PIL图像大小限制，解除默认的安全限制
Image.MAX_IMAGE_PIXELS = None

# 初始化构件检测器
component_detector = ComponentDetector()

# 加载YOLO模型
model = None
model_path = os.path.join(settings.MODEL_PATH, 'best.pt')

# <--- 在这里添加 logger 实例的创建
logger = logging.getLogger(__name__)

# 导入WebSocket进度推送函数
try:
    from app.api.v1.endpoints.websocket import push_task_progress, push_user_notification
    WEBSOCKET_AVAILABLE = True
except ImportError:
    logger.warning("WebSocket模块不可用，将跳过实时进度推送")
    WEBSOCKET_AVAILABLE = False
    
    # 创建空的占位函数
    async def push_task_progress(task_id: str, progress_data: dict):
        pass
    
    async def push_user_notification(user_id: int, notification: dict):
        pass

# 异步推送进度的辅助函数
def sync_push_progress(task_id: str, progress_data: dict):
    """同步方式推送进度（在Celery任务中使用）"""
    if WEBSOCKET_AVAILABLE:
        try:
            # 在新的事件循环中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(push_task_progress(task_id, progress_data))
            loop.close()
        except Exception as e:
            logger.warning(f"推送进度失败: {e}")

def sync_push_notification(user_id: int, notification: dict):
    """同步方式推送通知（在Celery任务中使用）"""
    if WEBSOCKET_AVAILABLE:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(push_user_notification(user_id, notification))
            loop.close()
        except Exception as e:
            logger.warning(f"推送通知失败: {e}")

def load_yolo_model():
    """
    安全地加载YOLO模型
    """
    global model
    try:
        if not os.path.exists(model_path):
            print(f"警告: YOLO模型文件不存在: {model_path}")
            return None
            
        if model is None:
            model = YOLO(model_path)
        return model
    except Exception as e:
        print(f"警告: 加载YOLO模型失败: {str(e)}")
        return None

@celery_app.task(name='app.services.drawing.process_drawing', bind=True)
def process_drawing(self, drawing_id: int):
    """
    异步处理图纸 - 优化版本，包含数据库连接重试和错误处理
    """
    from app.database import SafeDBSession, with_db_retry
    from app.models.drawing import Drawing
    from app.services.quantity import QuantityCalculator
    from app.services.recognition_to_quantity_converter import RecognitionToQuantityConverter
    import traceback
    import gc
    
    local_file = None
    max_retries = 3
    task_id = self.request.id
    
    # 推送任务开始通知
    sync_push_progress(task_id, {
        "stage": "started",
        "progress": 0,
        "message": "开始处理图纸...",
        "drawing_id": drawing_id
    })
    
    for attempt in range(max_retries):
        try:
            with SafeDBSession() as db:
                # 查询图纸
                drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
                if not drawing:
                    sync_push_progress(task_id, {
                        "stage": "error",
                        "progress": 0,
                        "message": f"图纸不存在: {drawing_id}",
                        "error": True
                    })
                    return {"error": f"图纸不存在: {drawing_id}"}
                
                # 更新状态为处理中
                drawing.status = "processing"
                drawing.task_id = self.request.id
                try:
                    db.commit()
                except Exception as commit_error:
                    db.rollback()
                    continue  # 提交失败，重试
                
                # 更新任务状态
                self.update_state(state='PROCESSING', meta={'status': '正在处理图纸...'})
                sync_push_progress(task_id, {
                    "stage": "processing",
                    "progress": 10,
                    "message": "正在准备文件...",
                    "drawing_id": drawing_id
                })
                
                # 确保文件在本地可用
                try:
                    local_file = _ensure_local_file(drawing.file_path)
                    sync_push_progress(task_id, {
                        "stage": "processing",
                        "progress": 20,
                        "message": "文件准备完成，开始识别构件...",
                        "drawing_id": drawing_id
                    })
                except Exception as e:
                    drawing.status = "error"
                    drawing.error_message = str(e)
                    drawing.task_id = self.request.id
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()
                    
                    sync_push_progress(task_id, {
                        "stage": "error",
                        "progress": 20,
                        "message": f"文件准备失败: {str(e)}",
                        "error": True
                    })
                    return {"error": str(e)}
                
                # 根据文件类型处理
                try:
                    sync_push_progress(task_id, {
                        "stage": "processing",
                        "progress": 30,
                        "message": f"正在识别{drawing.file_type.upper()}文件中的构件...",
                        "drawing_id": drawing_id
                    })
                    
                    if drawing.file_type == "pdf":
                        recognition_results = process_pdf(local_file)
                    elif drawing.file_type in ["dwg", "dxf"]:
                        recognition_results = process_dwg(local_file)
                    else:
                        recognition_results = process_image(local_file)
                    
                    sync_push_progress(task_id, {
                        "stage": "processing",
                        "progress": 60,
                        "message": "构件识别完成，正在转换数据格式...",
                        "drawing_id": drawing_id
                    })
                    
                    # 使用转换器将识别结果转换为工程量计算格式
                    converter = RecognitionToQuantityConverter()
                    converted_results = converter.convert_recognition_results(recognition_results)
                    
                    sync_push_progress(task_id, {
                        "stage": "processing",
                        "progress": 80,
                        "message": "正在计算工程量...",
                        "drawing_id": drawing_id
                    })
                    
                    # 计算工程量
                    quantities = QuantityCalculator.process_recognition_results(converted_results)
                    
                    sync_push_progress(task_id, {
                        "stage": "processing",
                        "progress": 90,
                        "message": "正在保存结果...",
                        "drawing_id": drawing_id
                    })
                    
                    # 准备最终结果
                    final_results = {
                        "recognition": recognition_results,
                        "converted": converted_results,
                        "quantities": quantities
                    }
                    
                    # 分块保存大数据（避免32276字符截断问题）
                    try:
                        # 先尝试直接保存
                        drawing.recognition_results = final_results
                        drawing.status = "completed"
                        drawing.error_message = None
                        drawing.task_id = self.request.id
                        
                        try:
                            db.commit()
                            print(f"[处理] 图纸处理完成: {drawing_id}")
                            
                            # 推送完成通知
                            sync_push_progress(task_id, {
                                "stage": "completed",
                                "progress": 100,
                                "message": "图纸处理完成！",
                                "drawing_id": drawing_id,
                                "results": {
                                    "total_components": sum(len(comp_list) for comp_list in recognition_results.get("components", {}).values()) if isinstance(recognition_results.get("components"), dict) else 0,
                                    "quantities_calculated": bool(quantities)
                                }
                            })
                            
                            return {
                                "status": "completed",
                                "message": "图纸处理完成",
                                "results": drawing.recognition_results
                            }
                        except Exception as commit_error:
                            db.rollback()
                            # 如果直接保存失败，尝试压缩数据
                            import json
                            import gzip
                            import base64
                            
                            sync_push_progress(task_id, {
                                "stage": "processing",
                                "progress": 95,
                                "message": "数据较大，正在压缩保存...",
                                "drawing_id": drawing_id
                            })
                            
                            # 压缩大型结果数据
                            compressed_data = gzip.compress(
                                json.dumps(final_results, ensure_ascii=False).encode('utf-8')
                            )
                            compressed_b64 = base64.b64encode(compressed_data).decode('ascii')
                            
                            drawing.recognition_results = {
                                "compressed": True,
                                "data": compressed_b64,
                                "summary": {
                                    "status": "completed",
                                    "total_size": len(json.dumps(final_results)),
                                    "compressed_size": len(compressed_b64)
                                }
                            }
                            
                            try:
                                db.commit()
                                print(f"[处理] 图纸处理完成(压缩): {drawing_id}")
                                
                                sync_push_progress(task_id, {
                                    "stage": "completed",
                                    "progress": 100,
                                    "message": "图纸处理完成（数据已压缩）！",
                                    "drawing_id": drawing_id,
                                    "compressed": True
                                })
                                
                                return {
                                    "status": "completed",
                                    "message": "图纸处理完成(数据已压缩)",
                                    "compressed": True
                                }
                            except Exception:
                                db.rollback()
                    
                    except Exception as save_error:
                        print(f"[处理] 保存结果失败: {save_error}")
                        # 保存基本信息
                        drawing.recognition_results = {
                            "status": "completed",
                            "error": "结果过大，无法保存完整数据",
                            "summary": str(final_results)[:1000] + "..."
                        }
                        drawing.status = "completed"
                        drawing.error_message = f"保存警告: {save_error}"
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()
                        
                        sync_push_progress(task_id, {
                            "stage": "completed",
                            "progress": 100,
                            "message": "图纸处理完成，但结果数据过大",
                            "drawing_id": drawing_id,
                            "warning": str(save_error)
                        })
                        
                        return {
                            "status": "completed",
                            "message": "图纸处理完成，但结果数据过大",
                            "warning": str(save_error)
                        }
                        
                except Exception as e:
                    error_msg = f"处理失败: {str(e)}"
                    print(f"[处理] {error_msg}")
                    print(f"[处理] 错误详情: {traceback.format_exc()}")
                    
                    drawing.status = "error"
                    drawing.error_message = error_msg
                    drawing.task_id = self.request.id
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()
                    
                    sync_push_progress(task_id, {
                        "stage": "error",
                        "progress": 50,
                        "message": f"处理失败: {error_msg}",
                        "error": True,
                        "drawing_id": drawing_id
                    })
                    
                    return {"error": error_msg}
                    
        except Exception as db_error:
            error_msg = f"数据库操作失败 (尝试 {attempt + 1}/{max_retries}): {str(db_error)}"
            print(f"[处理] {error_msg}")
            
            if attempt < max_retries - 1:
                sync_push_progress(task_id, {
                    "stage": "retrying",
                    "progress": 10,
                    "message": f"数据库连接失败，正在重试... (尝试 {attempt + 2}/{max_retries})",
                    "drawing_id": drawing_id
                })
                import time
                time.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                print(f"[处理] 最终失败: {traceback.format_exc()}")
                sync_push_progress(task_id, {
                    "stage": "error",
                    "progress": 0,
                    "message": f"数据库操作最终失败: {str(db_error)}",
                    "error": True,
                    "drawing_id": drawing_id
                })
                return {"error": f"数据库操作最终失败: {str(db_error)}"}
        
        finally:
            # 清理临时文件
            if local_file and local_file != drawing.file_path and os.path.exists(local_file):
                try:
                    os.remove(local_file)
                    print(f"[处理] 已删除临时文件: {local_file}")
                except Exception as e:
                    print(f"[处理] 删除临时文件失败: {str(e)}")
            gc.collect()
        
        # 如果成功，跳出重试循环
        break
    
    sync_push_progress(task_id, {
        "stage": "error",
        "progress": 0,
        "message": "处理失败，已达到最大重试次数",
        "error": True,
        "drawing_id": drawing_id
    })
    return {"error": "处理失败，已达到最大重试次数"}

@celery_app.task(name='app.services.drawing.process_ocr_task', bind=True)
def process_ocr_task(self, drawing_id: int):
    """
    异步处理OCR任务
    """
    from app.database import SafeDBSession
    from app.models.drawing import Drawing
    from app.services.ocr import OCRService
    import traceback
    
    task_id = self.request.id
    
    # 推送任务开始通知
    sync_push_progress(task_id, {
        "stage": "started",
        "progress": 0,
        "message": "开始OCR文字识别...",
        "drawing_id": drawing_id
    })
    
    try:
        with SafeDBSession() as db:
            # 查询图纸
            drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
            if not drawing:
                sync_push_progress(task_id, {
                    "stage": "error",
                    "progress": 0,
                    "message": f"图纸不存在: {drawing_id}",
                    "error": True
                })
                return {"error": f"图纸不存在: {drawing_id}"}
            
            # 更新状态为处理中
            drawing.status = "ocr_processing"
            drawing.task_id = self.request.id
            db.commit()
            
            # 更新任务状态
            self.update_state(state='PROCESSING', meta={'status': '正在进行OCR识别...'})
            sync_push_progress(task_id, {
                "stage": "processing",
                "progress": 20,
                "message": "正在准备OCR识别...",
                "drawing_id": drawing_id
            })
            
            # 确保文件在本地可用
            try:
                local_file = _ensure_local_file(drawing.file_path)
                sync_push_progress(task_id, {
                    "stage": "processing",
                    "progress": 40,
                    "message": "文件准备完成，开始OCR识别...",
                    "drawing_id": drawing_id
                })
            except Exception as e:
                drawing.status = "error"
                drawing.error_message = str(e)
                db.commit()
                
                sync_push_progress(task_id, {
                    "stage": "error",
                    "progress": 40,
                    "message": f"文件准备失败: {str(e)}",
                    "error": True
                })
                return {"error": str(e)}
            
            # 执行OCR识别
            try:
                sync_push_progress(task_id, {
                    "stage": "processing",
                    "progress": 60,
                    "message": "正在执行OCR文字识别...",
                    "drawing_id": drawing_id
                })
                
                ocr_service = OCRService()
                ocr_results = ocr_service.extract_text(local_file)
                
                sync_push_progress(task_id, {
                    "stage": "processing",
                    "progress": 80,
                    "message": "OCR识别完成，正在保存结果...",
                    "drawing_id": drawing_id
                })
                
                # 保存OCR结果
                drawing.ocr_results = ocr_results
                drawing.status = "ocr_completed"
                drawing.error_message = None
                db.commit()
                
                print(f"[OCR] OCR处理完成: {drawing_id}")
                
                sync_push_progress(task_id, {
                    "stage": "completed",
                    "progress": 100,
                    "message": "OCR文字识别完成！",
                    "drawing_id": drawing_id,
                    "results": {
                        "text_blocks": len(ocr_results.get("text_blocks", [])) if isinstance(ocr_results, dict) else 0,
                        "total_text": len(str(ocr_results)) if ocr_results else 0
                    }
                })
                
                return {
                    "status": "completed",
                    "message": "OCR处理完成",
                    "results": ocr_results
                }
                
            except Exception as e:
                error_msg = f"OCR处理失败: {str(e)}"
                print(f"[OCR] {error_msg}")
                print(f"[OCR] 错误详情: {traceback.format_exc()}")
                
                drawing.status = "error"
                drawing.error_message = error_msg
                db.commit()
                
                sync_push_progress(task_id, {
                    "stage": "error",
                    "progress": 60,
                    "message": f"OCR识别失败: {error_msg}",
                    "error": True,
                    "drawing_id": drawing_id
                })
                
                return {"error": error_msg}
            
            finally:
                # 清理临时文件
                if local_file and local_file != drawing.file_path and os.path.exists(local_file):
                    try:
                        os.remove(local_file)
                        print(f"[OCR] 已删除临时文件: {local_file}")
                    except Exception as e:
                        print(f"[OCR] 删除临时文件失败: {str(e)}")
                        
    except Exception as e:
        error_msg = f"数据库操作失败: {str(e)}"
        print(f"[OCR] {error_msg}")
        print(f"[OCR] 错误详情: {traceback.format_exc()}")
        
        sync_push_progress(task_id, {
            "stage": "error",
            "progress": 0,
            "message": f"数据库操作失败: {error_msg}",
            "error": True,
            "drawing_id": drawing_id
        })
        
        return {"error": error_msg}

@celery_app.task(name='app.services.drawing.process_dwg_multi_sheets', bind=True)
def process_dwg_multi_sheets(self, drawing_id: int):
    """
    Celery任务：处理DWG文件的多图框识别 - 优化版本
    """
    from app.database import SafeDBSession
    from app.models.drawing import Drawing
    from app.services.quantity import QuantityCalculator
    import traceback
    import gc
    import json
    import gzip
    import base64
    
    local_file = None
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with SafeDBSession() as db:
                # 更新任务状态
                self.update_state(state='STARTED', meta={'status': '开始处理DWG多图框...'})
                
                drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
                if not drawing:
                    print(f"[DWG多图框] 图纸不存在: {drawing_id}")
                    return {"error": "图纸不存在"}
                    
                try:
                    # 更新任务状态
                    self.update_state(state='PROCESSING', meta={'status': '正在检测图框和分割图纸...'})
                    
                    # 确保文件在本地可用
                    try:
                        local_file = _ensure_local_file(drawing.file_path)
                    except Exception as e:
                        drawing.status = "error"
                        drawing.error_message = str(e)
                        drawing.task_id = self.request.id
                        db.commit()
                        return {"error": str(e)}
                    
                    # 使用DWG处理器
                    from app.services.dwg_processor import DWGProcessor
                    
                    processor = DWGProcessor()
                    result = processor.process_multi_sheets(local_file)
                    
                    if "error" in result:
                        drawing.status = "error"
                        drawing.error_message = result["error"]
                        drawing.task_id = self.request.id
                        db.commit()
                        return {"error": result["error"]}
                    
                    # 计算工程量
                    if result.get("type") == "multiple_drawings":
                        # 多图纸情况
                        self.update_state(state='PROCESSING', meta={'status': '正在计算多图纸工程量...'})
                        
                        # 汇总所有图纸的构件
                        all_components = result.get("summary", {}).get("total_components", {})
                        
                        # 计算总工程量
                        quantities = QuantityCalculator.process_recognition_results({
                            "components": all_components,
                            "text": result.get("summary", {}).get("all_text", "")
                        })
                        
                        # 为每张图纸计算独立工程量
                        for drawing_data in result.get("drawings", []):
                            drawing_components = drawing_data.get("components", {})
                            drawing_quantities = QuantityCalculator.process_recognition_results({
                                "components": drawing_components,
                                "text": drawing_data.get("text", "")
                            })
                            drawing_data["quantities"] = drawing_quantities
                        
                        # 保存结果
                        recognition_results = {
                            "recognition": result,
                            "quantities": quantities,
                            "type": "multiple_drawings",
                            "drawings": result.get("drawings", []),
                            "statistics": {
                                "total_drawings": result.get("total_drawings", 0),
                                "processed_drawings": result.get("processed_drawings", 0),
                                "drawing_list": [
                                    {
                                        "number": d.get("number", ""),
                                        "title": d.get("title", ""),
                                        "scale": d.get("scale", ""),
                                        "component_count": d.get("summary", {}).get("total_components", 0)
                                    }
                                    for d in result.get("drawings", [])
                                ]
                            }
                        }
                        
                    else:
                        # 单图纸情况
                        self.update_state(state='PROCESSING', meta={'status': '正在计算单图纸工程量...'})
                        
                        # 计算工程量
                        quantities = QuantityCalculator.process_recognition_results(result)
                        
                        recognition_results = {
                            "recognition": result,
                            "quantities": quantities,
                            "type": "single_drawing"
                        }
                    
                    # 安全保存大型结果数据
                    try:
                        # 尝试直接保存
                        drawing.recognition_results = recognition_results
                        drawing.status = "completed"
                        drawing.error_message = None
                        drawing.task_id = self.request.id
                        
                        try:
                            db.commit()
                            print(f"[DWG多图框] 处理完成: {drawing_id}")
                            return {
                                "status": "completed",
                                "message": "DWG多图框处理完成",
                                "results": drawing.recognition_results
                            }
                        except Exception as commit_error:
                            db.rollback()
                            # 如果直接保存失败，尝试压缩数据
                            import json
                            import gzip
                            import base64
                            
                            # 压缩大型结果数据
                            compressed_data = gzip.compress(
                                json.dumps(recognition_results, ensure_ascii=False).encode('utf-8')
                            )
                            compressed_b64 = base64.b64encode(compressed_data).decode('ascii')
                            
                            drawing.recognition_results = {
                                "compressed": True,
                                "data": compressed_b64,
                                "type": recognition_results.get("type", "unknown"),
                                "summary": {
                                    "status": "completed",
                                    "total_size": len(json.dumps(recognition_results)),
                                    "compressed_size": len(compressed_b64),
                                    "total_drawings": recognition_results.get("statistics", {}).get("total_drawings", 1)
                                }
                            }
                            
                            try:
                                db.commit()
                                print(f"[DWG多图框] 处理完成(压缩): {drawing_id}")
                                return {
                                    "status": "completed",
                                    "message": "DWG多图框处理完成(数据已压缩)",
                                    "compressed": True
                                }
                            except Exception:
                                db.rollback()
                    
                    except Exception as save_error:
                        print(f"[DWG多图框] 保存结果失败: {save_error}")
                        # 保存基本信息
                        drawing.recognition_results = {
                            "status": "completed",
                            "type": recognition_results.get("type", "unknown"),
                            "error": "结果过大，无法保存完整数据",
                            "summary": str(recognition_results)[:1000] + "..."
                        }
                        drawing.status = "completed"
                        drawing.error_message = f"保存警告: {save_error}"
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()
                        
                        return {
                            "status": "completed",
                            "message": "DWG多图框处理完成，但结果数据过大",
                            "warning": str(save_error)
                        }
                        
                except Exception as e:
                    error_msg = f"DWG多图框处理失败: {str(e)}"
                    print(f"[DWG多图框] {error_msg}")
                    print(f"[DWG多图框] 错误详情: {traceback.format_exc()}")
                    drawing.status = "error"
                    drawing.error_message = error_msg
                    drawing.task_id = self.request.id
                    db.commit()
                    return {"error": error_msg}
                    
        except Exception as db_error:
            error_msg = f"数据库操作失败 (尝试 {attempt + 1}/{max_retries}): {str(db_error)}"
            print(f"[DWG多图框] {error_msg}")
            
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
            else:
                print(f"[DWG多图框] 最终失败: {traceback.format_exc()}")
                return {"error": f"数据库操作最终失败: {str(db_error)}"}
        
        finally:
            # 清理临时文件
            if local_file and local_file != drawing.file_path and os.path.exists(local_file):
                try:
                    os.remove(local_file)
                    print(f"[DWG多图框] 已删除临时文件: {local_file}")
                except Exception as e:
                    print(f"[DWG多图框] 删除临时文件失败: {str(e)}")
            gc.collect()
        
        # 如果成功，跳出重试循环
        break
    
    return {"error": "DWG多图框处理失败，已达到最大重试次数"}

def process_image(file_path: str) -> dict:
    """
    处理图片文件并返回识别结果 - 优化版本
    支持多种图片格式和增强错误处理
    """
    try:
        print(f"[process_image] 开始处理图片文件: {file_path}")
        
        if not os.path.exists(file_path):
            return {"error": f"文件不存在: {file_path}"}
        
        # 检查文件格式
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in supported_formats:
            return {"error": f"不支持的图片格式: {file_ext}"}
        
        # 检查文件大小
        try:
            file_size = os.path.getsize(file_path)
            max_size = 50 * 1024 * 1024  # 50MB限制
            
            if file_size > max_size:
                return {"error": f"图片文件过大: {file_size / 1024 / 1024:.1f}MB，超过50MB限制"}
                
            print(f"[process_image] 图片大小: {file_size / 1024 / 1024:.1f}MB")
            
        except Exception as e:
            return {"error": f"检查文件大小失败: {str(e)}"}
        
        # 确保文件在本地可用
        try:
            local_file = _ensure_local_file(file_path)
        except Exception as e:
            return {"error": f"获取本地文件失败: {str(e)}"}
        
        try:
            # 验证图片文件完整性
            from PIL import Image
            try:
                with Image.open(local_file) as img:
                    img.verify()  # 验证图片完整性
                print(f"[process_image] 图片验证通过")
            except Exception as e:
                return {"error": f"图片文件损坏或格式错误: {str(e)}"}
            
            # 识别构件
            print(f"[process_image] 开始构件识别...")
            
            try:
                components = component_detector.detect_components(local_file)
                print(f"[process_image] 构件识别完成，识别到 {sum(components.values())} 个构件")
            except Exception as e:
                print(f"[process_image] 构件识别失败: {str(e)}")
                components = {}
            
            # 提取文字
            print(f"[process_image] 开始文字识别...")
            try:
                text_result = extract_text(local_file)
                
                if isinstance(text_result, dict):
                    if "error" in text_result:
                        print(f"[process_image] 文字识别失败: {text_result['error']}")
                        text = ""
                    else:
                        text = text_result.get("text", "")
                else:
                    text = str(text_result) if text_result else ""
                    
                print(f"[process_image] 文字识别完成，提取文本长度: {len(text)}")
                
            except Exception as e:
                print(f"[process_image] 文字识别异常: {str(e)}")
                text = ""
            
            # 构造返回结果
            result = {
                "components": components,
                "text": text,
                "image_info": {
                    "file_size": file_size,
                    "format": file_ext,
                    "component_count": sum(components.values()),
                    "text_length": len(text)
                }
            }
            
            print(f"[process_image] 图片处理完成")
            return result
            
        except Exception as processing_error:
            error_msg = f"图片处理过程失败: {str(processing_error)}"
            print(f"[process_image] {error_msg}")
            print(f"[process_image] 错误详情: {traceback.format_exc()}")
            return {"error": error_msg}
            
        finally:
            # 清理临时文件
            if local_file != file_path and os.path.exists(local_file):
                try:
                    os.remove(local_file)
                    print(f"[process_image] 已删除临时文件: {local_file}")
                except Exception as e:
                    print(f"[process_image] 删除临时文件失败: {str(e)}")
                    
    except Exception as e:
        error_msg = f"图片文件处理失败: {str(e)}"
        print(f"[process_image] {error_msg}")
        print(f"[process_image] 错误详情: {traceback.format_exc()}")
        return {"error": error_msg}

@celery_app.task(name='app.services.drawing.process_pdf_multi_pages', bind=True)
def process_pdf_multi_pages(self, drawing_id: int):
    """
    Celery任务：处理PDF文件的多页面识别 - 优化版本
    """
    from app.database import SafeDBSession
    from app.models.drawing import Drawing
    from app.services.quantity import QuantityCalculator
    import traceback
    import gc
    import json
    import gzip
    import base64
    
    local_file = None
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with SafeDBSession() as db:
                # 更新任务状态
                self.update_state(state='STARTED', meta={'status': '开始处理PDF多页面...'})
                
                drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
                if not drawing:
                    print(f"[PDF多页面] 图纸不存在: {drawing_id}")
                    return {"error": "图纸不存在"}
                    
                try:
                    # 更新任务状态
                    self.update_state(state='PROCESSING', meta={'status': '正在处理PDF页面...'})
                    
                    # 确保文件在本地可用
                    try:
                        local_file = _ensure_local_file(drawing.file_path)
                    except Exception as e:
                        drawing.status = "error"
                        drawing.error_message = str(e)
                        drawing.task_id = self.request.id
                        db.commit()
                        return {"error": str(e)}
                    
                    # 处理PDF文件
                    pdf_result = process_pdf(local_file)
                    
                    if "error" in pdf_result:
                        drawing.status = "error"
                        drawing.error_message = pdf_result["error"]
                        drawing.task_id = self.request.id
                        db.commit()
                        return {"error": pdf_result["error"]}
                    
                    # 计算工程量
                    self.update_state(state='PROCESSING', meta={'status': '正在计算工程量...'})
                    
                    # 准备识别结果
                    if pdf_result.get("type") == "multiple_pages":
                        # 多页面情况
                        all_components = {}
                        all_text = ""
                        
                        for page_data in pdf_result.get("pages", []):
                            page_components = page_data.get("components", {})
                            page_text = page_data.get("text", "")
                            
                            # 汇总构件
                            for comp_type, count in page_components.items():
                                all_components[comp_type] = all_components.get(comp_type, 0) + count
                            
                            # 汇总文本
                            all_text += page_text + "\n"
                            
                            # 为每页计算独立工程量
                            page_quantities = QuantityCalculator.process_recognition_results({
                                "components": page_components,
                                "text": page_text
                            })
                            page_data["quantities"] = page_quantities
                        
                        # 计算总工程量
                        total_quantities = QuantityCalculator.process_recognition_results({
                            "components": all_components,
                            "text": all_text
                        })
                        
                        recognition_results = {
                            "recognition": pdf_result,
                            "quantities": total_quantities,
                            "type": "multiple_pages",
                            "pages": pdf_result.get("pages", []),
                            "statistics": {
                                "total_pages": pdf_result.get("total_pages", 0),
                                "processed_pages": pdf_result.get("processed_pages", 0),
                                "page_list": [
                                    {
                                        "page": i + 1,
                                        "component_count": len(p.get("components", {}))
                                    }
                                    for i, p in enumerate(pdf_result.get("pages", []))
                                ]
                            }
                        }
                        
                    else:
                        # 单页面情况
                        quantities = QuantityCalculator.process_recognition_results(pdf_result)
                        recognition_results = {
                            "recognition": pdf_result,
                            "quantities": quantities,
                            "type": "single_page"
                        }
                    
                    # 安全保存大型结果数据
                    try:
                        # 尝试直接保存
                        drawing.recognition_results = recognition_results
                        drawing.status = "completed"
                        drawing.error_message = None
                        drawing.task_id = self.request.id
                        
                        try:
                            db.commit()
                            print(f"[PDF多页面] 处理完成: {drawing_id}")
                            return {
                                "status": "completed",
                                "message": "PDF多页面处理完成",
                                "results": drawing.recognition_results
                            }
                        except Exception as commit_error:
                            db.rollback()
                            # 如果直接保存失败，尝试压缩数据
                            import json
                            import gzip
                            import base64
                            
                            # 压缩大型结果数据
                            compressed_data = gzip.compress(
                                json.dumps(recognition_results, ensure_ascii=False).encode('utf-8')
                            )
                            compressed_b64 = base64.b64encode(compressed_data).decode('ascii')
                            
                            drawing.recognition_results = {
                                "compressed": True,
                                "data": compressed_b64,
                                "type": recognition_results.get("type", "unknown"),
                                "summary": {
                                    "status": "completed",
                                    "total_size": len(json.dumps(recognition_results)),
                                    "compressed_size": len(compressed_b64),
                                    "total_pages": recognition_results.get("statistics", {}).get("total_pages", 1)
                                }
                            }
                            
                            try:
                                db.commit()
                                print(f"[PDF多页面] 处理完成(压缩): {drawing_id}")
                                return {
                                    "status": "completed",
                                    "message": "PDF多页面处理完成(数据已压缩)",
                                    "compressed": True
                                }
                            except Exception:
                                db.rollback()
                    
                    except Exception as save_error:
                        print(f"[PDF多页面] 保存结果失败: {save_error}")
                        # 保存基本信息
                        drawing.recognition_results = {
                            "status": "completed",
                            "type": recognition_results.get("type", "unknown"),
                            "error": "结果过大，无法保存完整数据",
                            "summary": str(recognition_results)[:1000] + "..."
                        }
                        drawing.status = "completed"
                        drawing.error_message = f"保存警告: {save_error}"
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()
                        
                        return {
                            "status": "completed",
                            "message": "PDF多页面处理完成，但结果数据过大",
                            "warning": str(save_error)
                        }
                        
                except Exception as e:
                    error_msg = f"PDF多页面处理失败: {str(e)}"
                    print(f"[PDF多页面] {error_msg}")
                    print(f"[PDF多页面] 错误详情: {traceback.format_exc()}")
                    drawing.status = "error"
                    drawing.error_message = error_msg
                    drawing.task_id = self.request.id
                    db.commit()
                    return {"error": error_msg}
                    
        except Exception as db_error:
            error_msg = f"数据库操作失败 (尝试 {attempt + 1}/{max_retries}): {str(db_error)}"
            print(f"[PDF多页面] {error_msg}")
            
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
            else:
                print(f"[PDF多页面] 最终失败: {traceback.format_exc()}")
                return {"error": f"数据库操作最终失败: {str(db_error)}"}
        
        finally:
            # 清理临时文件
            if local_file and local_file != drawing.file_path and os.path.exists(local_file):
                try:
                    os.remove(local_file)
                    print(f"[PDF多页面] 已删除临时文件: {local_file}")
                except Exception as e:
                    print(f"[PDF多页面] 删除临时文件失败: {str(e)}")
            gc.collect()
        
        # 如果成功，跳出重试循环
        break
    
    return {"error": "PDF多页面处理失败，已达到最大重试次数"}

def process_pdf(file_path: str) -> dict:
    """
    处理PDF文件并返回识别结果 - 使用ChatGPT进行分析。
    """
    import traceback # 确保traceback在整个函数作用域内可用
    try:
        print(f"[process_pdf_gpt] 开始使用ChatGPT处理PDF文件: {file_path}")

        if not os.path.exists(file_path):
            return {"error": f"文件不存在: {file_path}"}

        # 基本的PDF文件检查
        try:
            doc = fitz.open(file_path)
            page_count = doc.page_count
            doc.close() 
            if page_count == 0:
                print(f"[process_pdf_gpt] 警告: PDF文件 '{file_path}' 没有页面。")
                return {"type": "single_page", "components": {}, "text": "", "warning": "PDF文件没有页面"}
            print(f"[process_pdf_gpt] PDF文件 '{file_path}' 包含 {page_count} 页。将提交给ChatGPT分析器。")
        except Exception as e:
            error_msg = f"打开或验证PDF文件失败: {str(e)}"
            print(f"[process_pdf_gpt] {error_msg}")
            return {"error": error_msg}

        analyzer = ChatGPTQuantityAnalyzer(api_key=settings.OPENAI_API_KEY)
        
        # 假设 analyze_pdf_for_recognition_data 返回符合后续处理流程的 "recognition_results" 结构
        # 例如: {"components": {...}, "text": "...", "type": "single_page/multiple_pages", ...}
        # 此方法内部应处理PDF页面迭代、图像提取（如果需要）、与GPT交互等。
        recognition_results = analyzer.analyze_drawing_pdf(pdf_path=file_path)

        if "error" in recognition_results:
            print(f"[process_pdf_gpt] ChatGPT分析器返回错误: {recognition_results['error']}")
            return recognition_results

        print(f"[process_pdf_gpt] ChatGPT分析成功: {file_path}")
        return recognition_results

    except Exception as e:
        error_msg = f"使用ChatGPT处理PDF时发生意外错误: {str(e)}"
        print(f"[process_pdf_gpt] {error_msg}")
        print(f"[process_pdf_gpt] 错误详情: {traceback.format_exc()}")
        return {"error": error_msg}

def process_dwg(file_path: str) -> dict:
    """
    处理DWG/DXF CAD文件 - 优化版本
    """
    try:
        print(f"[process_dwg] 开始处理CAD文件: {file_path}")
        
        if not os.path.exists(file_path):
            return {"error": f"文件不存在: {file_path}"}
        
        # 使用DWG处理器
        processor = DWGProcessor()
        result = processor.process_file(file_path)
        
        if "error" in result:
            print(f"[process_dwg] DWG处理器错误: {result['error']}")
            return result
        
        print(f"[process_dwg] CAD文件处理完成")
        return result
        
    except Exception as e:
        error_msg = f"CAD文件处理失败: {str(e)}"
        print(f"[process_dwg] {error_msg}")
        print(f"[process_dwg] 错误详情: {traceback.format_exc()}")
        return {"error": error_msg}

def _ensure_local_file(file_path: str) -> str:
    """
    确保文件在本地可用 - 优化版本
    支持本地文件和远程文件下载，增强错误处理
    """
    import shutil
    import uuid
    import tempfile
    from urllib.parse import urlparse
    import requests
    
    try:
        print(f"[_ensure_local_file] 处理文件路径: {file_path}")
        
        # 检查是否为本地文件
        if os.path.exists(file_path):
            print(f"[_ensure_local_file] 文件在本地存在")
            return file_path
        
        # 检查是否为URL
        parsed = urlparse(file_path)
        if parsed.scheme in ['http', 'https']:
            print(f"[_ensure_local_file] 检测到远程文件，开始下载...")
            
            try:
                # 创建临时文件
                temp_dir = tempfile.gettempdir()
                file_ext = os.path.splitext(parsed.path)[1] or '.tmp'
                temp_filename = f"download_{uuid.uuid4().hex}{file_ext}"
                local_path = os.path.join(temp_dir, temp_filename)
                
                # 下载文件
                response = requests.get(file_path, stream=True, timeout=30)
                response.raise_for_status()
                
                # 检查文件大小
                content_length = response.headers.get('content-length')
                if content_length:
                    file_size = int(content_length)
                    max_size = 100 * 1024 * 1024  # 100MB限制
                    
                    if file_size > max_size:
                        raise Exception(f"远程文件过大: {file_size / 1024 / 1024:.1f}MB，超过100MB限制")
                
                # 保存文件
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 验证下载的文件
                if not os.path.exists(local_path):
                    raise Exception("文件下载失败")
                
                downloaded_size = os.path.getsize(local_path)
                if downloaded_size == 0:
                    os.remove(local_path)
                    raise Exception("下载的文件为空")
                
                print(f"[_ensure_local_file] 文件下载成功: {downloaded_size / 1024 / 1024:.1f}MB")
                return local_path
                
            except requests.exceptions.RequestException as e:
                raise Exception(f"下载文件失败: {str(e)}")
            except Exception as e:
                raise Exception(f"处理远程文件失败: {str(e)}")
        
        # 检查是否为相对路径
        if not os.path.isabs(file_path):
            # 尝试相对于工作目录
            abs_path = os.path.abspath(file_path)
            if os.path.exists(abs_path):
                print(f"[_ensure_local_file] 找到相对路径文件: {abs_path}")
                return abs_path
            
            # 尝试相对于上传目录
            upload_dir = getattr(settings, 'UPLOAD_DIR', './uploads')
            upload_path = os.path.join(upload_dir, file_path)
            if os.path.exists(upload_path):
                print(f"[_ensure_local_file] 找到上传目录文件: {upload_path}")
                return upload_path
        
        # 文件不存在
        raise Exception(f"文件不存在: {file_path}")
        
    except Exception as e:
        error_msg = f"确保本地文件失败: {str(e)}"
        print(f"[_ensure_local_file] {error_msg}")
        raise Exception(error_msg)

def preprocess_image(image, is_cad=False):
    """
    平衡速度和准确率的图像预处理函数
    """
    # 转换为灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    # 适度放大（在速度和效果间平衡）
    scale_factor = 2.0 if is_cad else 1.8
    enlarged = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    
    # 改进的对比度增强
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(enlarged)
    
    # 高质量去噪，保持边缘
    denoised = cv2.bilateralFilter(enhanced, 5, 50, 50)
    
    # 优化的自适应二值化
    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,  # 中等块大小，适合多种文字大小
        3
    )
    
    # 轻微的形态学操作，改善文字清晰度
    kernel = np.ones((2,2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    return cleaned

def process_region(image, lang='chi_sim+eng'):
    """
    平衡的区域处理函数，适度增加PSM模式
    """
    # 增加一个有效的PSM模式，保持合理数量
    psm_modes = [6, 3, 4]  # 3个最有效的模式
    
    # 扩展建筑图纸相关字符，包含更多中文
    special_chars = r'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-+.×÷()[]{}#@/\°∅∠，。、；：！？（）【】《》""''￥%&*'
    
    try:
        best_result = ""
        max_length = 0
        
        for psm in psm_modes:
            try:
                config = f'--oem 1 --psm {psm} -c preserve_interword_spaces=1'
                result = pytesseract.image_to_string(image, lang=lang, config=config).strip()
                
                # 选择最长且有意义的结果
                if result and len(result) > max_length:
                    max_length = len(result)
                    best_result = result
                    
            except Exception as e:
                continue
        
        return best_result
        
    except Exception as e:
        print(f"[OCR] 区域识别失败: {str(e)}")
        return ""
    finally:
        gc.collect()

def extract_text(image_path: str, use_ai: bool = True, ai_provider: str = "auto"):
    """
    优化后的OCR文字提取函数 - 支持传统OCR和AI大模型识别
    
    Args:
        image_path: 图像文件路径
        use_ai: 是否使用AI大模型识别（默认True，优先使用AI OCR）
        ai_provider: AI服务提供商 ("openai", "claude", "baidu", "qwen", "auto")
    """
    import traceback
    import time
    
    print(f"[OCR] 开始处理: {image_path}")
    print(f"[OCR] 使用AI模式: {use_ai}, 服务商: {ai_provider}")
    
    # 如果用户选择AI模式
    if use_ai:
        print(f"[OCR] 使用AI大模型识别: {ai_provider}")
        try:
            from app.services.ai_ocr import extract_text_with_ai
            ai_result = extract_text_with_ai(image_path, ai_provider)
            if "error" not in ai_result:
                print(f"[OCR] AI识别成功，提供商: {ai_result.get('provider', 'unknown')}")
                print(f"[OCR] 识别文字长度: {len(ai_result.get('text', ''))}")
                return ai_result
            else:
                print(f"[OCR] AI识别失败: {ai_result['error']}")
                print("[OCR] 降级使用传统OCR方法...")
                # AI失败时降级使用传统OCR
        except Exception as e:
            print(f"[OCR] AI识别异常: {str(e)}")
            print("[OCR] 降级使用传统OCR方法...")
    
    # 使用传统OCR方法（原有逻辑）
    # 确保Tesseract配置正确
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "tesseract"
    ]
    
    for path in tesseract_paths:
        if os.path.exists(path) or path == "tesseract":
            try:
                pytesseract.pytesseract.tesseract_cmd = path
                break
            except:
                continue
    
    local_path = image_path
    temp_files = []  # 跟踪临时文件
    
    try:
        print(f"[OCR传统] 开始识别: {image_path}")
            
        if not os.path.exists(local_path):
            return {"error": f"文件不存在: {local_path}"}
            
        ext = os.path.splitext(local_path)[-1].lower()
        
        if ext == ".pdf":
            print("[OCR传统] 识别PDF文件")
            try:
                from pdf2image import convert_from_path
                pages = convert_from_path(local_path, dpi=300)
                all_text = ""
                
                for page_num, page in enumerate(pages):
                    print(f"[OCR传统] 处理第{page_num+1}页")
                    
                    # 保存临时图片
                    temp_path = f"temp_page_{page_num}_{int(time.time())}.png"
                    page.save(temp_path, 'PNG')
                    temp_files.append(temp_path)
                    
                    # 对每页进行优化OCR
                    page_result = _extract_text_from_image_optimized(temp_path)
                    if isinstance(page_result, dict) and "text" in page_result:
                        all_text += f"\n--- 第{page_num+1}页 ---\n{page_result['text']}"
                    
                return {"text": all_text} if all_text else {"warning": "PDF中未识别到文字内容"}
                
            except Exception as e:
                print(f"[OCR传统] PDF处理失败: {e}")
                return {"error": f"PDF处理失败: {str(e)}"}
            
        elif ext in [".dwg", ".dxf"]:
            print("[OCR传统] 识别CAD文件")
            try:
                import ezdxf
                doc = ezdxf.readfile(local_path)
                
                # 尝试提取文字实体
                text_entities = []
                for entity in doc.modelspace():
                    if entity.dxftype() == 'TEXT':
                        text_entities.append(entity.dxf.text)
                    elif entity.dxftype() == 'MTEXT':
                        text_entities.append(entity.plain_text())
                
                if text_entities:
                    text = "\n".join(text_entities)
                    return {"text": text}
                else:
                    # 如果没有文字实体，转换为图片后OCR
                    print("[OCR传统] CAD文件无文字实体，转换为图片")
                    return {"warning": "CAD文件处理完成，但未找到文字实体"}
                    
            except Exception as e:
                print(f"[OCR传统] CAD处理失败: {e}")
                return {"error": f"CAD处理失败: {str(e)}"}
                
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            print("[OCR传统] 识别图片文件")
            return _extract_text_from_image_optimized(local_path)
                
        else:
            return {"error": f"不支持的文件格式: {ext}"}
                
    except Exception as e:
        print(f"[OCR传统] 处理失败: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        # 清理临时文件
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        gc.collect()

def _extract_text_from_image_optimized(image_path: str):
    """
    针对建筑图纸优化的图像OCR函数 - 增强版
    使用多种预处理方法和配置组合，提升识别率
    """
    try:
        print(f"[图像OCR] 开始处理: {image_path}")
        
        image = cv2.imread(image_path)
        if image is None:
            return {"error": f"图片读取失败: {image_path}"}
        
        # 方法1: 标准高质量预处理
        result1 = _method_simple_high_quality(image)
        
        # 方法2: 增强预处理（适合低质量图片）
        result2 = _method_enhanced_preprocessing(image)
        
        # 方法3: 多PSM模式组合
        result3 = _method_multi_psm(image)
        
        # 方法4: 多语言配置测试
        result4 = _method_multi_language(image)
        
        # 收集所有结果
        all_results = [
            ("标准质量", result1),
            ("增强预处理", result2),
            ("多PSM模式", result3),
            ("多语言配置", result4)
        ]
        
        # 选择最佳结果（综合考虑长度和质量）
        best_result = ""
        best_method = "无"
        max_score = 0
        
        for method, result in all_results:
            if result and len(result.strip()) > 10:
                # 计算结果质量分数（长度 + 关键词奖励）
                score = len(result)
                
                # 建筑关键词奖励
                building_keywords = ['mm', 'CM', 'M', '墙', '柱', '梁', '板', '基础', 'Wall', 'Column', 'Beam', 'Slab']
                for keyword in building_keywords:
                    if keyword in result:
                        score += 50
                
                # 数字密度奖励（建筑图纸通常包含大量尺寸）
                import re
                numbers = re.findall(r'\d+', result)
                score += len(numbers) * 2
                
                if score > max_score:
                    max_score = score
                    best_result = result
                    best_method = method
        
        # 后处理优化
        if best_result:
            final_text = _enhanced_post_process(best_result)
            print(f"[图像OCR] 最佳方法: {best_method}, 得分: {max_score}")
            print(f"[图像OCR] 识别完成，提取: {len(final_text)} 字符")
            return {"text": final_text, "method": best_method, "score": max_score}
        else:
            print("[图像OCR] 所有方法都未能识别到有效文字")
            return {"warning": "未识别到文字内容"}
        
    except Exception as e:
        print(f"[图像OCR] 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def _method_multi_psm(image):
    """使用多种PSM模式的OCR方法"""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 自适应二值化
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # 测试多种PSM模式
        psm_modes = [6, 3, 4, 8, 11, 13]
        best_result = ""
        
        for psm in psm_modes:
            try:
                config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
                result = pytesseract.image_to_string(adaptive, lang='chi_sim+eng', config=config).strip()
                if len(result) > len(best_result):
                    best_result = result
            except:
                continue
        
        return best_result
    except:
        return ""

def _method_multi_language(image):
    """使用多种语言配置的OCR方法"""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # OTSU二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 测试多种语言配置
        lang_configs = [
            'chi_sim+eng',
            'eng+chi_sim',
            'chi_sim',
            'eng',
            'chi_tra+eng'  # 繁体中文
        ]
        
        best_result = ""
        config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        
        for lang in lang_configs:
            try:
                result = pytesseract.image_to_string(binary, lang=lang, config=config).strip()
                if len(result) > len(best_result):
                    best_result = result
            except:
                continue
        
        return best_result
    except:
        return ""

def _enhanced_post_process(text):
    """增强的后处理函数"""
    if not text:
        return text
    
    # 基本清理
    text = text.replace('\n\n', '\n').replace('\r', '')
    
    # 修复常见的OCR错误
    corrections = {
        'O': '0',  # 字母O误识别为数字0的情况
        'l': '1',  # 小写L误识别为数字1的情况（在数字上下文中）
        '|': '1',  # 竖线误识别
        'S': '5',  # 在数字上下文中
        'B': '8',  # 在数字上下文中
    }
    
    # 只在数字上下文中进行修正
    import re
    
    # 修复尺寸标注中的常见错误
    text = re.sub(r'(\d+)O(\d+)', r'\1 0\2', text)  # 修复类似 "123O456" 的错误
    text = re.sub(r'(\d+)l(\d+)', r'\1 1\2', text)  # 修复类似 "123l456" 的错误
    
    # 保留重要的空格和格式
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line and len(line) > 1:  # 过滤掉单字符行
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def _method_simple_high_quality(image):
    """方法0: 简单高质量方法（基准）"""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 简单但有效的预处理
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # 自适应二值化，保持文字清晰
        binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        
        # 使用最稳定的PSM模式
        config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        result = pytesseract.image_to_string(binary, lang='chi_sim+eng', config=config)
        
        return result.strip()
        
    except Exception as e:
        print(f"[基准方法] 失败: {e}")
        return ""

def _calculate_text_quality(text):
    """计算文本质量分数"""
    if not text or len(text.strip()) < 3:
        return 0.0
    
    text = text.strip()
    total_chars = len(text)
    
    # 基础分数
    score = 0.0
    
    # 1. 字母数字比例（建筑图纸主要是英文和数字）
    alnum_chars = sum(1 for c in text if c.isalnum())
    alnum_ratio = alnum_chars / total_chars if total_chars > 0 else 0
    score += alnum_ratio * 0.4
    
    # 2. 特殊字符比例（适量的特殊字符是正常的）
    special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace() and c in '.-+()[]{}:/')
    special_ratio = special_chars / total_chars if total_chars > 0 else 0
    if special_ratio < 0.2:  # 特殊字符不超过20%
        score += 0.2
    
    # 3. 垃圾字符惩罚
    garbage_chars = sum(1 for c in text if not c.isalnum() and not c.isspace() and c not in '.-+()[]{}:/@,')
    garbage_ratio = garbage_chars / total_chars if total_chars > 0 else 0
    score -= garbage_ratio * 0.5
    
    # 4. 建筑术语加分
    building_terms = [
        'foundation', 'plan', 'scale', 'wall', 'column', 'beam', 
        'kitchen', 'bedroom', 'bathroom', 'garage', 'storage',
        'concrete', 'steel', 'grade', 'dimension', 'depth',
        'living', 'room', 'type', 'mm', 'notes'
    ]
    
    text_lower = text.lower()
    found_terms = sum(1 for term in building_terms if term in text_lower)
    score += found_terms * 0.05  # 每个术语加5%
    
    # 5. 数字模式加分（尺寸标注等）
    import re
    number_patterns = re.findall(r'\d+', text)
    if len(number_patterns) > 0:
        score += 0.1
    
    # 尺寸格式加分（如 "200x300", "4500"）
    dimension_patterns = re.findall(r'\d+x\d+', text.lower())
    score += len(dimension_patterns) * 0.05
    
    return min(1.0, max(0.0, score))  # 限制在0-1之间

def _calculate_keyword_score(text):
    """计算关键词识别分数"""
    if not text:
        return 0.0
    
    # 建筑图纸关键词
    building_keywords = [
        'foundation', 'plan', 'scale', 'wall', 'column', 'beam', 
        'kitchen', 'bedroom', 'bathroom', 'garage', 'storage',
        'concrete', 'steel', 'grade', 'dimension', 'depth',
        'living', 'room', 'type', 'mm', 'notes', 'section',
        'elevation', 'detail', 'reinforcement'
    ]
    
    text_lower = text.lower()
    found_keywords = sum(1 for keyword in building_keywords if keyword in text_lower)
    
    # 归一化分数 (0-1)
    max_possible = len(building_keywords)
    return min(1.0, found_keywords / max_possible * 3)  # 乘以3是为了让分数更有区分度

def _select_best_result_final(valid_results):
    """最终版本的结果选择 - 平衡质量和关键词识别"""
    if len(valid_results) == 1:
        return valid_results[0]
    
    best_score = 0
    best_result = valid_results[0]
    
    for method_name, text, length, quality, keyword_score in valid_results:
        # 综合得分：关键词权重最高，质量次之，长度最低
        composite_score = (keyword_score * 0.5 +     # 关键词50%
                          quality * 0.3 +            # 质量30%
                          min(length / 500, 1.0) * 0.2)  # 长度20%，但有上限
        
        print(f"    {method_name} 综合得分: {composite_score:.2f} (关键词:{keyword_score:.1f}, 质量:{quality:.1f}, 长度:{length})")
        
        if composite_score > best_score:
            best_score = composite_score
            best_result = (method_name, text, length, quality, keyword_score)
    
    return best_result

def _smart_merge_results(valid_results, primary_text):
    """智能合并结果，确保关键信息不丢失"""
    if not valid_results:
        return primary_text
    
    # 按关键词分数排序，找到关键词识别最好的结果
    sorted_by_keywords = sorted(valid_results, key=lambda x: x[4], reverse=True)
    best_keyword_text = sorted_by_keywords[0][1]
    
    # 按质量排序，找到质量最好的结果
    sorted_by_quality = sorted(valid_results, key=lambda x: x[3], reverse=True)
    best_quality_text = sorted_by_quality[0][1]
    
    # 如果主要结果的关键词分数不是最高的，考虑替换或补充
    primary_keyword_score = _calculate_keyword_score(primary_text)
    best_keyword_score = _calculate_keyword_score(best_keyword_text)
    
    if best_keyword_score > primary_keyword_score * 1.2:  # 如果最佳关键词结果明显更好
        print(f"[智能合并] 使用关键词最佳结果 (分数: {best_keyword_score:.1f} vs {primary_keyword_score:.1f})")
        return best_keyword_text
    
    # 否则使用主要结果，但补充缺失的关键信息
    import re
    
    # 提取所有结果中的数字和尺寸
    all_numbers = set()
    all_dimensions = set()
    
    for _, text, _, _, _ in valid_results:
        numbers = re.findall(r'\b\d+\b', text)
        dimensions = re.findall(r'\b\d+x\d+(?:x\d+)?\b', text.lower())
        all_numbers.update(numbers)
        all_dimensions.update(dimensions)
    
    # 检查主要结果中缺失的重要信息
    primary_numbers = set(re.findall(r'\b\d+\b', primary_text))
    primary_dimensions = set(re.findall(r'\b\d+x\d+(?:x\d+)?\b', primary_text.lower()))
    
    missing_numbers = all_numbers - primary_numbers
    missing_dimensions = all_dimensions - primary_dimensions
    
    # 构建补充信息（只补充最重要的）
    supplement = ""
    if missing_numbers:
        # 只补充看起来像尺寸的数字（通常是建筑中的重要数字）
        important_numbers = [n for n in missing_numbers if len(n) >= 3 and int(n) >= 100]
        if important_numbers:
            supplement += f"\n[补充尺寸数字]: {' '.join(sorted(important_numbers)[:3])}"
    
    if missing_dimensions:
        supplement += f"\n[补充尺寸格式]: {' '.join(sorted(missing_dimensions)[:2])}"
    
    return primary_text + supplement

def _method_standard_preprocessing(image):
    """方法1: 标准预处理"""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 适度增强对比度
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # 去噪
        denoised = cv2.medianBlur(enhanced, 3)
        
        # 二值化
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 使用最佳PSM模式组合
        best_result = ""
        best_psm_modes = [11, 12, 6, 3]  # 基于测试结果排序
        
        for psm in best_psm_modes:
            try:
                config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
                result = pytesseract.image_to_string(binary, lang='chi_sim+eng', config=config)
                if len(result.strip()) > len(best_result.strip()):
                    best_result = result
            except:
                continue
        
        return best_result.strip()
        
    except Exception as e:
        print(f"[标准预处理] 失败: {e}")
        return ""

def _method_enhanced_preprocessing(image):
    """方法2: 增强预处理（放大、锐化）"""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 放大图像提高精度
        scale_factor = 2.5
        height, width = gray.shape
        enlarged = cv2.resize(gray, (int(width * scale_factor), int(height * scale_factor)), 
                            interpolation=cv2.INTER_CUBIC)
        
        # 增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(enlarged)
        
        # 去噪，保留边缘
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # 锐化
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        # 自适应二值化
        binary = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 15, 10)
        
        # OCR识别
        config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        result = pytesseract.image_to_string(binary, lang='chi_sim+eng', config=config)
        
        return result.strip()
        
    except Exception as e:
        print(f"[增强预处理] 失败: {e}")
        return ""

def _method_segmented_processing(image):
    """方法3: 分割区域处理"""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 预处理
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 分割图像
        height, width = binary.shape
        all_text = []
        
        # 使用滑动窗口而不是固定网格
        window_size = min(height, width) // 3
        step = window_size // 2
        
        for y in range(0, height - window_size, step):
            for x in range(0, width - window_size, step):
                segment = binary[y:y+window_size, x:x+window_size]
                
                # 检查区域是否有足够的文字内容
                if np.sum(segment == 0) > window_size * window_size * 0.01:  # 至少1%是黑色像素
                    try:
                        config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
                        seg_text = pytesseract.image_to_string(segment, lang='chi_sim+eng', config=config)
                        
                        if seg_text.strip() and len(seg_text.strip()) > 2:
                            all_text.append(seg_text.strip())
                    except:
                        continue
        
        # 去重并合并
        unique_texts = list(set(all_text))
        return " ".join(unique_texts)
        
    except Exception as e:
        print(f"[分割处理] 失败: {e}")
        return ""

def _post_process_text(text):
    """后处理文本"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:  # 只保留非空行
            # 修正常见OCR错误
            line = line.replace('O', '0').replace('l', '1').replace('I', '1')  # 数字修正
            line = re.sub(r'\s+', ' ', line)  # 多个空格合并为一个
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def detect_components(image_path: str):
    """
    使用YOLO模型检测构件
    """
    try:
        local_path = _ensure_local_file(image_path)
        model = load_yolo_model()
        
        if model is None:
            return {"error": "YOLO模型未能加载"}
            
        results = model(local_path)
        
        # 清理临时文件
        if local_path != image_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as e:
                print(f"警告: 删除临时文件失败: {str(e)}")
                
        return results[0].boxes.data.cpu().numpy()
        
    except Exception as e:
        return {"error": f"构件检测失败: {str(e)}"}

def dwg_file_to_pdf(dwg_path: str, output_pdf: str) -> bool:
    """
    DWG文件转PDF，按多图框顺序分页输出
    Args:
        dwg_path: DWG文件路径
        output_pdf: 输出PDF文件路径
    Returns:
        是否成功
    """
    try:
        # 创建输出目录
        output_dir = os.path.dirname(output_pdf)
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化DWG处理器
        processor = DWGProcessor()
        
        # 处理DWG文件并生成PDF
        pdf_files = processor.process_dwg_to_pdf(dwg_path, output_dir)
        
        if not pdf_files:
            logger.error("未生成任何PDF文件")
            return False
            
        # 如果只有一个PDF文件，直接重命名
        if len(pdf_files) == 1:
            os.rename(pdf_files[0], output_pdf)
            return True
            
        # 如果有多个PDF文件，合并为一个
        try:
            from PyPDF2 import PdfMerger
            merger = PdfMerger()
            
            for pdf_file in pdf_files:
                merger.append(pdf_file)
                
            merger.write(output_pdf)
            merger.close()
            
            # 清理临时文件
            for pdf_file in pdf_files:
                try:
                    os.remove(pdf_file)
                except:
                    pass
                    
            return True
            
        except ImportError:
            logger.error("PyPDF2库未安装，无法合并PDF文件")
            return False
            
    except Exception as e:
        logger.error(f"DWG转PDF失败: {e}")
        return False 