#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版网格切片分析器
实现 OCR + Vision 双轨协同分析架构
"""

import os
import json
import logging
import time
import math
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import cv2
import numpy as np

# 导入优化工具
from app.utils.analysis_optimizations import (
    OCRCacheManager, CoordinateTransformService, GPTResponseParser, 
    AnalysisLogger, AnalysisMetadata, CoordinatePoint, ocr_cache_manager
)
from app.core.config import AnalysisSettings

logger = logging.getLogger(__name__)

from .enhanced_slice_models import OCRTextItem, EnhancedSliceInfo
from .ocr_enhancement import OCREnhancer
from .vision_analysis_manager import VisionAnalysisManager as VisionAnalyzer
from .fusion_manager import FusionManager as DualTrackFusion
from .quantity_display_manager import QuantityDisplayManager as QuantityListDisplay
from .utils import extract_dimension_value

from .analyzer_parts.reuse_handler import ReuseHandler
from .analyzer_parts.coordinate_handler import CoordinateHandler
from .analyzer_parts.prompt_handler import PromptHandler
from .analyzer_parts.result_handler import ResultHandler
from .analyzer_parts.ocr_handler import OCRHandler


class EnhancedGridSliceAnalyzer:
    """增强版网格切片分析器（OCR+Vision协同）"""
    
    def __init__(self, slice_size: int = 1024, overlap: int = 128):
        """初始化增强分析器"""
        self.slice_size = slice_size
        self.overlap = overlap
        self.ocr_enhancer = OCREnhancer(self._default_component_patterns())
        self.vision_analyzer = VisionAnalyzer()
        self.fusion = DualTrackFusion()
        self.quantity_display = QuantityListDisplay()
        
        # 初始化各个处理器模块
        self.reuse_handler = ReuseHandler()
        self.coordinate_handler = CoordinateHandler()
        self.prompt_handler = PromptHandler()
        self.result_handler = ResultHandler()
        self.ocr_handler = OCRHandler()
        
        self.enhanced_slices = []
        self.slice_components = {}
        self.merged_components = []
        self.coordinate_service = None
        
        # 使用全局OCR缓存管理器
        self.ocr_cache = ocr_cache_manager
        
        # 初始化各种分析器
        self.ai_analyzer = None
        self.ocr_engine = None
        
        try:
            from app.services.ai_analyzer import AIAnalyzerService
            self.ai_analyzer = AIAnalyzerService()
        except Exception as e:
            logger.warning(f"⚠️ AI分析器初始化失败: {e}")
        
        try:
            from app.services.ocr.paddle_ocr import PaddleOCRService
            self.ocr_engine = PaddleOCRService()
        except Exception as e:
            logger.warning(f"⚠️ OCR引擎初始化失败: {e}")
        
        # 存储分析结果
        self.global_drawing_overview: Dict[str, Any] = {}

    def reset_batch_state(self):
        """重置批次状态（用于实例复用）"""
        self.enhanced_slices = []
        self.slice_components = {}
        self.merged_components = []
        self.coordinate_service = None
        # 不重置全图概览和OCR缓存，这些可以跨批次复用

    def analyze_drawing_with_dual_track(self, 
                                      image_path: str,
                                      drawing_info: Dict[str, Any],
                                      task_id: str,
                                      output_dir: str = "temp_slices",
                                      shared_slice_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行双轨协同分析（OCR + Vision）- 严格要求共享切片结果"""
        start_time = time.time()
        metadata = AnalysisMetadata(
            analysis_method="dual_track_analysis",
            batch_id=drawing_info.get('batch_id', 1),
            slice_count=0,
            success=False
        )
        
        logger.info(f"🚀 开始双轨协同分析: {image_path}")
        
        # 启动OpenAI交互记录会话（用于API调用记录）
        if hasattr(self, 'ai_analyzer') and self.ai_analyzer and hasattr(self.ai_analyzer, 'interaction_logger'):
            try:
                session_id = self.ai_analyzer.interaction_logger.start_session(
                    task_id=task_id,
                    drawing_id=drawing_info.get('drawing_id', 0),
                    session_type="dual_track_vision_analysis"
                )
                logger.info(f"🔄 双轨协同分析会话开始: {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ 交互记录会话启动失败: {e}")
        
        try:
            # 严格检查共享切片结果
            if not shared_slice_results:
                error_msg = "双轨协同分析要求必须提供shared_slice_results参数"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            if not self.reuse_handler.can_reuse_shared_slices(shared_slice_results, image_path):
                error_msg = f"无法复用共享切片结果，请检查切片数据完整性"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Step 1: 复用智能切片结果（必须成功）
            logger.info("📐 Step 1: 复用智能切片结果")
            slice_result = self.reuse_handler.reuse_shared_slices(shared_slice_results, image_path, drawing_info)
            if not slice_result["success"]:
                error_msg = f"智能切片复用失败: {slice_result.get('error', '未知错误')}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            metadata.slice_count = slice_result.get('slice_count', 0)
            logger.info(f"✅ 成功复用 {metadata.slice_count} 个智能切片")
            
            # 关键修复：确保每次调用都重新初始化坐标服务
            if 'slice_coordinate_map' in slice_result and 'original_image_info' in slice_result:
                self.coordinate_handler.initialize_coordinate_service(
                    slice_result['slice_coordinate_map'], 
                    slice_result['original_image_info']
                )
                logger.info("✅ 坐标转换服务已使用当前任务数据进行初始化")
            else:
                error_msg = "复用的切片结果中缺少坐标映射或原始图像信息"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
                        
            # Step 2: OCR结果处理（严格复用已有结果，不重复处理）
            logger.info("♻️ Step 2: 严格复用已有OCR结果")
            try:
                ocr_result = self.reuse_handler.load_shared_ocr_results(shared_slice_results, image_path)
                metadata.ocr_cache_used = True
            except Exception as e:
                error_msg = f"无法加载共享OCR结果: {e}"
                logger.error(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            if not ocr_result["success"]:
                error_msg = f"OCR文本提取失败: {ocr_result.get('error', '未知错误')}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Step 2.5: 汇总OCR结果并进行全图概览分析（使用优化的解析器）
            logger.info("🔍 Step 2.5: 汇总OCR结果并进行全图概览分析")
            global_overview_result = self.ocr_handler.extract_global_ocr_overview_optimized(self, self.enhanced_slices, drawing_info, task_id)
            if not global_overview_result["success"]:
                logger.warning(f"⚠️ 全图OCR概览失败，继续使用基础信息: {global_overview_result.get('error')}")
                self.global_drawing_overview = {}
            else:
                self.global_drawing_overview = global_overview_result["overview"]
                logger.info(f"✅ 全图概览完成: {len(self.global_drawing_overview.get('component_ids', []))} 个构件编号")
                
                # 保存轨道1结果到Sealos
                self._save_global_overview_to_sealos(drawing_info, task_id)
            
            # Step 3: OCR结果分类和增强提示生成
            logger.info("🧠 Step 3: OCR智能分类与提示增强")
            enhancement_result = self.ocr_enhancer.enhance_slices_with_ocr(self.enhanced_slices)
            if not enhancement_result["success"]:
                error_msg = f"OCR增强处理失败: {enhancement_result.get('error', '未知错误')}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Step 4: Vision分析（基于OCR增强提示）
            logger.info("👁️ Step 4: OCR引导的Vision分析")
            vision_result = self.vision_analyzer.analyze_slices(self.enhanced_slices, None, drawing_info, task_id)
            if not vision_result["success"]:
                error_msg = f"Vision分析失败: {vision_result.get('error', '未知错误')}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Step 5: 双轨结果融合与合并
            logger.info("🔀 Step 5: 双轨结果智能融合")
            fusion_result = self.fusion.merge_results(self.slice_components, self.global_drawing_overview, self.coordinate_service)
            if not fusion_result["success"]:
                error_msg = f"结果融合失败: {fusion_result.get('error', '未知错误')}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Step 6: 坐标还原与可视化
            logger.info("📎 Step 6: 坐标还原与可视化")
            restore_result = self.coordinate_handler.restore_global_coordinates(self, image_path)
            
            # 记录处理时间和成功状态
            metadata.processing_time = time.time() - start_time
            metadata.success = True
            
            # 记录分析元数据
            AnalysisLogger.log_analysis_metadata(metadata)
            
            # 构建最终结果
            final_result = {
                "success": True,
                "qto_data": {
                    "components": self.merged_components,
                    "drawing_info": self.global_drawing_overview.get('drawing_info', {}),
                    "quantity_summary": fusion_result.get("statistics", {}),
                    "analysis_metadata": asdict(metadata)
                },
                "ocr_recognition_display": self._generate_ocr_recognition_display(),
                "quantity_list_display": self.quantity_display.generate(self.merged_components),
                "processing_summary": {
                    "total_slices": len(self.enhanced_slices),
                    "total_components": len(self.merged_components),
                    "processing_time": metadata.processing_time,
                    "ocr_cache_hit_rate": self.ocr_cache.get_cache_stats(),
                    "coordinate_transforms": len(self.merged_components),
                    "success_rate": 1.0 if metadata.success else 0.0
                }
            }
            
            logger.info(f"✅ 双轨协同分析完成: {len(self.merged_components)} 个构件，耗时 {metadata.processing_time:.2f}s")
            return final_result
            
        except Exception as e:
            metadata.processing_time = time.time() - start_time
            metadata.error_message = str(e)
            AnalysisLogger.log_analysis_metadata(metadata)
            
            logger.error(f"❌ 双轨协同分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _generate_ocr_recognition_display(self) -> Dict[str, Any]:
        """生成OCR识别显示块"""
        return {
            "drawing_basic_info": self.global_drawing_overview.get("drawing_info", {}) if self.global_drawing_overview else {},
            "component_overview": {
                "component_ids": self.global_drawing_overview.get("component_ids", []) if self.global_drawing_overview else [],
                "component_types": self.global_drawing_overview.get("component_types", []) if self.global_drawing_overview else [],
                "material_grades": self.global_drawing_overview.get("material_grades", []) if self.global_drawing_overview else [],
                "axis_lines": self.global_drawing_overview.get("axis_lines", []) if self.global_drawing_overview else [],
                "summary": self.global_drawing_overview.get("summary", {}) if self.global_drawing_overview else {}
            },
            "ocr_source_info": {
                "total_slices": len(self.enhanced_slices),
                "analysis_method": "基于智能切片OCR汇总的GPT分析",
                "slice_reused": True
            }
        }

    def _save_global_overview_to_sealos(self, drawing_info: Dict[str, Any], task_id: str) -> Optional[str]:
        """
        保存轨道1的全图概览结果到Sealos
        
        Args:
            drawing_info: 图纸信息
            task_id: 任务ID
            
        Returns:
            保存的文件URL
        """
        try:
            from app.services.s3_service import S3Service
            import json
            import time
            from datetime import datetime
            
            if not self.global_drawing_overview:
                logger.warning("⚠️ 全图概览数据为空，跳过Sealos保存")
                return None
            
            s3_service = S3Service()
            
            # 构建保存数据
            save_data = {
                "metadata": {
                    "data_type": "global_drawing_overview",
                    "track": "track_1_ocr",
                    "task_id": task_id,
                    "drawing_id": drawing_info.get("drawing_id", "unknown"),
                    "drawing_name": drawing_info.get("drawing_name", "unknown"),
                    "save_time": datetime.now().isoformat(),
                    "analysis_method": "基于智能切片OCR汇总的GPT分析"
                },
                "drawing_overview": self.global_drawing_overview,
                "source_info": {
                    "total_slices": len(self.enhanced_slices),
                    "ocr_text_items": sum(len(slice_info.ocr_results) for slice_info in self.enhanced_slices if slice_info.ocr_results),
                    "component_count": len(self.global_drawing_overview.get("component_ids", [])),
                    "component_types_count": len(self.global_drawing_overview.get("component_types", [])),
                    "material_grades_count": len(self.global_drawing_overview.get("material_grades", []))
                },
                "data_integrity": {
                    "complete": True,
                    "openai_processed": True,
                    "structured_format": True
                }
            }
            
            # 生成文件名和路径
            timestamp = int(time.time())
            filename = f"global_overview_{task_id}_{timestamp}.json"
            folder = f"dual_track_results/{drawing_info.get('drawing_id', 'unknown')}/track_1_ocr"
            
            # 保存到Sealos
            json_content = json.dumps(save_data, ensure_ascii=False, indent=2)
            result = s3_service.upload_txt_content(
                content=json_content,
                file_name=filename,
                folder=folder
            )
            
            if result.get("success"):
                file_url = result.get("s3_url")
                logger.info(f"💾 轨道1全图概览已保存到Sealos: {file_url}")
                return file_url
            else:
                logger.error(f"❌ 轨道1全图概览保存失败: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 保存轨道1全图概览到Sealos失败: {e}")
            return None

    def _default_component_patterns(self):
        """默认构件模式"""
        return {
            'component_id': [r'^[A-Z]{1,2}\d{2,4}$', r'^[A-Z]{1,2}-\d{1,3}$', r'^\d{1,3}[A-Z]{1,2}$'],
            'dimension': [r'^\d{2,4}[xX×]\d{2,4}$', r'^\d{2,4}[xX×]\d{2,4}[xX×]\d{2,4}$', r'^[bBhH]?\d{2,4}$'],
            'material': [r'^C\d{2}$', r'^HRB\d{3}$', r'^MU\d{1,2}$', r'^Q\d{3}$'],
            'axis': [r'^[A-Z]-[A-Z]$', r'^\d+-\d+$', r'^轴线\s*[A-Z0-9\-/]+$', r'^[A-Z]\d*/[A-Z]\d*$']
        }
