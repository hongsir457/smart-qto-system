#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸图像处理器
负责文件转换、图像处理和OCR相关功能
"""

import os
import logging
import tempfile
import base64
import asyncio
from typing import Dict, Any, List
from pathlib import Path

from app.tasks.real_time_task_manager import TaskStatus, TaskStage
from app.tasks import task_manager

logger = logging.getLogger(__name__)

class DrawingImageProcessor:
    """图纸图像处理器"""
    
    def __init__(self, core_processor):
        """初始化图像处理器"""
        self.core_processor = core_processor
        self.file_processor = core_processor.file_processor

    def process_file(self, local_file_path: str, drawing, task_id: str, loop) -> Dict[str, Any]:
        """处理文件并转换为图像"""
        try:
            logger.info(f"🔄 开始文件处理: {drawing.file_type}")
            
            temp_files = []
            source_type = "unknown"
            
            if drawing.file_type.lower() in ['dwg', 'dxf']:
                # DWG/DXF文件处理
                source_type = "dwg"
                temp_files = self._process_dwg_file(local_file_path, drawing, task_id, loop)
                
            elif drawing.file_type.lower() == 'pdf':
                # PDF文件处理
                source_type = "pdf"
                temp_files = self._process_pdf_file(local_file_path, drawing, task_id, loop)
                
            elif drawing.file_type.lower() in ['png', 'jpg', 'jpeg', 'bmp', 'tiff']:
                # 图片文件处理
                source_type = "image"
                temp_files = [local_file_path]  # 图片文件直接使用
                
            else:
                raise ValueError(f"不支持的文件类型: {drawing.file_type}")
            
            if not temp_files:
                raise Exception("文件处理后没有生成任何图像文件")
            
            logger.info(f"✅ 文件处理成功，生成 {len(temp_files)} 个图像文件")
            
            return {
                "success": True,
                "temp_files": temp_files,
                "source_type": source_type,
                "file_count": len(temp_files)
            }
            
        except Exception as e:
            logger.error(f"❌ 文件处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "temp_files": [],
                "source_type": "unknown"
            }

    def _process_dwg_file(self, local_file_path: str, drawing, task_id: str, loop) -> List[str]:
        """处理DWG文件"""
        try:
            # 更新任务状态
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.FILE_PROCESSING,
                    progress=25, message="正在处理DWG文件..."
                )
            )
            
            if not self.file_processor:
                raise Exception("文件处理器不可用")
            
            # 使用文件处理器处理DWG
            result = self.file_processor.process_file(local_file_path)
            
            if not result.get("success"):
                raise Exception(f"DWG处理失败: {result.get('error', '未知错误')}")
            
            temp_files = result.get("temp_files", [])
            if not temp_files:
                raise Exception("DWG处理后没有生成图像文件")
            
            logger.info(f"✅ DWG处理完成，生成 {len(temp_files)} 个图像")
            return temp_files
            
        except Exception as e:
            logger.error(f"❌ DWG文件处理失败: {e}")
            raise

    def _process_pdf_file(self, local_file_path: str, drawing, task_id: str, loop) -> List[str]:
        """处理PDF文件"""
        try:
            # 更新任务状态
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.FILE_PROCESSING,
                    progress=25, message="正在处理PDF文件..."
                )
            )
            
            if not self.file_processor:
                raise Exception("文件处理器不可用")
            
            # 使用文件处理器处理PDF
            result = self.file_processor.process_file(local_file_path)
            
            if not result.get("success"):
                raise Exception(f"PDF处理失败: {result.get('error', '未知错误')}")
            
            temp_files = result.get("temp_files", [])
            if not temp_files:
                raise Exception("PDF处理后没有生成图像文件")
            
            logger.info(f"✅ PDF处理完成，生成 {len(temp_files)} 个图像")
            return temp_files
            
        except Exception as e:
            logger.error(f"❌ PDF文件处理失败: {e}")
            raise

    async def process_images_with_shared_slices(self, image_paths: List[str], 
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
                        ocr_result = await self._process_single_slice_ocr(
                            slice_data, j, drawing_id, task_id
                        )
                        if ocr_result:
                            slice_ocr_results.append(ocr_result)
                            total_slices_processed += 1
                    
                    # 合并所有切片的OCR结果
                    if slice_ocr_results:
                        merged_result = self._merge_slice_ocr_results(slice_ocr_results)
                        all_results.append(merged_result)
                        total_text_regions += len(merged_result.get('text_regions', []))
                        successful_images += 1
                        
                        logger.info(f"  ✅ 共享切片OCR成功: {len(slice_ocr_results)} 个切片处理完成")
                    else:
                        logger.warning(f"  ❌ 所有切片OCR都失败")
                else:
                    # 使用原图OCR处理
                    logger.info(f"  📄 使用原图OCR处理")
                    
                    result = await self._process_direct_image_ocr(image_path, drawing_id)
                    if result.get('success'):
                        all_results.append(result)
                        total_text_regions += len(result.get('text_regions', []))
                        successful_images += 1
                        logger.info(f"  ✅ 原图OCR成功")
                    else:
                        logger.warning(f"  ❌ 原图OCR失败")
                        
            except Exception as e:
                logger.error(f"  ❌ 处理图像异常: {e}")
        
        # 汇总结果
        if successful_images > 0:
            return self._build_final_ocr_result(all_results, successful_images, total_text_regions, total_slices_processed)
        else:
            return {
                "success": False,
                "error": "所有图像OCR处理都失败",
                "statistics": {
                    "total_images": len(image_paths),
                    "successful_images": 0,
                    "total_text_regions": 0
                }
            }

    async def _process_single_slice_ocr(self, slice_data, slice_index: int, drawing_id: int, task_id: str) -> Dict[str, Any]:
        """处理单个切片的OCR"""
        try:
            # 将base64数据转换为临时图片文件
            slice_image_data = base64.b64decode(slice_data.base64_data)
            temp_slice_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_slice_file.write(slice_image_data)
            temp_slice_file.close()
            
            # 使用基础OCR服务处理单个切片
            from app.services.ocr.paddle_ocr import PaddleOCRService
            basic_ocr = PaddleOCRService()
            slice_result = basic_ocr.recognize_text(temp_slice_file.name, save_to_sealos=True, drawing_id=str(drawing_id))
            
            if slice_result.get('text_regions'):
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
                
                result = {
                    'slice_id': slice_data.slice_id,
                    'text_regions': adjusted_regions,
                    'slice_text': slice_result.get('all_text', ''),
                    'slice_index': slice_index
                }
                
                logger.info(f"    ✅ 切片 {slice_index+1} OCR完成: {len(adjusted_regions)} 个文本区域")
                
                # 清理临时文件
                os.unlink(temp_slice_file.name)
                
                return result
            else:
                logger.warning(f"    ❌ 切片 {slice_index+1} OCR失败")
                # 清理临时文件
                os.unlink(temp_slice_file.name)
                return None
                
        except Exception as e:
            logger.error(f"    ❌ 切片 {slice_index+1} OCR异常: {e}")
            return None

    async def _process_direct_image_ocr(self, image_path: str, drawing_id: int) -> Dict[str, Any]:
        """直接处理原图OCR"""
        try:
            from app.services.ocr.paddle_ocr import PaddleOCRService
            basic_ocr = PaddleOCRService()
            result = basic_ocr.recognize_text(image_path, save_to_sealos=True, drawing_id=str(drawing_id))
            
            if result.get('text_regions'):
                result['processing_method'] = 'direct_ocr'
                result['success'] = True
                return result
            else:
                return {"success": False, "error": "原图OCR失败"}
                
        except Exception as e:
            logger.error(f"原图OCR异常: {e}")
            return {"success": False, "error": str(e)}

    def _merge_slice_ocr_results(self, slice_ocr_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并切片OCR结果"""
        merged_text_regions = []
        merged_text = []
        
        for slice_result in slice_ocr_results:
            merged_text_regions.extend(slice_result['text_regions'])
            if slice_result['slice_text']:
                merged_text.append(slice_result['slice_text'])
        
        # 去重处理（简单的基于位置的去重）
        deduplicated_regions = self._remove_duplicate_regions(merged_text_regions)
        
        return {
            'success': True,
            'texts': [{'text': region.get('text', ''), 'bbox': region.get('bbox', [])} for region in deduplicated_regions],
            'text_regions': deduplicated_regions,
            'all_text': '\n'.join(merged_text),
            'statistics': {
                'total_regions': len(deduplicated_regions),
                'total_slices': len(slice_ocr_results),
                'processed_slices': len(slice_ocr_results),
                'avg_confidence': self._calculate_average_confidence(deduplicated_regions)
            },
            'processing_method': 'shared_slice_ocr'
        }

    def _remove_duplicate_regions(self, text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """移除重复的文本区域"""
        # 简单的去重实现，基于文本内容和位置
        unique_regions = []
        seen_texts = set()
        
        for region in text_regions:
            text = region.get('text', '').strip()
            bbox = region.get('bbox', [])
            
            # 创建唯一标识
            if bbox and len(bbox) >= 4:
                position_key = f"{text}_{bbox[0]}_{bbox[1]}"
            else:
                position_key = text
            
            if position_key not in seen_texts and text:
                seen_texts.add(position_key)
                unique_regions.append(region)
        
        return unique_regions

    def _calculate_average_confidence(self, text_regions: List[Dict[str, Any]]) -> float:
        """计算平均置信度"""
        confidences = [region.get('confidence', 0.8) for region in text_regions if region.get('confidence')]
        return sum(confidences) / len(confidences) if confidences else 0.8

    def _build_final_ocr_result(self, all_results: List[Dict], successful_images: int, 
                               total_text_regions: int, total_slices_processed: int) -> Dict[str, Any]:
        """构建最终的OCR结果"""
        # 合并所有文本区域
        all_text_regions = []
        all_text = []
        
        for result in all_results:
            all_text_regions.extend(result.get('text_regions', []))
            if result.get('all_text'):
                all_text.append(result['all_text'])
        
        return {
            "success": True,
            "text_regions": all_text_regions,
            "all_text": '\n'.join(all_text),
            "statistics": {
                "total_images": successful_images,
                "successful_images": successful_images,
                "total_text_regions": total_text_regions,
                "total_slices_processed": total_slices_processed,
                "avg_confidence": self._calculate_average_confidence(all_text_regions)
            },
            "processing_method": "shared_slice_batch_ocr",
            "storage_info": "已保存到Sealos存储"
        }

    def cleanup(self):
        """清理资源"""
        logger.info("🧹 DrawingImageProcessor 资源清理完成") 