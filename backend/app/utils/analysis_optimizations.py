#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析优化工具模块
包含：OCR缓存管理器、坐标转换服务、GPT响应解析器、分析日志记录器等
"""

import os
import json
import time
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# 获取日志记录器
logger = logging.getLogger(__name__)

@dataclass
class AnalysisMetadata:
    """统一的分析元数据结构"""
    analysis_method: str
    batch_id: int
    slice_count: int
    success: bool
    ocr_cache_used: bool = False
    processing_time: float = 0.0
    confidence_score: float = 0.0
    retry_count: int = 0
    error_message: str = ""

@dataclass
class CoordinatePoint:
    """坐标点数据结构"""
    x: float
    y: float
    slice_id: str = ""
    global_x: float = 0.0
    global_y: float = 0.0

class AnalysisSettings:
    """分析配置设置"""
    MAX_SLICES_PER_BATCH = 8
    OCR_CACHE_TTL = 3600  # 1小时
    COORDINATE_TRANSFORM_PRECISION = 2
    GPT_RESPONSE_MAX_RETRIES = 3
    OCR_CACHE_PRIORITY = ["global_cache", "shared_slice", "single_slice"]

class OCRCacheManager:
    """统一的OCR缓存管理器"""
    
    def __init__(self):
        self.global_cache: Dict[str, Any] = {}
        self.shared_slice_cache: Dict[str, Any] = {}
        self.single_slice_cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}
    
    def get_cached_ocr(self, slice_key: str, cache_type: str = "auto") -> Optional[Any]:
        """获取缓存的OCR结果（get_ocr_result的别名）"""
        return self.get_ocr_result(slice_key, cache_type)
    
    def get_ocr_result(self, slice_key: str, cache_type: str = "auto") -> Optional[Any]:
        """根据优先级获取OCR结果"""
        if cache_type == "auto":
            # 按优先级顺序检查
            for priority in AnalysisSettings.OCR_CACHE_PRIORITY:
                result = self._get_from_cache(slice_key, priority)
                if result:
                    AnalysisLogger.log_ocr_reuse(slice_key, len(result), priority)
                    return result
        else:
            return self._get_from_cache(slice_key, cache_type)
        return None
    
    def _get_from_cache(self, slice_key: str, cache_type: str) -> Optional[Any]:
        """从指定缓存类型获取结果"""
        cache_map = {
            "global_cache": self.global_cache,
            "shared_slice": self.shared_slice_cache,
            "single_slice": self.single_slice_cache
        }
        
        cache = cache_map.get(cache_type)
        if not cache:
            return None
            
        # 检查缓存过期
        timestamp = self.cache_timestamps.get(f"{cache_type}_{slice_key}", 0)
        if time.time() - timestamp > AnalysisSettings.OCR_CACHE_TTL:
            self._remove_from_cache(slice_key, cache_type)
            return None
            
        return cache.get(slice_key)
    
    def set_ocr_result(self, slice_key: str, result: Any, cache_type: str = "global_cache"):
        """设置OCR结果到指定缓存"""
        cache_map = {
            "global_cache": self.global_cache,
            "shared_slice": self.shared_slice_cache,
            "single_slice": self.single_slice_cache
        }
        
        cache = cache_map.get(cache_type)
        if cache is not None:
            cache[slice_key] = result
            self.cache_timestamps[f"{cache_type}_{slice_key}"] = time.time()
    
    def _remove_from_cache(self, slice_key: str, cache_type: str):
        """从缓存中移除过期数据"""
        cache_map = {
            "global_cache": self.global_cache,
            "shared_slice": self.shared_slice_cache,
            "single_slice": self.single_slice_cache
        }
        
        cache = cache_map.get(cache_type)
        if cache and slice_key in cache:
            del cache[slice_key]
        
        timestamp_key = f"{cache_type}_{slice_key}"
        if timestamp_key in self.cache_timestamps:
            del self.cache_timestamps[timestamp_key]
    
    def clear_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, timestamp in self.cache_timestamps.items():
            if current_time - timestamp > AnalysisSettings.OCR_CACHE_TTL:
                expired_keys.append(key)
        
        for key in expired_keys:
            cache_type, slice_key = key.split("_", 1)
            self._remove_from_cache(slice_key, cache_type)
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            "global_cache_size": len(self.global_cache),
            "shared_slice_cache_size": len(self.shared_slice_cache),
            "single_slice_cache_size": len(self.single_slice_cache),
            "total_timestamps": len(self.cache_timestamps)
        }

class CoordinateTransformService:
    """统一的坐标转换服务"""
    
    def __init__(self, slice_coordinate_map: Dict[str, Any], original_image_info: Dict[str, Any]):
        self.slice_map = slice_coordinate_map
        self.original_info = original_image_info
        self.precision = AnalysisSettings.COORDINATE_TRANSFORM_PRECISION
    
    def transform_to_global(self, slice_coord: CoordinatePoint, slice_id: str) -> CoordinatePoint:
        """将切片坐标转换为全图坐标"""
        slice_info = self.slice_map.get(slice_id)
        if not slice_info:
            logger.warning(f"未找到切片 {slice_id} 的坐标映射信息")
            return slice_coord
        
        # 计算全图坐标
        global_x = slice_coord.x + slice_info.get('x_offset', 0)
        global_y = slice_coord.y + slice_info.get('y_offset', 0)
        
        # 边界检查
        original_width = self.original_info.get('width', 0)
        original_height = self.original_info.get('height', 0)
        
        global_x = max(0, min(global_x, original_width))
        global_y = max(0, min(global_y, original_height))
        
        # 精度控制
        global_x = round(global_x, self.precision)
        global_y = round(global_y, self.precision)
        
        return CoordinatePoint(
            x=slice_coord.x,
            y=slice_coord.y,
            slice_id=slice_id,
            global_x=global_x,
            global_y=global_y
        )
    
    def transform_bbox_to_global(self, bbox: Dict[str, float], slice_id: str) -> Dict[str, float]:
        """转换边界框到全图坐标"""
        top_left = CoordinatePoint(x=bbox['x'], y=bbox['y'])
        bottom_right = CoordinatePoint(x=bbox['x'] + bbox['width'], y=bbox['y'] + bbox['height'])
        
        global_top_left = self.transform_to_global(top_left, slice_id)
        global_bottom_right = self.transform_to_global(bottom_right, slice_id)
        
        return {
            'x': global_top_left.global_x,
            'y': global_top_left.global_y,
            'width': global_bottom_right.global_x - global_top_left.global_x,
            'height': global_bottom_right.global_y - global_top_left.global_y
        }
    
    def batch_transform_coordinates(self, coordinates: List[Tuple[CoordinatePoint, str]]) -> List[CoordinatePoint]:
        """批量转换坐标"""
        results = []
        for coord, slice_id in coordinates:
            transformed = self.transform_to_global(coord, slice_id)
            results.append(transformed)
        return results

class GPTResponseParser:
    """统一的GPT响应解析器"""
    
    @staticmethod
    def extract_json_from_response(response_text: str) -> Dict[str, Any]:
        """从GPT响应中提取JSON数据"""
        try:
            # 清理响应文本
            cleaned_response = response_text.strip()
            
            # 如果响应包含```json标记，提取其中的JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
            if json_match:
                cleaned_response = json_match.group(1).strip()
            
            # 如果响应以```开头但没有json标记，去除```
            elif cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                if len(lines) > 1:
                    cleaned_response = '\n'.join(lines[1:-1]) if lines[-1].strip() == '```' else '\n'.join(lines[1:])
            
            # 尝试解析JSON
            return json.loads(cleaned_response)
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ GPT响应JSON解析失败: {e}")
            return GPTResponseParser._create_fallback_response()
    
    @staticmethod
    def _create_fallback_response() -> Dict[str, Any]:
        """创建降级响应"""
        return {
            "drawing_info": {
                "drawing_title": "未识别",
                "drawing_number": "未识别",
                "scale": "未识别",
                "project_name": "未识别",
                "drawing_type": "结构图纸"
            },
            "component_ids": [],
            "component_types": [],
            "material_grades": [],
            "axis_lines": [],
            "summary": {
                "total_components": 0,
                "main_structure_type": "未知",
                "complexity_level": "中等"
            }
        }
    
    @staticmethod
    def validate_json_structure(data: Dict[str, Any], required_fields: List[str]) -> bool:
        """验证JSON结构是否包含必需字段"""
        for field in required_fields:
            if field not in data:
                return False
        return True

class AnalysisLogger:
    """统一的分析日志记录器"""
    
    @staticmethod
    def log_step(step_name: str, details: str = "", step_number: int = None, total_steps: int = None, 
                 status: str = "info", task_id: str = ""):
        """记录分析步骤，支持多种参数格式"""
        # 智能emoji选择
        emoji_map = {
            "info": "🚀",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌",
            "ocr_extraction_optimized": "🔍",
            "ocr_extraction_completed": "📋",
            "global_ocr_overview": "🌍",
            "ocr_error": "💥"
        }
        
        emoji = emoji_map.get(status, "📌")
        
        # 构建消息
        message_parts = [emoji, "Step:", step_name]
        
        if step_number and total_steps:
            message_parts.extend([f"({step_number}/{total_steps})"])
        
        if details:
            message_parts.extend(["-", details])
        
        if task_id:
            message_parts.append(f"[Task: {task_id[:8]}...]")
        
        message = " ".join(message_parts)
        
        # 根据状态选择日志级别
        if status == "error":
            logger.error(message)
        elif status == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    @staticmethod
    def log_ocr_reuse(slice_key: str, count: int, source: str):
        """记录OCR复用情况"""
        logger.info(f"♻️ OCR复用: {slice_key} - {count}项 (来源: {source})")
    
    @staticmethod
    def log_batch_processing(batch_id: int, total_batches: int, slice_count: int):
        """记录批次处理情况"""
        logger.info(f"📦 批次处理: {batch_id}/{total_batches} - {slice_count}个切片")
    
    @staticmethod
    def log_coordinate_transform(transformed_count: int, total_count: int):
        """记录坐标转换情况"""
        logger.info(f"📐 坐标转换: {transformed_count}/{total_count}个坐标点")
    
    @staticmethod
    def log_cache_stats(stats: Dict[str, int]):
        """记录缓存统计信息"""
        logger.info(f"💾 缓存统计: {stats}")
    
    @staticmethod
    def log_analysis_metadata(metadata: AnalysisMetadata):
        """记录分析元数据"""
        logger.info(f"📊 分析元数据: {metadata.analysis_method} - 成功:{metadata.success}")
    
    @staticmethod
    def log_performance_metrics(operation_name: str, start_time: float, 
                              item_count: int = 0, success_count: int = 0):
        """记录性能指标"""
        duration = time.time() - start_time
        if item_count > 0:
            rate = item_count / duration if duration > 0 else 0
            success_rate = success_count / item_count if item_count > 0 else 0
            logger.info(f"⚡ {operation_name}: {duration:.2f}s, {rate:.1f}项/秒, 成功率{success_rate:.1%}")
        else:
            logger.info(f"⚡ {operation_name}: {duration:.2f}s")
    
    @staticmethod
    def log_error_with_context(error_msg: str, context: Dict[str, Any] = None, 
                              exception: Exception = None):
        """记录带上下文的错误信息"""
        message = f"❌ 错误: {error_msg}"
        if context:
            message += f" | 上下文: {context}"
        if exception:
            message += f" | 异常: {type(exception).__name__}: {exception}"
        logger.error(message)

class AnalyzerInstanceManager:
    """分析器实例管理器"""
    
    def __init__(self):
        self.instances: Dict[str, Any] = {}
        self.creation_times: Dict[str, float] = {}
        self.usage_counts: Dict[str, int] = {}
    
    def get_analyzer(self, analyzer_class):
        """获取分析器实例（复用或创建新实例）"""
        class_name = analyzer_class.__name__
        
        if class_name not in self.instances:
            self.instances[class_name] = self._create_new_analyzer(analyzer_class)
            self.creation_times[class_name] = time.time()
            self.usage_counts[class_name] = 0
        
        self.usage_counts[class_name] += 1
        AnalysisLogger.log_step(f"analyzer_reuse", f"{class_name} (使用次数: {self.usage_counts[class_name]})")
        
        return self.instances[class_name]
    
    def _create_new_analyzer(self, analyzer_class):
        """创建新的分析器实例"""
        return analyzer_class()
    
    def reset_for_new_batch(self):
        """为新批次重置实例管理器"""
        self.instances.clear()
        self.creation_times.clear()
        # 保留usage_counts用于统计
    
    def get_instance_stats(self) -> Dict[str, Any]:
        """获取实例统计信息"""
        return {
            "active_instances": len(self.instances),
            "usage_counts": self.usage_counts.copy(),
            "total_usages": sum(self.usage_counts.values())
        }

# 全局实例
ocr_cache_manager = OCRCacheManager()
analyzer_instance_manager = AnalyzerInstanceManager() 