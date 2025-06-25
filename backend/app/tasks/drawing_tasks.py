#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸处理相关的 Celery 任务 - 按新的数据流程重构
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
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.database import get_celery_db_session
from app.models.drawing import Drawing
from app.models.user import User
from app.core.celery_app import celery_app
from app.services.s3_service import S3Service
from app.services.file_processor import FileProcessor
from app.services.unified_quantity_engine import UnifiedQuantityEngine
from app.services.result_merger_service import ResultMergerService
# from app.services.simplified_ocr_processor import SimplifiedOCRProcessor
from app.services.ocr.paddle_ocr import PaddleOCRService
from app.tasks.real_time_task_manager import RealTimeTaskManager, TaskStatus, TaskStage
from ..services.s3_service import s3_service
from ..services.file_processor import FileProcessor
from ..services.vision_scanner import VisionScannerService
from ..database import SessionLocal
from .task_status_pusher import track_progress
from . import task_manager  # 直接从 tasks 包导入唯一的实例

logger = logging.getLogger(__name__)

async def process_images_with_shared_slices(image_paths: List[str], 
                                          shared_slice_results: Dict[str, Any],
                                          drawing_id: int, 
                                          task_id: str) -> Dict[str, Any]:
    """
    使用共享智能切片结果处理图像OCR
    
    Args:
        image_paths: 原始图像路径列表
        shared_slice_results: 统一智能切片的结果
        drawing_id: 图纸ID
        task_id: 任务ID
        
    Returns:
        OCR处理结果
    """
    logger.info(f"🔍 开始基于共享切片的PaddleOCR处理: {len(image_paths)} 张图片")
    
    all_results = []
    total_text_regions = 0
    successful_images = 0
    total_slices_processed = 0
    
    for i, image_path in enumerate(image_paths):
        try:
            logger.info(f"处理图像 {i+1}/{len(image_paths)}: {Path(image_path).name}")
            
            slice_info = shared_slice_results.get(image_path, {})
            
            if slice_info.get('sliced', False):
                # 使用切片结果进行OCR
                slice_infos = slice_info.get('slice_infos', [])
                logger.info(f"  🔪 使用共享切片结果: {len(slice_infos)} 个切片")
                
                # 对每个切片执行OCR
                slice_ocr_results = []
                for j, slice_data in enumerate(slice_infos):
                    try:
                        # 将base64数据转换为临时图片文件
                        import base64
                        import tempfile
                        
                        slice_image_data = base64.b64decode(slice_data.base64_data)
                        temp_slice_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                        temp_slice_file.write(slice_image_data)
                        temp_slice_file.close()
                        
                        # 使用基础OCR服务处理单个切片
                        from app.services.ocr.paddle_ocr import PaddleOCRService
                        basic_ocr = PaddleOCRService()
                        # 为切片生成唯一标识，便于存储管理
                        slice_identifier = f"{drawing_id}_{task_id}_slice_{j}"
                        slice_result = basic_ocr.recognize_text(temp_slice_file.name, save_to_sealos=True, drawing_id=str(drawing_id))
                        
                        if slice_result.get('success', True):  # PaddleOCR通常没有explicit success字段
                            # 调整坐标到原图坐标系
                            adjusted_regions = []
                            for region in slice_result.get('text_regions', []):
                                adjusted_region = region.copy()
                                if 'bbox' in adjusted_region:
                                    bbox = adjusted_region['bbox']
                                    # 调整坐标: 加上切片在原图中的偏移
                                    adjusted_bbox = [
                                        bbox[0] + slice_data.x,
                                        bbox[1] + slice_data.y,
                                        bbox[2] + slice_data.x,
                                        bbox[3] + slice_data.y
                                    ]
                                    adjusted_region['bbox'] = adjusted_bbox
                                adjusted_regions.append(adjusted_region)
                            
                            slice_ocr_results.append({
                                'slice_id': slice_data.slice_id,
                                'text_regions': adjusted_regions,
                                'slice_text': slice_result.get('all_text', ''),
                                'slice_index': j
                            })
                            total_slices_processed += 1
                            logger.info(f"    ✅ 切片 {j+1}/{len(slice_infos)} OCR完成: {len(adjusted_regions)} 个文本区域")
                        else:
                            logger.warning(f"    ❌ 切片 {j+1} OCR失败")
                        
                        # 清理临时文件
                        os.unlink(temp_slice_file.name)
                        
                    except Exception as slice_ocr_error:
                        logger.error(f"    ❌ 切片 {j+1} OCR异常: {slice_ocr_error}")
                
                # 合并所有切片的OCR结果
                if slice_ocr_results:
                    merged_text_regions = []
                    merged_text = []
                    
                    for slice_result in slice_ocr_results:
                        merged_text_regions.extend(slice_result['text_regions'])
                        if slice_result['slice_text']:
                            merged_text.append(slice_result['slice_text'])
                    
                    # 去重处理（简单的基于位置的去重）
                    deduplicated_regions = remove_duplicate_regions(merged_text_regions)
                    
                    result = {
                        'success': True,
                        'texts': [{'text': region.get('text', ''), 'bbox': region.get('bbox', [])} for region in deduplicated_regions],
                        'text_regions': deduplicated_regions,
                        'all_text': '\n'.join(merged_text),
                        'statistics': {
                            'total_regions': len(deduplicated_regions),
                            'total_slices': len(slice_infos),
                            'processed_slices': len(slice_ocr_results),
                            'avg_confidence': calculate_average_confidence(deduplicated_regions)
                        },
                        'processing_method': 'shared_slice_ocr'
                    }
                    
                    all_results.append(result)
                    total_text_regions += len(deduplicated_regions)
                    successful_images += 1
                    
                    logger.info(f"  ✅ 共享切片OCR成功: {len(slice_ocr_results)} 个切片处理完成, {len(deduplicated_regions)} 个文本区域")
                else:
                    logger.warning(f"  ❌ 所有切片OCR都失败")
            else:
                # 已移除降级处理
                logger.info(f"  📄 使用原图OCR处理: {slice_info.get('reason', 'unknown')}")
                
                from app.services.ocr.paddle_ocr import PaddleOCRService
                basic_ocr = PaddleOCRService()
                result = basic_ocr.recognize_text(image_path, save_to_sealos=True, drawing_id=str(drawing_id))
                
                if result.get('text_regions'):  # PaddleOCR成功的判断
                    result['processing_method'] = 'direct_ocr_error'
                    result['success'] = True
                    all_results.append(result)
                    total_text_regions += len(result.get('text_regions', []))
                    successful_images += 1
                    logger.info(f"  ✅ 原图OCR成功: {len(result.get('text_regions', []))} 个文本区域")
                else:
                    logger.warning(f"  ❌ 原图OCR失败")
                    
        except Exception as e:
            logger.error(f"  ❌ 处理图像异常: {e}")
    
    # 汇总结果
    if successful_images > 0:
        # 合并所有文本区域
        all_text_regions = []
        all_text = []
        
        for result in all_results:
            all_text_regions.extend(result.get('text_regions', []))
            if result.get('all_text'):
                all_text.append(result['all_text'])
        
        # 收集存储信息
        storage_summaries = []
        for result in all_results:
            if result.get('storage_info', {}).get('saved'):
                storage_summaries.append(result['storage_info'])
        
        # 构建最终结果
        final_result = {
            'success': True,
            'total_images_processed': len(image_paths),
            'successful_images': successful_images,
            'failed_images': len(image_paths) - successful_images,
            'text_regions': all_text_regions,
            'all_text': '\n'.join(all_text),
            'statistics': {
                'total_regions': total_text_regions,
                'total_slices_processed': total_slices_processed,
                'avg_confidence': calculate_average_confidence(all_text_regions),
                'processing_time': sum(r.get('statistics', {}).get('processing_time', 0) for r in all_results)
            },
            'storage_summary': {
                'total_saved_files': len(storage_summaries),
                'storage_details': storage_summaries
            },
            'processing_summary': {
                'shared_slice_used': True,
                'slicing_enabled': True,
                'individual_results': [
                    {
                        'image': Path(image_paths[i]).name,
                        'success': i < len(all_results),
                        'method': all_results[i].get('processing_method') if i < len(all_results) else 'failed',
                        'regions': all_results[i].get('statistics', {}).get('total_regions', 0) if i < len(all_results) else 0
                    }
                    for i in range(len(image_paths))
                ]
            }
        }
        
        # 为了兼容现有代码，生成一个主要的result_s3_key（如果有存储结果的话）
        primary_s3_key = None
        if storage_summaries:
            # 选择第一个JSON结果作为主要的S3 key
            for storage_info in storage_summaries:
                if storage_info.get('json_result', {}).get('s3_key'):
                    primary_s3_key = storage_info['json_result']['s3_key']
                    break
        
        if primary_s3_key:
            final_result['result_s3_key'] = primary_s3_key
            logger.info(f"📁 OCR结果主要存储位置: {primary_s3_key}")
        
        # 🔧 新增：保存合并后的PaddleOCR结果
        if successful_images > 0:
            merged_ocr_storage = _save_merged_paddleocr_result(
                final_result, 
                drawing_id, 
                task_id
            )
            if merged_ocr_storage.get('success'):
                final_result['merged_ocr_storage'] = merged_ocr_storage
                logger.info(f"💾 合并OCR结果已保存: {merged_ocr_storage.get('s3_key', 'N/A')}")
        
        logger.info(f"✅ 共享切片OCR处理完成: {successful_images}/{len(image_paths)} 成功, "
                   f"总计 {total_text_regions} 个文本区域, {total_slices_processed} 个切片处理")
        
        return final_result
    else:
        return {
            'success': False,
            'error': '所有图像处理都失败',
            'total_images_processed': len(image_paths),
            'successful_images': 0,
            'failed_images': len(image_paths)
        }

