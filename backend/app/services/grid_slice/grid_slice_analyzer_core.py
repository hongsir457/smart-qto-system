#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格切片分析器核心模块
负责分析器的主要逻辑和协调功能
"""

import os
import json
import logging
import time
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

# 导入优化工具
from app.utils.analysis_optimizations import (
    OCRCacheManager, CoordinateTransformService, GPTResponseParser, 
    AnalysisLogger, AnalysisMetadata, CoordinatePoint, ocr_cache_manager
)
from app.core.config import AnalysisSettings

logger = logging.getLogger(__name__)

@dataclass
class OCRTextItem:
    """OCR文本项"""
    text: str
    position: List[List[int]]  # 四个角点坐标
    confidence: float
    category: str = "unknown"  # 分类：component_id, dimension, material, axis, etc.
    bbox: Optional[Dict[str, int]] = None  # 标准化边界框

@dataclass
class EnhancedSliceInfo:
    """增强切片信息（包含OCR结果）"""
    filename: str
    row: int
    col: int
    x_offset: int
    y_offset: int
    source_page: int
    width: int
    height: int
    slice_path: str
    ocr_results: List[OCRTextItem] = None
    enhanced_prompt: str = ""

class GridSliceAnalyzerCore:
    """网格切片分析器核心类"""
    
    def __init__(self, slice_size: int = 1024, overlap: int = 128):
        """初始化核心分析器"""
        self.slice_size = slice_size
        self.overlap = overlap
        
        # 使用全局OCR缓存管理器
        self.ocr_cache = ocr_cache_manager
        
        # 坐标转换服务（延迟初始化）
        self.coordinate_service = None
        
        # 初始化各种分析器
        self.ai_analyzer = None
        self.ocr_engine = None
        
        try:
            from app.services.ai import AIAnalyzerService
            self.ai_analyzer = AIAnalyzerService()
        except Exception as e:
            logger.warning(f"⚠️ AI分析器初始化失败: {e}")
        
        try:
            from app.services.ocr.paddle_ocr import PaddleOCRService
            self.ocr_engine = PaddleOCRService()
        except Exception as e:
            logger.warning(f"⚠️ OCR引擎初始化失败: {e}")
        
        # 构件识别规则
        self.component_patterns = {
            'component_id': [
                r'^[A-Z]{1,2}\d{2,4}$',  # B101, KZ01, GL201
                r'^[A-Z]{1,2}-\d{1,3}$', # B-1, KZ-12
                r'^\d{1,3}[A-Z]{1,2}$'   # 1B, 12KZ
            ],
            'dimension': [
                r'^\d{2,4}[xX×]\d{2,4}$',        # 300x600
                r'^\d{2,4}[xX×]\d{2,4}[xX×]\d{2,4}$', # 300x600x800
                r'^[bBhH]?\d{2,4}$'              # b300, h600, 200
            ],
            'material': [
                r'^C\d{2}$',           # C30, C25
                r'^HRB\d{3}$',         # HRB400
                r'^MU\d{1,2}$',        # MU10
                r'^Q\d{3}$'            # Q235
            ],
            'axis': [
                r'^[A-Z]-[A-Z]$',               # A-B
                r'^\d+-\d+$',                   # 1-2
                r'^轴线\s*[A-Z0-9\-/]+$',       # 轴线A-B
                r'^[A-Z]\d*/[A-Z]\d*$'          # A1/B2
            ]
        }
        
        # 存储分析结果
        self.enhanced_slices: List[EnhancedSliceInfo] = []
        self.slice_components: Dict[str, List] = {}
        self.merged_components: List = []
        
        # Vision结果缓存机制
        self._vision_cache: Dict[str, List] = {}
        
        # 存储全图OCR概览信息
        self.global_drawing_overview: Dict[str, Any] = {}

    def reset_batch_state(self):
        """重置批次状态（用于实例复用）"""
        self.enhanced_slices = []
        self.slice_components = {}
        self.merged_components = []
        self.coordinate_service = None
        # 不重置全图概览和OCR缓存，这些可以跨批次复用

    def _initialize_coordinate_service(self, slice_coordinate_map: Dict[str, Any], original_image_info: Dict[str, Any]):
        """初始化坐标转换服务"""
        if not self.coordinate_service:
            self.coordinate_service = CoordinateTransformService(slice_coordinate_map, original_image_info)

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
            
            # Step 1: 复用智能切片结果（委托给OCR处理器）
            logger.info("📐 Step 1: 复用智能切片结果")
            from .grid_slice_ocr_processor import GridSliceOCRProcessor
            ocr_processor = GridSliceOCRProcessor(self)
            
            if not ocr_processor.can_reuse_shared_slices(shared_slice_results, image_path):
                error_msg = f"无法复用共享切片结果，请检查切片数据完整性"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            slice_result = ocr_processor.reuse_shared_slices(shared_slice_results, image_path, drawing_info)
            if not slice_result["success"]:
                error_msg = f"智能切片复用失败: {slice_result.get('error', '未知错误')}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            metadata.slice_count = slice_result.get('slice_count', 0)
            logger.info(f"✅ 成功复用 {metadata.slice_count} 个智能切片")
            
            # 初始化坐标转换服务
            if 'slice_coordinate_map' in slice_result and 'original_image_info' in slice_result:
                self._initialize_coordinate_service(
                    slice_result['slice_coordinate_map'], 
                    slice_result['original_image_info']
                )
                        
            # Step 2: OCR结果处理（严格复用已有结果，不重复处理）
            logger.info("♻️ Step 2: 严格复用已有OCR结果")
            try:
                ocr_result = ocr_processor.load_shared_ocr_results(shared_slice_results, image_path)
                metadata.ocr_cache_used = True
            except Exception as e:
                # 报错退出，不降级处理
                error_msg = f"无法加载共享OCR结果: {e}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            logger.info(f"✅ OCR结果复用完成，发现 {len(self.enhanced_slices)} 个增强切片")
            
            # Step 3: 增强Vision分析（基于OCR结果）
            logger.info("🔍 Step 3: 增强Vision分析")
            from .grid_slice_vision_analyzer import GridSliceVisionAnalyzer
            vision_analyzer = GridSliceVisionAnalyzer(self)
            vision_result = vision_analyzer.analyze_slices_with_enhanced_vision(drawing_info, task_id)
            if not vision_result["success"]:
                logger.warning(f"⚠️ Vision分析失败: {vision_result.get('error', '未知错误')}")
                # Vision分析失败不影响整体流程，但会记录警告
            
            # Step 4: 结果合并和坐标还原
            logger.info("🔄 Step 4: 双轨结果合并")
            from .grid_slice_result_merger import GridSliceResultMerger
            result_merger = GridSliceResultMerger(self)
            merge_result = result_merger.merge_dual_track_results()
            if not merge_result["success"]:
                logger.warning(f"⚠️ 结果合并失败: {merge_result.get('error', '未知错误')}")
            
            # Step 5: 生成OCR识别显示块
            logger.info("📊 Step 5: 生成OCR识别显示")
            ocr_display = self._generate_ocr_recognition_display()
            
            # Step 6: 生成工程量清单显示
            logger.info("📋 Step 6: 生成工程量清单显示")
            quantity_display = result_merger.generate_quantity_list_display()
            
            # 计算处理时间
            processing_time = time.time() - start_time
            metadata.success = True
            
            logger.info(f"✅ 双轨协同分析完成，耗时: {processing_time:.2f}秒")
            
            return {
                "success": True,
                "components": self.merged_components,
                "metadata": asdict(metadata),
                "processing_time": processing_time,
                "analysis_method": "dual_track_enhanced",
                "ocr_recognition_display": ocr_display,
                "quantity_list_display": quantity_display,
                "slice_count": len(self.enhanced_slices),
                "component_count": len(self.merged_components)
            }
            
        except Exception as e:
            logger.error(f"❌ 双轨协同分析失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "components": [],
                "metadata": asdict(metadata)
            }

    def get_status(self) -> Dict[str, Any]:
        """获取分析器状态"""
        return {
            'version': 'GridSliceAnalyzerCore v2.0.0',
            'slice_size': self.slice_size,
            'overlap': self.overlap,
            'ai_analyzer_available': self.ai_analyzer is not None,
            'ocr_engine_available': self.ocr_engine is not None,
            'coordinate_service_initialized': self.coordinate_service is not None,
            'enhanced_slices_count': len(self.enhanced_slices),
            'merged_components_count': len(self.merged_components),
            'vision_cache_size': len(self._vision_cache),
            'has_global_overview': bool(self.global_drawing_overview)
        }

    def cleanup(self):
        """清理资源"""
        self.enhanced_slices = []
        self.slice_components = {}
        self.merged_components = []
        self._vision_cache = {}
        if self.coordinate_service:
            self.coordinate_service = None

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