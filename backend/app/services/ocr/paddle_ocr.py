#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR服务 - Eager Initialization (预先初始化) 版本
在模块加载时直接初始化全局唯一的PaddleOCR实例，以解决在Celery等环境中初始化失败的问题。
"""
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import cv2
import uuid
import json
from io import BytesIO
# import shutil  # No longer needed for debugging

# 核心依赖，如果缺失则系统无法提供OCR功能
try:
    from paddleocr import PaddleOCR
except ImportError:
    logging.critical("❌ FATAL: paddleocr库未安装，OCR功能将完全不可用。请运行: pip install paddleocr")
    PaddleOCR = None

from app.core.config import settings
from app.utils.image_processing import correct_skew, enhance_image, calculate_image_clarity

# 导入图像预处理器
try:
    from app.services.image_preprocessor import image_preprocessor
except ImportError:
    image_preprocessor = None

# 导入存储服务
try:
    from app.services.s3_service import S3Service
    from app.services.dual_storage_service import DualStorageService
except ImportError:
    S3Service = None
    DualStorageService = None

logger = logging.getLogger(__name__)

# --- Eager Initialization of Global PaddleOCR Instance ---

def _initialize_global_paddleocr():
    """
    在模块加载时执行的预先初始化函数。
    创建并预热一个全局唯一的PaddleOCR实例。
    """
    if not PaddleOCR:
        logger.error("🚫 PaddleOCR库未加载，无法初始化。")
        return None

    logger.info("🚀 EAGERLY INITIALIZING PADDLEOCR (GLOBAL INSTANCE)...")
    try:
        # 优化配置，平衡性能与资源消耗
        config = {
            'use_angle_cls': True,
            'lang': 'ch',
            'use_space_char': True,
            'drop_score': 0.3,  # 降低丢弃阈值，保留更多低置信度结果
            'use_gpu': False,
            'enable_mkldnn': True,
            'cpu_threads': max(1, cv2.getNumberOfCPUs() // 2),
            'show_log': False,
            'det_limit_side_len': 960,
            'max_side_len': 2400, # 配合更高DPI，提升最大边长
            'det_db_box_thresh': 0.5, # 降低框检测阈值，更容易检测小文本
        }
        logger.info(f"⚙️ PaddleOCR Config (High Accuracy): {config}")

        logger.info("⏳ Creating PaddleOCR instance...")
        start_time = time.time()
        ocr_instance = PaddleOCR(**config)
        creation_time = time.time() - start_time
        logger.info(f"✅ PaddleOCR instance created in {creation_time:.2f}s.")

        # 预热，确保模型完全加载到内存
        logger.info("🔥 Warming up PaddleOCR instance...")
        start_time = time.time()
        warmup_image = np.zeros((100, 200, 3), dtype='uint8')
        cv2.putText(warmup_image, "Warmup", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        ocr_instance.ocr(warmup_image, cls=True)
        warmup_time = time.time() - start_time
        logger.info(f"✅ PaddleOCR warmup complete in {warmup_time:.2f}s.")
        
        return ocr_instance

    except Exception as e:
        logger.critical("❌❌❌ FATAL: Global PaddleOCR initialization failed. OCR will be unavailable.", exc_info=True)
        return None

# --- Global Instance & Thread Lock ---
_paddle_ocr_instance = _initialize_global_paddleocr()
_ocr_lock = threading.Lock()  # 用于OCR调用的线程安全锁

class PaddleOCRService:
    """
    对全局PaddleOCR实例的封装服务。
    提供文本识别及相关的辅助功能。
    """
    def __init__(self):
        """初始化服务，关联到全局OCR实例，并准备存储服务。"""
        self.ocr = _paddle_ocr_instance
        self.initialized = self.ocr is not None
        
        # 已移除降级处理
        try:
            self.dual_storage = DualStorageService() if DualStorageService else None
            self.s3_service = S3Service() if S3Service else None
            self.storage_service = self.dual_storage or self.s3_service
        except Exception as e:
            logger.warning(f"存储服务初始化失败: {e}")
            self.dual_storage = None
            self.s3_service = None
            self.storage_service = None
            
        if self.initialized:
            logger.info("♻️ PaddleOCRService is using the pre-initialized global instance.")
            if self.dual_storage:
                logger.info("✅ 使用双重存储服务")
            elif self.s3_service:
                logger.info("⚠️ 降级使用S3存储服务")
            else:
                logger.warning("⚠️ 所有存储服务不可用，文件保存功能将被禁用")
        else:
            logger.warning("⚠️ PaddleOCRService is in a non-functional state due to initialization failure.")

    def is_available(self) -> bool:
        """检查OCR实例是否已成功初始化并可用。"""
        return self.initialized

    def get_status(self) -> Dict[str, Any]:
        """获取服务的当前状态。"""
        return {
            'initialized': self.initialized,
            'ocr_instance_ready': self.initialized,
            'lazy_init_attempted': True, # In eager mode, it's always "attempted" at load time
            'is_available': self.is_available(),
            'mode': 'PaddleOCR' if self.initialized else 'Unavailable'
        }

    def recognize_text(self, image_path: str, save_to_sealos: bool = True, drawing_id: str = None) -> Dict[str, Any]:
        """
        执行OCR文本识别，并可选地将结果保存到云存储
        
        Returns:
            Dict containing:
            - success: bool
            - text_regions: List[Dict] with detected text regions
            - all_text: str concatenated text
            - statistics: Dict with region count and confidence
            - storage_info: Dict if saved to Sealos
        """

        try:
            image_file = Path(image_path)
            if not image_file.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            logger.info(f"🚀 Starting OCR recognition for: {image_path}")
            
            logger.info("📊 (Pre-check) Detecting text regions on original image...")

            try:
                # 修复: 使用正确的PaddleOCR API
                # PaddleOCR的ocr方法返回格式: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], (text, confidence)]
                ocr_result = self.ocr.ocr(str(image_file), rec=True)

                if ocr_result is None or not ocr_result:
                    logger.warning("OCR detection returned no results.")
                    return {
                        "success": False,
                        "error": "No text detected",
                        "text_regions": [],
                        "all_text": "",
                        "statistics": {"total_regions": 0, "avg_confidence": 0},
                        "raw_paddle_data": []
                    }
                
                # ocr_result通常是一个嵌套列表: [[...], [...], ...]
                # 处理可能的多页结果（PDF转图片）
                if isinstance(ocr_result, list) and len(ocr_result) > 0:
                    if isinstance(ocr_result[0], list) and len(ocr_result[0]) > 0:
                        # 如果是多页，取第一页
                        page_result = ocr_result[0]
                    else:
                        page_result = ocr_result
                else:
                    page_result = []
                
                logger.info(f"🔍 Found {len(page_result)} text boxes, processing recognition...")
                
                # 处理OCR结果
                processed_result = self._process_ocr_result(page_result)
                processed_result["raw_paddle_data"] = page_result
                processed_result["success"] = True
                
                # 检查结果是否有效
                if processed_result.get("statistics", {}).get("total_regions", 0) == 0:
                    logger.warning("OCR recognition completed but no text regions found.")
                    # 可能不是错误，只是图片中没有文字
                    processed_result["success"] = False
                    processed_result["error"] = "No text regions detected"
                    
                # 应用特定领域的文本校正 - 根据用户要求已禁用
                # processed_result = self._apply_construction_text_correction(processed_result)
                logger.info("🚫 文本纠错已禁用，保持OCR原始结果")

                if save_to_sealos:
                    try:
                        storage_info = self._save_complete_raw_result_to_sealos(
                            raw_paddle_data=page_result,
                            ocr_result=processed_result,
                            image_path=image_path,
                            drawing_id=drawing_id
                        )
                        processed_result["storage_info"] = storage_info
                        if storage_info.get("saved"):
                            logger.info(f"✅ OCR结果已保存到Sealos: {storage_info.get('json_result', {}).get('s3_key', 'N/A')}")
                        else:
                            logger.warning(f"⚠️ OCR结果保存失败: {storage_info.get('error', 'Unknown error')}")
                    except Exception as storage_error:
                        logger.error(f"❌ OCR结果存储异常: {storage_error}")
                        processed_result["storage_info"] = {"saved": False, "error": str(storage_error)}
                
                return processed_result

            except Exception as e:
                import traceback
                logger.error(f"⚠️ An error occurred during OCR recognition process: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # 返回一致的错误格式
                return {
                    "success": False,
                    "error": str(e),
                    "text_regions": [],
                    "all_text": "",
                    "statistics": {"total_regions": 0, "avg_confidence": 0},
                    "raw_paddle_data": []
                }

        except Exception as e:
            import traceback
            logger.error(f"⚠️ An error occurred during OCR recognition process: {e}")
            logger.debug(traceback.format_exc())
            
            # 返回一致的错误格式
            return {
                "success": False,
                "error": str(e),
                "text_regions": [],
                "all_text": "",
                "statistics": {"total_regions": 0, "avg_confidence": 0},
                "raw_paddle_data": []
            }

    def extract_text_from_image(self, image_path: str) -> List[Dict]:
        """
        提取图像中的文本（兼容方法）
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            List[Dict]: OCR结果列表
        """
        try:
            # 调用recognize_text获取完整结果
            result = self.recognize_text(image_path, save_to_sealos=False)
            
            if not result.get("success", False):
                logger.warning(f"OCR文本提取失败: {result.get('error', '未知错误')}")
                return []
            
            # 返回text_regions格式的数据
            text_regions = result.get("text_regions", [])
            
            # 转换为兼容格式
            extracted_texts = []
            for region in text_regions:
                extracted_texts.append({
                    "text": region.get("text", ""),
                    "position": region.get("position", []),
                    "confidence": region.get("confidence", 0.0),
                    "bbox": region.get("bbox", {})
                })
            
            logger.debug(f"提取文本完成: {len(extracted_texts)} 个文本区域")
            return extracted_texts
            
        except Exception as e:
            logger.error(f"提取图像文本失败: {e}")
            return []

    def _structure_result(self, det_boxes, rec_result):
        """
        Helper function to combine detection and recognition results.
        """
        structured_output = []
        # rec_result format: [('text', confidence), ...]
        if len(det_boxes) != len(rec_result):
            logger.warning(
                f"Mismatch between detected boxes ({len(det_boxes)}) and recognized texts ({len(rec_result)}). "
                f"Results may be misaligned."
            )

        for i, res in enumerate(rec_result):
            if i < len(det_boxes):
                box = det_boxes[i]
                text, confidence = res
                structured_output.append({
                    "box": [[int(p[0]), int(p[1])] for p in box],
                    "text": text,
                    "confidence": float(confidence)
                })
        return structured_output

    def recognize_images(self, image_paths: List[str], drawing_id: int = None) -> Dict[str, Any]:
        """
        识别图像列表，并将所有结果打包上传到S3。
        这是为Celery双轨任务设计的核心方法。
        """
        if not self.is_available():
            logger.error("🚫 OCR service is unavailable. Cannot process image list.")
            return {"success": False, "error": "PaddleOCR not initialized"}

        logger.info(f"🚀🚀 Starting batch OCR recognition for {len(image_paths)} images. Drawing ID: {drawing_id}")
        
        all_processed_results = []
        all_raw_results = [] # 存储最原始的paddle ocr输出
        
        for image_path in image_paths:
            # 调用单图识别，但不让它单独上传S3
            processed_result = self.recognize_text(image_path, save_to_sealos=False, drawing_id=str(drawing_id))
            all_processed_results.append(processed_result)
            
            # 修复: 确保processed_result是字典格式，并安全地提取原始数据
            if isinstance(processed_result, dict) and processed_result.get("raw_paddle_data"):
                all_raw_results.extend(processed_result["raw_paddle_data"])
            elif not isinstance(processed_result, dict):
                logger.warning(f"Expected dict from recognize_text, got {type(processed_result)}: {processed_result}")

        # 检查是否有任何成功的结果
        successful_results = [r for r in all_processed_results if isinstance(r, dict) and r.get("success", False)]
        
        if not successful_results:
            # 所有图片都处理失败
            error_msgs = []
            for r in all_processed_results:
                if isinstance(r, dict) and r.get("error"):
                    error_msgs.append(r["error"])
            
            combined_error = "; ".join(error_msgs) if error_msgs else "All OCR processing failed"
            logger.error(f"❌ (Batch OCR) All images failed processing: {combined_error}")
            
            return {
                "success": False,
                "error": combined_error,
                "total_images_processed": len(image_paths),
                "successful_images": 0
            }

        # 使用现有的、功能更全的保存方法来处理上传
        # 这个方法会同时保存 .json 和 .txt
        try:
            save_result_info = self._save_complete_raw_result_to_sealos(
                raw_paddle_data=all_raw_results,
                ocr_result={"text_regions": [region for res in successful_results for region in res.get("text_regions", [])]}, # 合并所有文本区域
                image_path=image_paths[0] if image_paths else "batch_process",
                drawing_id=str(drawing_id)
            )
        except Exception as e:
            logger.error(f"❌ (Batch OCR) Failed to save results to S3: {e}")
            return {
                "success": False,
                "error": f"Failed to save results: {str(e)}",
                "total_images_processed": len(image_paths),
                "successful_images": len(successful_results)
            }

        if not save_result_info.get("saved"):
            error_msg = f"Failed to save batch result to S3: {save_result_info.get('error')}"
            logger.error(f"❌ (Batch OCR) {error_msg}")
            return {
                "success": False, 
                "error": error_msg,
                "total_images_processed": len(image_paths),
                "successful_images": len(successful_results)
            }

        # **修复核心问题**: 额外保存一个固定名称的合并文件供下游使用
        try:
            # 构建合并结果数据
            merged_data = {
                "meta": {
                    "ocr_id": str(drawing_id),
                    "drawing_id": drawing_id,
                    "processing_time": sum(r.get('statistics', {}).get('processing_time', 0) for r in successful_results),
                    "total_images": len(image_paths),
                    "successful_images": len(successful_results),
                    "processing_method": "paddle_ocr_batch_merged"
                },
                "merged_ocr_result": {
                    "total_text_regions": sum(len(r.get('text_regions', [])) for r in successful_results),
                    "text_regions": [region for res in successful_results for region in res.get("text_regions", [])],
                    "all_text": '\n'.join([res.get('all_text', '') for res in successful_results if res.get('all_text')]),
                    "statistics": {
                        "total_regions": sum(len(r.get('text_regions', [])) for r in successful_results),
                        "avg_confidence": sum(r.get('statistics', {}).get('avg_confidence', 0) for r in successful_results) / len(successful_results) if successful_results else 0,
                        "processing_time": sum(r.get('statistics', {}).get('processing_time', 0) for r in successful_results)
                    }
                }
            }
            
            # 保存为固定名称的merged_result.json
            merged_content = json.dumps(merged_data, ensure_ascii=False, indent=2)
            
            # 上传合并结果
            result_upload = self.storage_service.upload_content_sync(
                content=merged_content,
                s3_key=f"ocr_results/{drawing_id}/merged_result.json",
                content_type="application/json"
            )
            
            if result_upload.get("success"):
                logger.info(f"✅ 额外保存合并结果为 merged_result.json")
                # 添加合并结果信息到返回值
                save_result_info["merged_result"] = {
                    "s3_key": f"ocr_results/{drawing_id}/merged_result.json",
                    "s3_url": result_upload.get("final_url"),
                    "storage_method": result_upload.get("storage_method")
                }
            else:
                logger.warning(f"⚠️ 保存合并结果失败: {result_upload.get('error')}")
                
        except Exception as merge_e:
            logger.warning(f"⚠️ 保存额外合并文件失败（不影响主流程）: {merge_e}")

        logger.info(f"✅ (Batch OCR) 结果已成功上传到 S3。JSON 和 TXT 文件均已保存。")

        # 修复: 安全地计算总区域数
        total_regions = 0
        for r in successful_results:
            if isinstance(r, dict) and r.get('statistics'):
                total_regions += r['statistics'].get('total_regions', 0)

        return {
            "success": True,
            "result_s3_key": save_result_info.get("json_result", {}).get("s3_key"), # 主结果是JSON
            "result_s3_url": save_result_info.get("json_result", {}).get("s3_url"),
            "txt_result_s3_key": save_result_info.get("txt_result", {}).get("s3_key"), # TXT结果的key
            "merged_result_s3_key": save_result_info.get("merged_result", {}).get("s3_key"), # 新增：合并结果的key
            "storage_result": save_result_info.get("merged_result", {}),  # 添加存储结果信息，用于下游使用
            "total_images_processed": len(image_paths),
            "successful_images": len(successful_results),
            "total_text_regions_found": total_regions,
        }

    # --- Image Pre-processing ---
    def _enhance_image_for_ocr(self, image_path: str) -> str:
        """
        对图像进行OCR优化预处理，包括自动resize和质量增强
        """
        if not image_preprocessor:
            logger.warning("⚠️ 图像预处理器未可用，使用原始图像")
            return image_path
        
        try:
            logger.info(f"🔧 开始OCR图像预处理: {image_path}")
            
            # 获取图像信息用于日志
            image_info = image_preprocessor.get_image_info(image_path)
            logger.info(f"📊 原始图像信息: {image_info}")
            
            # 自动调整图像尺寸和质量
            optimized_path = image_preprocessor.auto_resize_for_ocr(image_path)
            
            if optimized_path != image_path:
                # 获取优化后的图像信息
                optimized_info = image_preprocessor.get_image_info(optimized_path)
                logger.info(f"✨ 优化后图像信息: {optimized_info}")
            
            return optimized_path
            
        except Exception as e:
            logger.error(f"❌ 图像预处理失败，使用原始图像: {e}", exc_info=True)
            return image_path

    # --- Result Post-processing ---
    def _process_ocr_result(self, result: List[List]) -> Dict[str, Any]:
        """将PaddleOCR原始输出转换为结构化的字典。"""
        text_regions = []
        all_text_list = []
        
        # --- FIX: Handle nested list structure from PaddleOCR ---
        # PaddleOCR can return results inside an extra list, e.g., [[...results...]]
        actual_results = result
        if result and isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):
             actual_results = result[0]
        # --- END FIX ---
        
        for i, line in enumerate(actual_results):
            if line is None:
                continue
            
            try:
                points, (text, confidence) = line
                bbox = self._calculate_bbox_info(points)
                
                region_data = {
                    'id': i,
                    'text': text,
                    'confidence': confidence,
                    'bbox_xyxy': bbox,
                    'type_analysis': self._analyze_text_type(text)
                }
                text_regions.append(region_data)
                all_text_list.append(text)
            except Exception as e:
                logger.error(f"Failed to process a single OCR line: {line}. Error: {e}", exc_info=True)

        statistics = self._calculate_statistics(text_regions)
        
        return {
            "text_regions": text_regions,
            "all_text": "\n".join(all_text_list),
            "statistics": statistics
        }

    def _calculate_bbox_info(self, points: List[List[float]]) -> Dict[str, float]:
        """从坐标点计算边界框信息。"""
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        return {'x_min': x_min, 'y_min': y_min, 'x_max': x_max, 'y_max': y_max}

    def _analyze_text_type(self, text: str) -> Dict[str, bool]:
        """分析文本类型（数字、字母等）。"""
        return {
            'is_numeric': text.replace('.', '', 1).isdigit(),
            'is_alphanumeric': text.isalnum(),
            'contains_letters': any(c.isalpha() for c in text),
            'contains_digits': any(c.isdigit() for c in text)
        }

    def _calculate_statistics(self, text_regions: List[Dict]) -> Dict[str, Any]:
        """计算识别结果的统计信息。"""
        if not text_regions:
            return {'total_regions': 0, 'avg_confidence': 0}
        
        total_regions = len(text_regions)
        avg_confidence = sum(r['confidence'] for r in text_regions) / total_regions
        return {'total_regions': total_regions, 'avg_confidence': avg_confidence}

    def _apply_construction_text_correction(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """应用建筑领域的文本校正规则。"""
        
        # 建筑术语纠错字典
        correction_dict = {
            # 构件类型纠错
            'KZ': ['XZ', 'KJ', 'K2', 'KZ1', 'K乙'],  # 柱的常见错误
            'GL': ['CL', 'G1', 'OL', '6L', 'GL1'],    # 梁的常见错误  
            'JC': ['JO', 'IC', 'JG', 'J0', 'JC1'],    # 基础的常见错误
            'WQ': ['MQ', 'W0', 'VQ', 'WO'],           # 墙的常见错误
            'LT': ['L7', 'LI', '17', 'LT1'],          # 楼梯的常见错误
            'SZ': ['52', 'S2', 'SZ1', 'SJ'],         # 剪力墙的常见错误
            
            # 钢筋符号纠错
            'Φ': ['φ', 'O', '0', '@', 'θ', 'Ф'],     # 钢筋符号
            '@': ['a', 'A', '&', 'α', 'о'],          # 间距符号
            'C': ['G', 'c', '℃', 'C2'],               # 混凝土等级
            
            # 数字纠错
            '1': ['I', 'l', '|', '!'],
            '0': ['O', 'o', '°'],
            '2': ['Z', 'z'],
            '5': ['S', 's'],
            '6': ['G', 'b'],
            '8': ['B'],
            '9': ['g', 'q'],
            
            # 单位纠错
            'mm': ['mm', 'MM', 'rnm', 'nn'],
            'm': ['rn', 'nn', 'M'],
            'MPa': ['MPA', 'Mpa', 'mpa', 'Mfa'],
        }
        
        # 格式化规则
        format_rules = [
            # 构件编号格式化: KZ-1, GL-2 等
            (r'([KGJLWSZBC])([Z|L|C|Q|T])[-\s]*(\d+)', r'\1\2-\3'),
            # 钢筋规格格式化: Φ12@200
            (r'[ΦφO0](\d+)[@aA&](\d+)', r'Φ\1@\2'),
            # 尺寸格式化: 350x500, 350×500
            (r'(\d+)[x×*](\d+)', r'\1×\2'),
            # 混凝土等级: C30, C35 等
            (r'[CcGg](\d+)', r'C\1'),
        ]
        
        corrected_count = 0
        
        for region in ocr_result.get('text_regions', []):
            original_text = region.get('text', '')
            corrected_text = original_text
            
            # 应用词典纠错（更精确的匹配）
            for correct, errors in correction_dict.items():
                for error in errors:
                    # 只在整词匹配或构件编号上下文中进行替换
                    if error == corrected_text or (error in corrected_text and len(error) >= 2):
                        corrected_text = corrected_text.replace(error, correct)
            
            # 应用格式化规则
            import re
            for pattern, replacement in format_rules:
                corrected_text = re.sub(pattern, replacement, corrected_text)
            
            # 如果有修改，记录原始文本
            if corrected_text != original_text:
                region['original_text'] = original_text
                region['text'] = corrected_text
                region['corrected'] = True
                region['correction_type'] = 'construction_terminology'
                corrected_count += 1
                logger.info(f"🔧 文本纠错: '{original_text}' → '{corrected_text}'")
        
        # 更新统计信息
        if corrected_count > 0:
            ocr_result['correction_applied'] = True
            ocr_result['corrections_count'] = corrected_count
            logger.info(f"✅ 应用建筑术语纠错: {corrected_count} 处修正")
        
        return ocr_result
    
    def _format_raw_result_as_txt(self, raw_paddle_data: List[List], image_path: str) -> str:
        """
        将PaddleOCR原始结果格式化为可读的TXT文本
        
        Args:
            raw_paddle_data: PaddleOCR原始输出
            image_path: 图像路径
            
        Returns:
            str: 格式化的TXT内容
        """
        try:
            lines = []
            lines.append("="*60)
            lines.append("PaddleOCR识别结果")
            lines.append("="*60)
            lines.append(f"图像文件: {Path(image_path).name}")
            lines.append(f"识别时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
            
            # 处理嵌套列表结构
            actual_results = raw_paddle_data
            if raw_paddle_data and isinstance(raw_paddle_data, list) and len(raw_paddle_data) == 1 and isinstance(raw_paddle_data[0], list):
                actual_results = raw_paddle_data[0]
            
            if not actual_results:
                lines.append("未检测到任何文本内容")
                lines.append("")
                lines.append("="*60)
                return "\n".join(lines)
            
            lines.append(f"检测到 {len(actual_results)} 个文本区域:")
            lines.append("")
            
            # 按置信度排序（从高到低）
            sorted_results = sorted(actual_results, key=lambda x: x[1][1] if len(x) > 1 and len(x[1]) > 1 and x[1][1] is not None else 0, reverse=True)
            
            for i, line in enumerate(sorted_results, 1):
                if line is None:
                    continue
                
                try:
                    points, (text, confidence) = line
                    
                    # 计算边界框
                    x_coords = [p[0] for p in points]
                    y_coords = [p[1] for p in points]
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    
                    # 格式化输出
                    lines.append(f"[{i:02d}] 文本: {text}")
                    lines.append(f"     置信度: {confidence:.3f}")
                    lines.append(f"     位置: ({x_min:.0f}, {y_min:.0f}) - ({x_max:.0f}, {y_max:.0f})")
                    lines.append(f"     尺寸: {x_max-x_min:.0f} x {y_max-y_min:.0f}")
                    lines.append("")
                    
                except Exception as e:
                    lines.append(f"[{i:02d}] 解析错误: {str(e)}")
                    lines.append("")
            
            # 添加统计信息
            lines.append("-"*40)
            lines.append("统计信息:")
            
            # 计算平均置信度
            confidences = []
            texts = []
            for line in actual_results:
                if line and len(line) > 1 and len(line[1]) > 1:
                    text, confidence = line[1]
                    confidences.append(confidence)
                    texts.append(text)
            
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                max_confidence = max(confidences)
                min_confidence = min(confidences)
                
                lines.append(f"平均置信度: {avg_confidence:.3f}")
                lines.append(f"最高置信度: {max_confidence:.3f}")
                lines.append(f"最低置信度: {min_confidence:.3f}")
                lines.append(f"总字符数: {sum(len(text) for text in texts)}")
                lines.append(f"总文本数: {len(texts)}")
            
            lines.append("")
            lines.append("-"*40)
            lines.append("纯文本内容:")
            lines.append("-"*40)
            
            # 添加纯文本内容（按位置从上到下，从左到右排序）
            text_with_positions = []
            for line in actual_results:
                if line and len(line) > 1:
                    try:
                        points, (text, confidence) = line
                        y_coords = [p[1] for p in points]
                        x_coords = [p[0] for p in points]
                        avg_y = sum(y_coords) / len(y_coords)
                        avg_x = sum(x_coords) / len(x_coords)
                        text_with_positions.append((avg_y, avg_x, text))
                    except:
                        continue
            
            # 按Y坐标排序（从上到下），然后按X坐标排序（从左到右）
            text_with_positions.sort(key=lambda x: (x[0], x[1]))
            
            for _, _, text in text_with_positions:
                lines.append(text)
            
            lines.append("")
            lines.append("="*60)
            lines.append("说明:")
            lines.append("- 文本按置信度从高到低排序")
            lines.append("- 位置坐标为像素坐标系")
            lines.append("- 纯文本内容按图像位置从上到下、从左到右排序")
            lines.append("="*60)
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"❌ 格式化TXT结果失败: {e}", exc_info=True)
            # 返回简化版本
            return f"PaddleOCR识别结果\n图像: {Path(image_path).name}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n格式化失败: {str(e)}"
        
    # --- Fallback & Mocking ---
    def _mock_recognition_result(self, error: str = "Unknown error") -> Dict[str, Any]:
        """在OCR失败时返回一个模拟的、结构一致的结果。"""
        logger.warning(f"Using mock OCR result due to error: {error}")
        mock_data = self._mock_raw_paddle_result()
        result = self._process_ocr_result(mock_data)
        result["mock_mode"] = True
        result["engine_status"] = "模拟模式（错误恢复）"
        result["error"] = error
        result["texts"] = []
        result["success"] = False  # 明确标记为失败
        return result

    def _mock_raw_paddle_result(self) -> List[List]:
        """生成模拟的PaddleOCR原始输出。"""
        return [
            [[[10, 10], [100, 10], [100, 30], [10, 30]], ('KZ-1 300x600', 0.95)],
            [[[10, 40], [120, 40], [120, 60], [10, 60]], ('B=200 H=400', 0.92)]
        ]

    # --- Data Persistence ---
    def _save_complete_raw_result_to_sealos(self, raw_paddle_data: List[List], ocr_result: Dict[str, Any], image_path: str, drawing_id: str = None) -> Dict[str, Any]:
        """
        构建包含完整OCR原始数据的JSON和TXT，并上传到S3/Sealos。
        
        Args:
            raw_paddle_data: PaddleOCR原始输出数据
            ocr_result: 处理后的OCR结果
            image_path: 图像文件路径
            drawing_id: 图纸ID，用于分类存储（可选）
        """
        storage_service = self.dual_storage
        if not storage_service:
            logger.warning("存储服务不可用，无法保存原始OCR结果")
            return {"saved": False, "error": "Storage service not available"}

        try:
            # 🔧 修复：生成唯一的file_id
            import uuid
            import time
            from pathlib import Path
            
            # 基于图像文件名和时间戳生成唯一ID
            image_name = Path(image_path).stem  # 去除扩展名的文件名
            timestamp = int(time.time())
            file_id = f"ocr_{image_name}_{timestamp}_{str(uuid.uuid4())[:8]}"
            
            # 准备数据和文件名
            json_filename = f"{file_id}.json"
            txt_filename = f"{file_id}.txt"
            image_filename = f"{file_id}{Path(image_path).suffix}"
            folder_path = f"ocr_results/{drawing_id}"

            # 1. 保存JSON结果
            json_data = json.dumps(ocr_result, ensure_ascii=False, indent=2).encode('utf-8')
            json_s3_key = f"{folder_path}/{json_filename}"
            json_upload_result = storage_service.upload_file_sync(
                file_obj=BytesIO(json_data),
                s3_key=json_s3_key,
                content_type="application/json"
            )
            
            # 2. 保存TXT格式的原始识别结果
            txt_content = self._format_raw_result_as_txt(raw_paddle_data, image_path)
            txt_s3_key = f"{folder_path}/{txt_filename}"
            txt_upload_result = storage_service.upload_file_sync(
                file_obj=BytesIO(txt_content.encode('utf-8')),
                s3_key=txt_s3_key,
                content_type="text/plain"
            )

            # 3. 保存原始图片
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_s3_key = f"{folder_path}/{image_filename}"
            image_upload_result = storage_service.upload_file_sync(
                file_obj=BytesIO(image_data),
                s3_key=image_s3_key,
                content_type="image/png" # 假设为png，或从路径推断
            )

            final_result = {
                "saved": True,
                "json_result": {
                    "s3_key": json_s3_key,
                    "s3_url": json_upload_result.get("final_url"),
                    "bucket": json_upload_result.get("bucket")
                },
                "txt_result": {
                    "s3_key": txt_s3_key,
                    "s3_url": txt_upload_result.get("final_url"),
                    "bucket": txt_upload_result.get("bucket")
                },
                "image_result": {
                    "s3_key": image_s3_key,
                    "s3_url": image_upload_result.get("final_url"),
                    "bucket": image_upload_result.get("bucket")
                },
                "error": None
            }

            return final_result

        except Exception as e:
            logger.error(f"Failed to upload raw OCR data to Sealos: {e}")
            return {"saved": False, "error": str(e)}

    def recognize_text_from_image_obj(self, image_data: bytes, save_to_storage: bool = False, drawing_id: str = None) -> Dict[str, Any]:
        """从内存中的图像数据执行OCR"""
        # ... existing code ...
        # This method needs to be implemented
        # ... existing code ...

# Make sure this file can be imported and initialized without errors.
# logger.info("PaddleOCR Service module loaded.") 