def remove_duplicate_regions(text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """简单的文本区域去重"""
    if not text_regions:
        return []
    
    deduplicated = []
    for region in text_regions:
        bbox = region.get('bbox', [])
        text = region.get('text', '')
        
        # 检查是否与已有区域重复
        is_duplicate = False
        for existing in deduplicated:
            existing_bbox = existing.get('bbox', [])
            existing_text = existing.get('text', '')
            
            # 简单的重复判断：文本相同且位置接近
            if text == existing_text and bbox and existing_bbox:
                if (abs(bbox[0] - existing_bbox[0]) < 10 and 
                    abs(bbox[1] - existing_bbox[1]) < 10):
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            deduplicated.append(region)
    
    return deduplicated

def calculate_average_confidence(text_regions: List[Dict[str, Any]]) -> float:
    """计算平均置信度"""
    if not text_regions:
        return 0.0
    
    confidences = [region.get('confidence', 0.0) for region in text_regions if 'confidence' in region]
    return sum(confidences) / len(confidences) if confidences else 0.0

def _save_merged_paddleocr_result(final_result: Dict[str, Any], 
                                drawing_id: int, 
                                task_id: str) -> Dict[str, Any]:
    """
    保存合并后的PaddleOCR结果到存储服务。
    文件名是固定的，但基于task_id是唯一的。
    【最终修复】精确匹配下游服务期望的JSON结构。
    """
    from app.services.dual_storage_service import DualStorageService
    storage_service = DualStorageService()

    try:
        # 从final_result中提取所有文本区域
        all_regions = final_result.get("text_regions", [])
        
        # 【最终修复】构建与 ocr_result_corrector.py 中
        # _preprocess_ocr_text_simple 函数期望完全一致的结构
        merged_data = {
            "task_id": task_id,
            "drawing_id": drawing_id,
            "merged_result": {
                "all_text_regions": all_regions,
                "statistics": final_result.get("statistics", {}),
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        
        # 使用基于 task_id 的固定文件名
        s3_key = f"ocr_results/{drawing_id}/merged_ocr_result_{task_id}.json"
        
        # 上传合并结果
        result_upload = storage_service.upload_content_sync(
            content=json.dumps(merged_data, ensure_ascii=False, indent=2),
            s3_key=s3_key,
            content_type="application/json"
        )
        
        if result_upload.get("success"):
            logger.info(f"✅ 合并OCR结果已保存到存储: {s3_key}")
            return {
                "success": True,
                "s3_key": s3_key,
                "message": "合并OCR结果保存成功"
            }
        
        logger.error(f"❌ 保存合并OCR结果失败: {result_upload.get('error')}")
        return {"success": False, "error": result_upload.get('error')}

    except Exception as e:
        logger.error(f"保存合并OCR结果时发生异常: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def process_images_with_enhanced_ocr(image_paths: List[str], drawing_id: int, task_id: str) -> Dict[str, Any]:
    """
    使用增强版PaddleOCR服务处理图像列表（支持智能切片）
    
    Args:
        image_paths: 图像文件路径列表
        drawing_id: 图纸ID
        task_id: 任务ID
        
    Returns:
        OCR处理结果
    """
    logger.info(f"开始处理 {len(image_paths)} 个图像文件，支持智能切片")
    
    all_results = []
    total_text_regions = 0
    successful_images = 0
    
    for i, image_path in enumerate(image_paths):
        try:
            logger.info(f"处理图像 {i+1}/{len(image_paths)}: {Path(image_path).name}")
            
            # 使用增强版PaddleOCR服务（自动判断是否使用切片）
            result = await paddle_ocr_service.process_image_async(
                image_path=image_path,
                use_slicing=None  # 自动判断
            )
            
            if result.get('success'):
                all_results.append(result)
                total_text_regions += result.get('statistics', {}).get('total_regions', 0)
                successful_images += 1
                
                processing_method = result.get('processing_method', 'unknown')
                regions_count = result.get('statistics', {}).get('total_regions', 0)
                logger.info(f"  ✅ 处理成功: {processing_method}, {regions_count} 个文本区域")
                
                # 如果使用了切片，记录切片信息
                if 'slicing_info' in result:
                    slicing_info = result['slicing_info']
                    logger.info(f"  🔪 切片信息: {slicing_info.get('total_slices', 0)} 个切片, "
                              f"成功率 {slicing_info.get('success_rate', 0):.1%}")
            else:
                logger.warning(f"  ❌ 处理失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"  ❌ 处理图像异常: {e}")
    
    # 汇总结果
    if successful_images > 0:
        # 合并所有文本区域
        all_text_regions = []
        all_text = []
        
        for result in all_results:
            all_text_regions.extend(result.get('text_regions', []))
            if result.get('all_text'):
                all_text.append(result['all_text'])
        
        # 构建最终结果
        final_result = {
            'success': True,
            'total_images_processed': len(image_paths),
            'successful_images': successful_images,
            'failed_images': len(image_paths) - successful_images,
            'text_regions': all_text_regions,
            'all_text': '\n'.join(all_text),
            'statistics': {
                'total_regions': total_text_regions,
                'avg_confidence': sum(r.get('statistics', {}).get('avg_confidence', 0) for r in all_results) / len(all_results) if all_results else 0,
                'processing_time': sum(r.get('statistics', {}).get('processing_time', 0) for r in all_results)
            },
            'processing_summary': {
                'enhanced_ocr_used': True,
                'slicing_enabled': True,
                'individual_results': [
                    {
                        'image': Path(image_paths[i]).name,
                        'success': i < len(all_results),
                        'method': all_results[i].get('processing_method') if i < len(all_results) else 'failed',
                        'regions': all_results[i].get('statistics', {}).get('total_regions', 0) if i < len(all_results) else 0
                    }
                    for i in range(len(image_paths))
                ]
            }
        }
        
        logger.info(f"✅ 增强版OCR处理完成: {successful_images}/{len(image_paths)} 成功, "
                   f"总计 {total_text_regions} 个文本区域")
        
        return final_result
    else:
        return {
            'success': False,
            'error': '所有图像处理都失败',
            'total_images_processed': len(image_paths),
            'successful_images': 0,
            'failed_images': len(image_paths)
        }

# 初始化服务
s3_service = S3Service()
file_processor = FileProcessor()
quantity_engine = UnifiedQuantityEngine()
# simplified_ocr_processor = SimplifiedOCRProcessor()
# 使用支持智能切片的PaddleOCR服务
from app.services.ocr.paddle_ocr_with_slicing import PaddleOCRWithSlicing
paddle_ocr_service = PaddleOCRWithSlicing()

class CallbackTask(Task):
    """带回调的 Celery 任务基类"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功完成时的回调"""
        logger.info(f"✅ Celery 任务成功完成: {task_id}")
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"❌ Celery 任务失败: {task_id}, 错误: {str(exc)}")

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
            # 创建临时文件但立即关闭句柄，避免Windows文件锁定问题
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{drawing.file_type}")
            local_file_path = temp_file.name
            temp_file.close()  # 立即关闭文件句柄，避免Windows锁定
            
            # 使用双重存储服务下载文件
            from app.services.dual_storage_service import DualStorageService
            dual_storage_service = DualStorageService()
            
            download_success = dual_storage_service.download_file(
                s3_key=drawing.s3_key,
                local_path=local_file_path
            )
            
            if not download_success:
                # 如果双重存储下载失败，尝试使用原始文件路径（本地备份）
                logger.warning(f"⚠️ 双重存储下载失败，尝试使用本地备份: {drawing.file_path}")
                if drawing.file_path and os.path.exists(drawing.file_path):
                    try:
                        import shutil
                        shutil.copy2(drawing.file_path, local_file_path)
                        logger.info(f"✅ 使用本地备份文件成功: {drawing.file_path}")
                        download_success = True
                    except Exception as backup_error:
                        logger.error(f"❌ 本地备份文件也无法使用: {backup_error}")
                
                if not download_success:
                    raise Exception(f"文件下载失败: {drawing.s3_key} (包括本地备份)")
            
            # 验证下载的文件
            if not os.path.exists(local_file_path):
                raise Exception(f"下载文件不存在: {local_file_path}")
            
            file_size = os.path.getsize(local_file_path)
            if file_size == 0:
                raise Exception(f"下载的文件为空: {drawing.s3_key}")
            
            logger.info(f"📁 文件下载完成: {local_file_path} (大小: {file_size} 字节)")
            
            # 检查并修复file_type字段
            from app.utils.file_utils import extract_file_type
            if not drawing.file_type:
                # 如果file_type为空，从文件名推断
                file_ext = os.path.splitext(drawing.filename)[1].lower()
                drawing.file_type = extract_file_type(drawing.filename)
                    
                # 更新数据库
                db.commit()
                logger.info(f"🔧 自动修复file_type: {file_ext} -> {drawing.file_type}")
            
            # 如果是PDF文件，额外验证文件头
            if drawing.file_type and drawing.file_type.lower() == 'pdf':
                try:
                    with open(local_file_path, 'rb') as f:
                        header = f.read(8)
                        if not header.startswith(b'%PDF'):
                            raise Exception(f"下载的PDF文件格式无效: 文件头 {header}")
                    logger.info("✅ PDF文件头验证通过")
                except Exception as header_error:
                    raise Exception(f"PDF文件验证失败: {header_error}")
            
            # 阶段3: 文件预处理
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.FILE_PROCESSING,
                    progress=20, message="Celery Worker 正在预处理文件..."
                )
            )
            
            # 3️⃣ 统一文件预处理（转换为图片）
            logger.info(f"🔄 开始统一文件预处理: {drawing.file_type}")
            file_processing_result = file_processor.process_file(local_file_path, drawing.file_type)
            
            if file_processing_result.get('status') != 'success':
                raise Exception(f"文件预处理失败: {file_processing_result.get('error')}")
            
            # 记录临时文件以便清理
            temp_files = file_processing_result.get('image_paths', [])
            source_type = file_processing_result.get('processing_method', 'unknown')
            
            logger.info(f"✅ 文件预处理完成: {len(temp_files)} 个图片文件 (来源: {source_type})")
            
            # ========= 新增：统一智能切片阶段 =========
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.FILE_PROCESSING,
                    progress=25, message="Celery Worker 正在进行统一智能切片..."
                )
            )
            
            # 3️⃣ 统一智能切片预处理
            logger.info("🔪 开始统一智能切片预处理...")
            shared_slice_results = {}
            original_images = {}
            
            try:
                from app.services.intelligent_image_slicer import IntelligentImageSlicer
                unified_slicer = IntelligentImageSlicer()
                
                for image_path in temp_files:
                    try:
                        logger.info(f"🔍 分析图片切片需求: {Path(image_path).name}")
                        
                        # 检查图片尺寸和文件大小
                        file_size = os.path.getsize(image_path)
                        
                        from PIL import Image
                        with Image.open(image_path) as img:
                            width, height = img.size
                            logger.info(f"📏 图片尺寸: {width}x{height}, 文件大小: {file_size / 1024 / 1024:.2f} MB")
                            
                            # 统一切片判断条件：尺寸>2048x2048 或 文件大小>1.5MB
                            max_dimension = 2048
                            max_file_size = int(1.5 * 1024 * 1024)  # 1.5MB
                            
                            needs_slicing = (width > max_dimension or height > max_dimension or file_size > max_file_size)
                            
                            if needs_slicing:
                                slice_reason = []
                                if width > max_dimension or height > max_dimension:
                                    slice_reason.append(f"尺寸{width}x{height}超过{max_dimension}x{max_dimension}")
                                if file_size > max_file_size:
                                    slice_reason.append(f"文件大小{file_size / 1024 / 1024:.1f}MB超过1.5MB")
                                
                                logger.info(f"🔪 执行智能切片: {', '.join(slice_reason)}")
                                
                                # 执行智能切片
                                task_slice_id = f"unified_{task_id}_{Path(image_path).stem}"
                                slice_infos = unified_slicer.slice_image(img, task_slice_id)
                                
                                if slice_infos and len(slice_infos) > 0:
                                    shared_slice_results[image_path] = {
                                        'sliced': True,
                                        'slice_count': len(slice_infos),
                                        'slice_infos': slice_infos,
                                        'original_size': (width, height),
                                        'slice_reason': slice_reason
                                    }
                                    logger.info(f"✅ 智能切片完成: {len(slice_infos)} 个切片")
                                else:
                                    logger.warning("⚠️ 智能切片返回空结果，使用原图")
                                    shared_slice_results[image_path] = {
                                        'sliced': False,
                                        'reason': 'slice_failed',
                                        'error_to_original': True
                                    }
                            else:
                                logger.info(f"✅ 图片尺寸适中，无需切片")
                                shared_slice_results[image_path] = {
                                    'sliced': False,
                                    'reason': 'size_appropriate',
                                    'original_size': (width, height)
                                }
                            
                            # 保存原图引用
                            original_images[image_path] = {
                                'path': image_path,
                                'size': (width, height),
                                'file_size': file_size
                            }
                    
                    except Exception as slice_error:
                        logger.error(f"❌ 图片切片失败 {image_path}: {slice_error}")
                        shared_slice_results[image_path] = {
                            'sliced': False,
                            'reason': 'slice_error',
                            'error': str(slice_error),
                            'error_to_original': True
                        }
                
                # 统计切片结果
                total_images = len(temp_files)
                sliced_images = sum(1 for result in shared_slice_results.values() if result.get('sliced', False))
                total_slices = sum(result.get('slice_count', 0) for result in shared_slice_results.values())
                
                logger.info(f"🎯 统一智能切片完成: {sliced_images}/{total_images} 张图片被切片, 总计 {total_slices} 个切片")
                
            except Exception as unified_slice_error:
                logger.error(f"❌ 统一智能切片失败: {unified_slice_error}")
                # 已移除降级处理
                shared_slice_results = {}
                for image_path in temp_files:
                    shared_slice_results[image_path] = {
                        'sliced': False,
                        'reason': 'unified_slice_failed',
                        'error': str(unified_slice_error),
                        'error_to_original': True
                    }
            
            # 【修复】提取原始图片信息，以供后续步骤使用
            original_image_info = {}
            if original_images:
                # 假设我们只处理单个图纸转换后的第一张图片
                first_image_path = next(iter(original_images))
                original_image_info = original_images[first_image_path]
                logger.info(f"提取到原始图片信息: {original_image_info.get('size')}")

            ocr_result = {}
            vision_scan_result = {}
            
            # ========= 轨道 1: PaddleOCR 分析（使用共享切片结果）=========
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.OCR_PROCESSING,
                    progress=40, message="Celery Worker 正在进行PaddleOCR扫描（使用共享切片）..."
                )
            )
            
            ocr_success = False
            try:
                logger.info("轨道 1: 🔍 开始 PaddleOCR 分析（使用共享智能切片结果）...")
                # 使用共享切片结果的增强版PaddleOCR服务
                ocr_result = loop.run_until_complete(
                    process_images_with_shared_slices(temp_files, shared_slice_results, drawing.id, task_id)
                )
                
                if ocr_result.get("success"):
                    logger.info("轨道 1: ✅ PaddleOCR 分析成功。")
                    drawing.ocr_result_s3_key = ocr_result.get("result_s3_key")
                    ocr_success = True
                else:
                    logger.warning(f"轨道 1: ⚠️ PaddleOCR 分析失败: {ocr_result.get('error', '未知错误')}")
                    drawing.error_message = f"OCR failed: {ocr_result.get('error')}"
            except Exception as ocr_exc:
                logger.error(f"轨道 1: ❌ PaddleOCR 分析过程中发生严重异常: {ocr_exc}", exc_info=True)
                drawing.error_message = f"OCR exception: {ocr_exc}"
                # 如果OCR失败，提供一个空的默认结构以避免后续步骤崩溃
                ocr_result = {
                    "success": False, 
                    "error": "OCR track failed completely.",
                    "storage_summary": {}
                }

            # 如果OCR失败，提供一个空的默认结构以避免后续步骤崩溃
            if not ocr_result:
                logger.warning("⚠️ OCR轨道处理结果为None，将使用空结果继续执行，Vision轨道将独立分析。")
                ocr_result = {
                    "success": False, 
                    "error": "OCR track failed completely.",
                    "storage_summary": {}
                }

            # 【最终修复】直接使用OCR轨道的结果，绕过有问题的中间合并步骤
            logger.info(f"✅ OCR轨道完成，成功={ocr_success}。将直接使用此结果进行后续步骤。")
            
            # ========= Vision轨道将依赖这个 ocr_result =========
            # (这个变量名保持不变，因为它将被传递给vision_scanner)
            enhanced_ocr_result = dict(ocr_result) 
            
            # ========= 移除有问题的OCR结果合并阶段 =========
            logger.info("⏩ 跳过已知的、有问题的'OCR结果合并阶段'。")
            ocr_full_result = None # 确保这个变量为空，以免干扰后续逻辑

            # ========= 新增：OCR结果智能纠正阶段 =========
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.OCR_PROCESSING,
                    progress=55, message="Celery Worker 正在进行OCR结果智能纠正..."
                )
            )
            
            logger.info("🧠 开始OCR结果智能纠正阶段...")
            ocr_correction_success = False
            corrected_ocr_result = None
            
            try:
                # 🔧 【最终修复】直接从 ocr_result 中查找S3 Key
                merged_ocr_key = None
                
                logger.info(f"🔍 在 ocr_result 中搜索合并OCR结果存储键...")
                if ocr_success and isinstance(ocr_result, dict):
                    # 路径: ocr_result.merged_ocr_storage.s3_key
                    if 'merged_ocr_storage' in ocr_result and isinstance(ocr_result['merged_ocr_storage'], dict):
                        merged_ocr_key = ocr_result['merged_ocr_storage'].get('s3_key')
                        if merged_ocr_key:
                            logger.info(f"✅ 从 ocr_result.merged_ocr_storage 中找到存储键: {merged_ocr_key}")

                if merged_ocr_key:
                    logger.info(f"🎯 确认使用OCR存储键: {merged_ocr_key}")
                    
                    # 初始化OCR纠正服务
                    from app.services.ocr_result_corrector import OCRResultCorrector
                    from app.services.ai_analyzer import AIAnalyzerService
                    from app.services.dual_storage_service import DualStorageService
                    
                    ai_analyzer = AIAnalyzerService()
                    storage_service = DualStorageService()
                    
                    # 确保storage_service已正确初始化
                    if not storage_service:
                        raise Exception("存储服务未初始化，无法进行OCR智能纠正")
                    
                    ocr_corrector = OCRResultCorrector(ai_analyzer=ai_analyzer, storage_service=storage_service)
                    
                    # 执行OCR纠正
                    corrected_ocr_result = loop.run_until_complete(
                        ocr_corrector.correct_ocr_result(
                            merged_ocr_key=merged_ocr_key,
                            drawing_id=drawing.id,
                            task_id=task_id,
                            original_image_info={
                                'width': original_image_info.get('size', (0,0))[0],
                                'height': original_image_info.get('size', (0,0))[1],
                                'filename': drawing.filename
                            }
                        )
                    )
                    
                    if corrected_ocr_result:
                        # 保存纠正结果到数据库
                        drawing.ocr_merged_result_key = merged_ocr_key
                        drawing.ocr_corrected_result_key = corrected_ocr_result.corrected_result_key
                        drawing.ocr_correction_summary = {
                            "processing_time": corrected_ocr_result.processing_metadata.get("processing_time"),
                            "correction_method": corrected_ocr_result.processing_metadata.get("correction_method"),
                            "components_extracted": len(corrected_ocr_result.component_list),
                            "notes_extracted": len(corrected_ocr_result.global_notes),
                            "drawing_info_extracted": bool(corrected_ocr_result.drawing_basic_info),
                            "timestamp": corrected_ocr_result.timestamp
                        }
                        
                        ocr_correction_success = True
                        logger.info(f"✅ OCR结果智能纠正完成: 提取了 {len(corrected_ocr_result.component_list)} 个构件和 {len(corrected_ocr_result.global_notes)} 条说明")
                        
                        # 更新OCR结果，提供纠正后的数据给Vision分析使用
                        ocr_result['corrected_data'] = {
                            "drawing_basic_info": corrected_ocr_result.drawing_basic_info,
                            "component_list": corrected_ocr_result.component_list,
                            "global_notes": corrected_ocr_result.global_notes,
                            "corrected_text_regions": corrected_ocr_result.text_regions_corrected,
                            "correction_summary": corrected_ocr_result.correction_summary
                        }
                    else:
                        logger.warning("⚠️ OCR纠正结果为空，继续使用原始OCR结果")
                else:
                    logger.warning("⚠️ 未在 ocr_result 中找到合并OCR结果存储键，跳过OCR纠正")
                    
            except Exception as correction_exc:
                logger.error(f"❌ OCR结果智能纠正失败: {correction_exc}")
                # 纠正失败不影响后续流程，继续使用原始OCR结果
                current_error = getattr(drawing, 'error_message', None)
                drawing.error_message = f"{current_error}; OCR correction failed: {correction_exc}" if current_error else f"OCR correction failed: {correction_exc}"
            
            logger.info(f"📋 OCR智能纠正阶段完成: 成功={ocr_correction_success}")

            # ========= 轨道 2: 大模型 Vision 扫描（使用共享智能切片结果 + 纠正后OCR结果）=========
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.GPT_ANALYSIS,
                    progress=60, message="Celery Worker 正在进行大模型图纸扫描（使用共享智能切片结果 + 纠正后OCR结果）..."
                )
            )
            
            vision_success = False
            try:
                logger.info("轨道 2: 🤖 开始 Vision Scan 分析（使用共享智能切片结果 + 纠正后OCR结果）...")
                vision_scanner = VisionScannerService()
                
                # 【最终修复】确保使用正确的OCR结果变量
                # enhanced_ocr_result 在上面已经从 ocr_result 复制而来
                if ocr_correction_success and corrected_ocr_result:
                    # 如果纠正成功，将纠正数据添加到 enhanced_ocr_result
                    enhanced_ocr_result['corrected_data'] = {
                        "drawing_basic_info": corrected_ocr_result.drawing_basic_info,
                        "component_list": corrected_ocr_result.component_list,
                        "global_notes": corrected_ocr_result.global_notes,
                        "corrected_text_regions": corrected_ocr_result.text_regions_corrected,
                        "correction_summary": corrected_ocr_result.correction_summary
                    }
                    logger.info(f"📋 将纠正后的OCR数据传递给Vision分析: {len(corrected_ocr_result.component_list)} 个构件")
                
                vision_scan_result = vision_scanner.scan_images_with_shared_slices(
                    temp_files, 
                    shared_slice_results,
                    drawing.id, 
                    task_id=task_id,
                    ocr_result=enhanced_ocr_result  # 传递包含纠正信息的OCR结果
                )

                if vision_scan_result.get("success"):
                    logger.info("轨道 2: ✅ Vision 扫描成功。")
                    drawing.llm_result_s3_key = vision_scan_result.get("result_s3_key")
                    vision_success = True
                else:
                    error_message = vision_scan_result.get('error', '未知的Vision扫描错误')
                    logger.error(f"轨道 2: ❌ Vision 扫描失败: {error_message}")
                    # 如果已有OCR错误信息，追加新的错误
                    current_error = getattr(drawing, 'error_message', None)
                    drawing.error_message = f"{current_error}; Vision failed: {error_message}" if current_error else f"Vision failed: {error_message}"
            
            except Exception as vision_exc:
                logger.error(f"轨道 2: ❌ Vision Scan 分析过程中发生严重异常: {vision_exc}", exc_info=True)
                current_error = getattr(drawing, 'error_message', None)
                drawing.error_message = f"{current_error}; Vision exception: {vision_exc}" if current_error else f"Vision exception: {vision_exc}"
                # 创建空的Vision结果
                vision_scan_result = {
                    "success": False,
                    "error": str(vision_exc)
                }

            # ========= Vision结果合并阶段（简化版）=========
            logger.info("🔄 开始Vision结果合并阶段...")
            
            # 初始化结果合并服务
            merger_service = ResultMergerService(storage_service=s3_service)
            
            # 合并Vision分析结果（如果Vision成功）
            if vision_success:
                try:
                    logger.info("🔄 开始合并Vision分析结果...")
                    # 定义slice_coordinate_map，避免未定义错误
                    slice_coordinate_map = {}
                    # 从vision_scan_result中提取切片结果
                    vision_slice_results = []
                    if isinstance(vision_scan_result, dict):
                        # 如果vision_scan_result包含分批结果
                        if 'batch_results' in vision_scan_result:
                            vision_slice_results = vision_scan_result['batch_results']
                        elif 'qto_data' in vision_scan_result:
                            # 如果是单个结果，包装成列表
                            vision_slice_results = [vision_scan_result]
                    
                    if vision_slice_results:
                        vision_merge_result = merger_service.merge_vision_analysis_results(
                            vision_results=vision_slice_results,
                            slice_coordinate_map=slice_coordinate_map,
                            original_image_info=original_image_info,
                            task_id=task_id,
                            drawing_id=drawing.id
                        )
                        
                        if vision_merge_result.get('success'):
                            logger.info(f"✅ Vision分析结果合并完成，生成 vision_full.json")
                            # 将合并结果添加到最终结果中
                            vision_scan_result['merged_full_result'] = vision_merge_result.get('vision_full_result')
                            vision_scan_result['vision_full_storage'] = vision_merge_result.get('storage_result')
                        else:
                            logger.warning(f"⚠️ Vision分析结果合并失败")
                    else:
                        logger.warning(f"⚠️ 没有找到有效的Vision切片结果进行合并")
                        
                except Exception as vision_merge_exc:
                    logger.error(f"❌ Vision分析结果合并异常: {vision_merge_exc}")

            logger.info("✅ 结果合并阶段完成")

            # ========= 数据汇总与后续处理 =========
            logger.info(f"数据汇总阶段: OCR成功={ocr_success}, Vision成功={vision_success}")
            
            # 如果两个流程都失败，则任务失败
            if not ocr_success and not vision_success:
                raise Exception("OCR和Vision分析流程都失败，无法进行后续处理。")
            
            # 如果至少有一个成功，尝试进行工程量计算
            analysis_result = {}
            components = []
            
            if vision_success:
                logger.info("✅ 使用Vision Scan结果进行后续计算。")
                
                # 优先使用合并后的Vision结果（包含所有构件）
                analysis_result = {}
                components = []
                
                # 1. 优先检查合并后的完整结果
                if vision_scan_result.get('merged_full_result'):
                    merged_result = vision_scan_result['merged_full_result']
                    components = merged_result.get('merged_components', [])
                    analysis_result = {
                        "components": components,
                        "project_info": merged_result.get('project_info', {}),
                        "component_summary": merged_result.get('component_summary', {}),
                        "source": "vision_merged_full",
                        "total_slices": merged_result.get('total_slices', 0)
                    }
                    logger.info(f"🎯 使用合并Vision结果: {len(components)} 个构件 (来源: merged_full_result)")
                
                # 已移除降级处理
                elif 'batch_results' in vision_scan_result:
                    batch_results = vision_scan_result['batch_results']
                    for batch_result in batch_results:
                        if batch_result.get('qto_data', {}).get('components'):
                            components.extend(batch_result['qto_data']['components'])
                    analysis_result = {
                        "components": components,
                        "source": "vision_batch_results",
                        "total_batches": len(batch_results)
                    }
                    logger.info(f"🎯 使用批次Vision结果: {len(components)} 个构件 (来源: batch_results)")
                
                # 已移除降级处理
                elif vision_scan_result.get("qto_data"):
                    analysis_result = vision_scan_result.get("qto_data", {})
                    components = analysis_result.get("components", [])
                    logger.info(f"🎯 使用单一Vision结果: {len(components)} 个构件 (来源: qto_data)")
                
                # 4. 兜底使用原始结果
                else:
                    analysis_result = vision_scan_result if isinstance(vision_scan_result, dict) and "components" in vision_scan_result else {}
                    components = analysis_result.get("components", [])
                    logger.info(f"🎯 使用原始Vision结果: {len(components)} 个构件 (来源: error)")
            elif ocr_success:
                logger.info("⚠️ Vision失败，尝试使用OCR结果进行基础计算。")
                # 基于OCR结果创建基础分析数据
                analysis_result = {
                    "components": [],
                    "source": "OCR_only",
                    "confidence": "low"
                }
                components = []
            
            logger.info(f"🔍 分析完成: 识别 {len(components)} 个构件")
            
            # 阶段5: 统一工程量计算
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.QUANTITY_CALCULATION,
                    progress=70, message="Celery Worker 正在计算工程量..."
                )
            )
            
            # 5️⃣ 统一工程量计算
            logger.info("📊 开始统一工程量计算...")
            try:
                quantity_result = quantity_engine.calculate_quantities(analysis_result)
                
                if quantity_result.get('status') != 'success':
                    logger.warning(f"工程量计算失败: {quantity_result.get('error')}")
                    # 创建基础的工程量结果
                    quantity_result = {
                        'status': 'partial_success',
                        'error': quantity_result.get('error'),
                        'summary': {'total_components': len(components)},
                        'message': '由于分析结果不完整，工程量计算仅提供基础信息'
                    }
            except Exception as calc_exc:
                logger.error(f"工程量计算异常: {calc_exc}")
                quantity_result = {
                    'status': 'error',
                    'error': str(calc_exc),
                    'summary': {'total_components': len(components)},
                    'message': '工程量计算失败，但基础信息已保存'
                }
            
            summary = quantity_result.get('summary', {})
            logger.info(f"📈 工程量计算完成: {summary.get('total_components', 0)} 个构件")
            
            # 6️⃣ 将最终结果保存到数据库
            logger.info("💾 开始保存最终结果到数据库...")
            final_result_payload = {
                "vision_scan_result": vision_scan_result,
                "ocr_result": ocr_result,
                "quantity_result": quantity_result,
                "processing_summary": {
                    "ocr_success": ocr_success,
                    "vision_success": vision_success,
                    "components_count": len(components),
                    "merged_results": {
                        "ocr_full_generated": bool(ocr_success and ocr_result.get('merged_full_result')),
                        "vision_full_generated": bool(vision_success and vision_scan_result.get('merged_full_result')),
                        "ocr_full_url": ocr_result.get('ocr_full_storage', {}).get('s3_url') if ocr_success else None,
                        "vision_full_url": vision_scan_result.get('vision_full_storage', {}).get('s3_url') if vision_success else None
                    }
                }
            }
            drawing.processing_result = final_result_payload
            drawing.status = 'completed'
            db.commit()
            logger.info("✅ 最终结果已保存到数据库。")
            
            # 阶段7: 任务成功完成
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id,
                    TaskStatus.SUCCESS,
                    TaskStage.COMPLETED,
                    progress=100,
                    message="图纸处理成功完成！",
                    results=final_result_payload
                )
            )
            
            logger.info(f"🎉 Celery Dual-Track Analysis处理流程成功完成: 图纸ID={db_drawing_id}")
            
            return {
                'status': 'success',
                'drawing_id': db_drawing_id,
                'source_type': source_type,
                'pipeline_type': 'Dual-Track Analysis',
                'components_count': len(components),
                'processed_images': len(temp_files),
                'ai_model': 'GPT-4o',
                'summary': summary,
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
            if temp_files:
                file_processor.cleanup_temp_files(temp_files)
                
        except Exception as cleanup_error:
            logger.warning(f"清理临时文件失败: {cleanup_error}")

@celery_app.task(bind=True, base=CallbackTask, name='batch_process_drawings')
def batch_process_drawings_celery_task(
    self,
    drawing_tasks: list
):
    """
    批量处理图纸的 Celery 任务
    
    Args:
        self: Celery 任务实例
        drawing_tasks: 图纸任务列表，每个元素包含处理参数
    """
    
    logger.info(f"🚀 开始 Celery 批量图纸处理任务: {len(drawing_tasks)} 个图纸")
    
    results = []
    
    for i, task_params in enumerate(drawing_tasks):
        try:
            logger.info(f"📋 处理第 {i+1}/{len(drawing_tasks)} 个图纸...")
            
            # 调用单个图纸处理任务
            result = process_drawing_celery_task.apply(
                args=(
                    task_params['db_drawing_id'],
                    task_params['task_id']
                )
            )
            
            results.append({
                "drawing_id": task_params['db_drawing_id'],
                "status": "success",
                "result": result.get()
            })
            
        except Exception as e:
            logger.error(f"❌ 批量处理第 {i+1} 个图纸失败: {str(e)}")
            results.append({
                "drawing_id": task_params.get('db_drawing_id', 'unknown'),
                "status": "error",
                "error": str(e)
            })
    
    logger.info(f"✅ Celery 批量图纸处理完成: {len(results)} 个结果")
    
    return {
        "status": "completed",
        "total_tasks": len(drawing_tasks),
        "successful_tasks": len([r for r in results if r["status"] == "success"]),
        "failed_tasks": len([r for r in results if r["status"] == "error"]),
        "results": results
    }