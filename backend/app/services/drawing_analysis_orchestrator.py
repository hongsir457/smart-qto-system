#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸分析编排器
集成多种分析方法：传统OCR、智能切片、上下文链分析等
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DrawingAnalysisOrchestrator:
    """图纸分析编排器"""
    
    def __init__(self):
        """初始化分析编排器"""
        self.analysis_methods = {}
        self._initialize_analyzers()
    
    def _initialize_analyzers(self):
        """初始化各种分析器"""
        try:
            # 传统OCR分析器
            from app.services.unified_ocr_engine import UnifiedOCREngine
            self.analysis_methods['traditional_ocr'] = UnifiedOCREngine()
            logger.info("✅ 传统OCR分析器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 传统OCR分析器初始化失败: {e}")
        
        try:
            # AI分析器
            from app.services.ai_analyzer import AIAnalyzerService
            self.analysis_methods['ai_vision'] = AIAnalyzerService()
            logger.info("✅ AI Vision分析器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ AI Vision分析器初始化失败: {e}")
        
        try:
            # 网格切片分析器
            from app.services.grid_slice_analyzer import GridSliceAnalyzer
            self.analysis_methods['grid_slice'] = GridSliceAnalyzer()
            logger.info("✅ 网格切片分析器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 网格切片分析器初始化失败: {e}")
        
        try:
            # 上下文链分析器
            from app.services.contextual_slice_analyzer import ContextualSliceAnalyzer
            self.analysis_methods['contextual_slice'] = ContextualSliceAnalyzer()
            logger.info("✅ 上下文链分析器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 上下文链分析器初始化失败: {e}")
        
        try:
            # 双轨协同分析器
            from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
            self.analysis_methods['dual_track'] = EnhancedGridSliceAnalyzer()
            logger.info("✅ 双轨协同分析器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 双轨协同分析器初始化失败: {e}")
    
    def analyze_drawing(self, 
                       drawing_info: Dict[str, Any],
                       task_id: str,
                       preferred_method: str = "auto") -> Dict[str, Any]:
        """
        智能选择最佳分析方法进行图纸分析
        
        Args:
            drawing_info: 图纸信息
            task_id: 任务ID
            preferred_method: 偏好的分析方法 (auto/traditional_ocr/ai_vision/grid_slice/contextual_slice/dual_track)
            
        Returns:
            分析结果
        """
        logger.info(f"🚀 开始图纸分析编排 - 任务ID: {task_id}")
        
        try:
            # 分析图纸特征
            analysis_strategy = self._determine_analysis_strategy(
                drawing_info, preferred_method
            )
            
            logger.info(f"📋 选择的分析策略: {analysis_strategy['method']} - {analysis_strategy['reason']}")
            
            # 执行分析
            start_time = time.time()
            
            if analysis_strategy['method'] == 'grid_slice':
                result = self._execute_grid_slice_analysis(drawing_info, task_id)
                
            elif analysis_strategy['method'] == 'contextual_slice':
                result = self._execute_contextual_slice_analysis(drawing_info, task_id)
                
            elif analysis_strategy['method'] == 'ai_vision':
                result = self._execute_ai_vision_analysis(drawing_info, task_id)
                
            elif analysis_strategy['method'] == 'traditional_ocr':
                result = self._execute_traditional_ocr_analysis(drawing_info, task_id)
                
            elif analysis_strategy['method'] == 'dual_track':
                result = self._execute_dual_track_analysis(drawing_info, task_id)
                
            elif analysis_strategy['method'] == 'hybrid':
                result = self._execute_hybrid_analysis(drawing_info, task_id)
                
            else:
                return {
                    "success": False,
                    "error": f"不支持的分析方法: {analysis_strategy['method']}"
                }
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # 补充分析元数据
            if result.get("success"):
                result["analysis_metadata"] = {
                    "method_used": analysis_strategy['method'],
                    "selection_reason": analysis_strategy['reason'],
                    "execution_time": elapsed,
                    "task_id": task_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                logger.info(f"✅ 图纸分析完成 - 方法: {analysis_strategy['method']}, 耗时: {elapsed:.2f}s")
            else:
                logger.error(f"❌ 图纸分析失败 - {result.get('error', '未知错误')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 图纸分析编排失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "orchestrator_error"
            }
    
    def _determine_analysis_strategy(self, 
                                   drawing_info: Dict[str, Any],
                                   preferred_method: str) -> Dict[str, str]:
        """
        简化分析策略选择：固定使用双轨协同分析
        """
        
        # 如果用户明确指定了其他方法，仍然尊重用户选择
        if preferred_method != "auto" and preferred_method in self.analysis_methods:
            return {
                "method": preferred_method,
                "reason": "用户明确指定方法"
            }
        
        # 默认始终使用双轨协同分析
        if 'dual_track' in self.analysis_methods:
            return {
                "method": "dual_track",
                "reason": "系统默认使用双轨协同分析（OCR+Vision最佳精度）"
            }
        
        # 如果双轨协同不可用，降级到可用方法
        fallback_order = ['ai_vision', 'grid_slice', 'contextual_slice', 'traditional_ocr']
        for method in fallback_order:
            if method in self.analysis_methods:
                return {
                    "method": method,
                    "reason": f"双轨协同不可用，降级使用 {method}"
                }
        
        return {
            "method": "none",
            "reason": "没有可用的分析方法"
        }
    
    def _calculate_complexity_score(self, 
                                  file_size: int,
                                  width: int, 
                                  height: int,
                                  file_type: str) -> float:
        """计算图纸复杂度评分（0-10分）"""
        
        score = 0.0
        
        # 尺寸评分 (0-4分)
        pixel_count = width * height
        if pixel_count > 50_000_000:  # >50MP
            score += 4.0
        elif pixel_count > 20_000_000:  # >20MP
            score += 3.0
        elif pixel_count > 8_000_000:   # >8MP
            score += 2.0
        elif pixel_count > 2_000_000:   # >2MP
            score += 1.0
        
        # 文件大小评分 (0-3分)
        size_mb = file_size / (1024 * 1024)
        if size_mb > 50:
            score += 3.0
        elif size_mb > 20:
            score += 2.0
        elif size_mb > 5:
            score += 1.0
        
        # 文件类型评分 (0-2分)
        if file_type in ['dwg', 'dxf']:
            score += 2.0  # CAD文件通常更复杂
        elif file_type in ['pdf']:
            score += 1.5  # PDF可能包含矢量信息
        elif file_type in ['tiff', 'tif']:
            score += 1.0  # 高质量扫描件
        
        # 长宽比评分 (0-1分)
        if width > 0 and height > 0:
            aspect_ratio = max(width/height, height/width)
            if aspect_ratio > 3.0:  # 极端长宽比，可能是长条图纸
                score += 1.0
        
        return min(score, 10.0)  # 限制在10分以内
    
    def _execute_grid_slice_analysis(self, 
                                   drawing_info: Dict[str, Any],
                                   task_id: str) -> Dict[str, Any]:
        """执行网格切片分析"""
        
        try:
            analyzer = self.analysis_methods['grid_slice']
            
            # 根据图纸尺寸调整切片参数
            image_dims = drawing_info.get("image_dimensions", {})
            width = image_dims.get("width", 4096)
            height = image_dims.get("height", 4096)
            
            # 动态调整切片大小
            if width > 8192 or height > 8192:
                analyzer.slice_size = 2048  # 大图用2K切片
                analyzer.overlap = 256
            elif width > 4096 or height > 4096:
                analyzer.slice_size = 1024  # 中图用1K切片
                analyzer.overlap = 128
            else:
                analyzer.slice_size = 512   # 小图用512切片
                analyzer.overlap = 64
            
            logger.info(f"📐 网格切片参数: {analyzer.slice_size}x{analyzer.slice_size}, 重叠: {analyzer.overlap}")
            
            result = analyzer.analyze_drawing_with_grid_slicing(
                image_path=drawing_info["image_path"],
                drawing_info=drawing_info,
                task_id=task_id,
                output_dir=f"temp_slices_{task_id}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 网格切片分析执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "grid_slice"
            }
    
    def _execute_contextual_slice_analysis(self, 
                                         drawing_info: Dict[str, Any],
                                         task_id: str) -> Dict[str, Any]:
        """执行上下文链切片分析"""
        
        try:
            analyzer = self.analysis_methods['contextual_slice']
            
            result = analyzer.analyze_with_contextual_slicing(
                drawing_info=drawing_info,
                task_id=task_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 上下文链分析执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "contextual_slice"
            }
    
    def _execute_ai_vision_analysis(self, 
                                  drawing_info: Dict[str, Any],  
                                  task_id: str) -> Dict[str, Any]:
        """执行AI Vision分析"""
        
        try:
            analyzer = self.analysis_methods['ai_vision']
            
            if not analyzer.is_available():
                return {
                    "success": False,
                    "error": "AI Vision分析器不可用",
                    "analysis_method": "ai_vision"
                }
            
            result = analyzer.analyze_drawing_complete(
                drawing_info=drawing_info,
                task_id=task_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ AI Vision分析执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "ai_vision"
            }
    
    def _execute_traditional_ocr_analysis(self, 
                                        drawing_info: Dict[str, Any],
                                        task_id: str) -> Dict[str, Any]:
        """执行传统OCR分析"""
        
        try:
            analyzer = self.analysis_methods['traditional_ocr']
            
            result = analyzer.process_document(
                file_path=drawing_info["image_path"],
                drawing_id=task_id,
                options={"include_text_merge": True}
            )
            
            # 转换为统一格式
            if result.get("success"):
                return {
                    "success": True,
                    "analysis_method": "traditional_ocr",
                    "qto_data": {
                        "drawing_info": drawing_info,
                        "ocr_results": result.get("results", {}),
                        "component_summary": {
                            "total_components": 0,  # OCR不直接识别构件
                            "component_types": [],
                            "text_blocks": len(result.get("results", {}).get("paddle_ocr", {}).get("texts", []))
                        }
                    }
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"❌ 传统OCR分析执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "traditional_ocr"
            }
    
    def _execute_dual_track_analysis(self, 
                                   drawing_info: Dict[str, Any],
                                   task_id: str) -> Dict[str, Any]:
        """执行双轨协同分析（OCR + Vision）"""
        
        try:
            analyzer = self.analysis_methods['dual_track']
            
            # 根据图纸尺寸调整切片参数（与网格分析类似）
            image_dims = drawing_info.get("image_dimensions", {})
            width = image_dims.get("width", 4096)
            height = image_dims.get("height", 4096)
            
            # 动态调整切片大小
            if width > 8192 or height > 8192:
                analyzer.slice_size = 2048  # 大图用2K切片
                analyzer.overlap = 256
            elif width > 4096 or height > 4096:
                analyzer.slice_size = 1024  # 中图用1K切片
                analyzer.overlap = 128
            else:
                analyzer.slice_size = 512   # 小图用512切片
                analyzer.overlap = 64
            
            logger.info(f"🔄 双轨协同参数: {analyzer.slice_size}x{analyzer.slice_size}, 重叠: {analyzer.overlap}")
            
            result = analyzer.analyze_drawing_with_dual_track(
                image_path=drawing_info["image_path"],
                drawing_info=drawing_info,
                task_id=task_id,
                output_dir=f"temp_dual_track_{task_id}"
            )
            
            if result.get("success"):
                logger.info(f"✅ 双轨协同分析完成")
            else:
                logger.error(f"❌ 双轨协同分析失败: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 双轨协同分析执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "dual_track"
            }
    
    def _execute_hybrid_analysis(self, 
                               drawing_info: Dict[str, Any],
                               task_id: str) -> Dict[str, Any]:
        """执行混合分析（多方法结合）"""
        
        logger.info("🔀 执行混合分析策略")
        
        results = {}
        final_result = {
            "success": False,
            "analysis_method": "hybrid",
            "sub_results": {},
            "error": "所有分析方法都失败"
        }
        
        # 按优先级尝试多种方法
        methods_to_try = ['ai_vision', 'grid_slice', 'traditional_ocr']
        
        for method in methods_to_try:
            if method not in self.analysis_methods:
                continue
            
            logger.info(f"🔍 尝试 {method} 分析...")
            
            try:
                if method == 'ai_vision':
                    result = self._execute_ai_vision_analysis(drawing_info, f"{task_id}_{method}")
                elif method == 'grid_slice':
                    result = self._execute_grid_slice_analysis(drawing_info, f"{task_id}_{method}")
                elif method == 'traditional_ocr':
                    result = self._execute_traditional_ocr_analysis(drawing_info, f"{task_id}_{method}")
                
                results[method] = result
                
                if result.get("success"):
                    logger.info(f"✅ {method} 分析成功")
                    final_result = result
                    final_result["analysis_method"] = "hybrid"
                    final_result["primary_method"] = method
                    break
                else:
                    logger.warning(f"⚠️ {method} 分析失败: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ {method} 分析异常: {e}")
                results[method] = {
                    "success": False,
                    "error": str(e),
                    "analysis_method": method
                }
        
        final_result["sub_results"] = results
        
        if final_result.get("success"):
            logger.info(f"✅ 混合分析成功 - 主要方法: {final_result.get('primary_method')}")
        else:
            logger.error("❌ 混合分析失败 - 所有方法都失败")
        
        return final_result
    
    def get_available_methods(self) -> List[str]:
        """获取可用的分析方法列表"""
        return list(self.analysis_methods.keys())
    
    def get_method_info(self) -> Dict[str, Dict[str, str]]:
        """获取分析方法详细信息"""
        return {
            "traditional_ocr": {
                "name": "传统OCR分析",
                "description": "使用OCR技术提取文字信息",
                "适用场景": "文字密集型图纸、简单标注提取",
                "优势": "快速、准确提取文字"
            },
            "ai_vision": {
                "name": "AI视觉分析",
                "description": "使用AI模型直接分析图像内容",
                "适用场景": "复杂图纸、构件类型识别",
                "优势": "理解图像语义、识别复杂构件"
            },
            "grid_slice": {
                "name": "网格切片分析",
                "description": "将大图分割为网格进行分析",
                "适用场景": "超大尺寸图纸、高精度分析",
                "优势": "处理大图、精确定位"
            },
            "contextual_slice": {
                "name": "上下文链分析",
                "description": "带上下文的切片分析",
                "适用场景": "复杂图纸、需要全局信息",
                "优势": "保持上下文一致性"
            },
            "dual_track": {
                "name": "双轨协同分析",
                "description": "OCR与Vision协同分析",
                "适用场景": "高精度要求、复杂工程图纸",
                "优势": "文字精准+语义理解、互补增强"
            },
            "hybrid": {
                "name": "混合分析",
                "description": "结合多种分析方法",
                "适用场景": "复杂多样的图纸类型",
                "优势": "综合优势、降级处理"
            }
        }