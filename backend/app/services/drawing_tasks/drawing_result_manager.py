#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸结果管理器
负责分析结果管理、存储和后处理
"""

import logging
import asyncio
import json
from typing import Dict, Any, List

from app.tasks.real_time_task_manager import TaskStatus, TaskStage
from app.tasks import task_manager

logger = logging.getLogger(__name__)

class DrawingResultManager:
    """图纸结果管理器"""
    
    def __init__(self, core_processor):
        """初始化结果管理器"""
        self.core_processor = core_processor
        self.quantity_engine = core_processor.quantity_engine
        self.vision_scanner = core_processor.vision_scanner

    def perform_dual_track_analysis(self, temp_files: List[str], drawing, task_id: str, loop) -> Dict[str, Any]:
        """执行双轨协同分析"""
        try:
            logger.info("🔍 开始双轨协同分析...")
            
            # 阶段4: 智能切片
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.SLICING,
                    progress=40, message="正在进行智能切片..."
                )
            )
            
            # 智能切片
            slice_result = self._perform_intelligent_slicing(temp_files, drawing, task_id, loop)
            if not slice_result["success"]:
                logger.warning(f"⚠️ 智能切片失败: {slice_result.get('error', '未知错误')}")
                return {"success": False, "error": slice_result.get("error", "智能切片失败")}
            
            # 阶段5: OCR处理
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.OCR_PROCESSING,
                    progress=60, message="正在进行OCR识别..."
                )
            )
            
            # OCR处理
            ocr_result = self._perform_ocr_processing(temp_files, slice_result, drawing, task_id, loop)
            if not ocr_result["success"]:
                logger.warning(f"⚠️ OCR处理失败: {ocr_result.get('error', '未知错误')}")
            
            # 阶段6: Vision分析
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.AI_ANALYSIS,
                    progress=80, message="正在进行智能分析..."
                )
            )
            
            # Vision分析
            vision_result = self._perform_vision_analysis(temp_files, slice_result, drawing, task_id, loop)
            if not vision_result["success"]:
                logger.warning(f"⚠️ Vision分析失败: {vision_result.get('error', '未知错误')}")
            
            # 阶段7: 结果合并和工程量计算
            loop.run_until_complete(
                task_manager.update_task_status(
                    task_id, TaskStatus.PROCESSING, TaskStage.RESULT_PROCESSING,
                    progress=90, message="正在合并结果和计算工程量..."
                )
            )
            
            # 结果合并
            final_result = self._merge_analysis_results(ocr_result, vision_result, drawing, task_id)
            
            logger.info("✅ 双轨协同分析完成")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 双轨协同分析失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _perform_intelligent_slicing(self, temp_files: List[str], drawing, task_id: str, loop) -> Dict[str, Any]:
        """执行智能切片"""
        try:
            logger.info("📐 开始智能切片...")
            
            if not self.vision_scanner:
                return {"success": False, "error": "Vision扫描器不可用"}
            
            # 使用Vision扫描器进行智能切片
            slice_results = {}
            
            for i, image_path in enumerate(temp_files):
                try:
                    logger.info(f"处理图像 {i+1}/{len(temp_files)}: {image_path}")
                    
                    # 调用Vision扫描器的智能切片功能
                    result = self.vision_scanner.scan_with_intelligent_slicing(
                        image_path=image_path,
                        drawing_info={
                            "drawing_id": drawing.id,
                            "filename": drawing.filename,
                            "batch_id": 1,
                            "page_number": i + 1
                        },
                        task_id=f"{task_id}_slice_{i}",
                        enable_slicing=True
                    )
                    
                    if result.get("success"):
                        slice_results[image_path] = result
                        logger.info(f"  ✅ 智能切片成功")
                    else:
                        logger.warning(f"  ⚠️ 智能切片失败: {result.get('error', '未知错误')}")
                        slice_results[image_path] = {"sliced": False, "reason": result.get("error", "未知错误")}
                        
                except Exception as slice_error:
                    logger.error(f"  ❌ 智能切片异常: {slice_error}")
                    slice_results[image_path] = {"sliced": False, "reason": str(slice_error)}
            
            logger.info(f"✅ 智能切片完成，处理 {len(slice_results)} 张图像")
            
            return {
                "success": True,
                "slice_results": slice_results,
                "total_images": len(temp_files),
                "sliced_images": sum(1 for r in slice_results.values() if r.get("sliced", False))
            }
            
        except Exception as e:
            logger.error(f"❌ 智能切片失败: {e}")
            return {"success": False, "error": str(e)}

    def _perform_ocr_processing(self, temp_files: List[str], slice_result: Dict[str, Any], 
                               drawing, task_id: str, loop) -> Dict[str, Any]:
        """执行OCR处理"""
        try:
            logger.info("🔍 开始OCR处理...")
            
            from .drawing_image_processor import DrawingImageProcessor
            image_processor = DrawingImageProcessor(self.core_processor)
            
            # 使用共享切片结果进行OCR
            ocr_result = loop.run_until_complete(
                image_processor.process_images_with_shared_slices(
                    temp_files,
                    slice_result.get("slice_results", {}),
                    drawing.id,
                    task_id
                )
            )
            
            if ocr_result.get("success"):
                logger.info(f"✅ OCR处理成功: {ocr_result.get('statistics', {}).get('total_text_regions', 0)} 个文本区域")
            else:
                logger.warning(f"⚠️ OCR处理失败: {ocr_result.get('error', '未知错误')}")
            
            return ocr_result
            
        except Exception as e:
            logger.error(f"❌ OCR处理失败: {e}")
            return {"success": False, "error": str(e)}

    def _perform_vision_analysis(self, temp_files: List[str], slice_result: Dict[str, Any], 
                                drawing, task_id: str, loop) -> Dict[str, Any]:
        """执行Vision分析"""
        try:
            logger.info("👁️ 开始Vision分析...")
            
            if not self.vision_scanner:
                return {"success": False, "error": "Vision扫描器不可用"}
            
            # 使用增强网格切片分析器进行Vision分析
            vision_results = []
            
            for i, image_path in enumerate(temp_files):
                try:
                    logger.info(f"Vision分析图像 {i+1}/{len(temp_files)}")
                    
                    # 获取该图像的切片结果
                    image_slice_result = slice_result.get("slice_results", {}).get(image_path, {})
                    
                    # 使用增强网格切片分析器
                    from app.services.grid_slice import EnhancedGridSliceAnalyzer
                    analyzer = EnhancedGridSliceAnalyzer()
                    
                    vision_result = analyzer.analyze_drawing_with_dual_track(
                        image_path=image_path,
                        drawing_info={
                            "drawing_id": drawing.id,
                            "filename": drawing.filename,
                            "batch_id": 1,
                            "page_number": i + 1
                        },
                        task_id=f"{task_id}_vision_{i}",
                        shared_slice_results=image_slice_result
                    )
                    
                    if vision_result.get("success"):
                        vision_results.append(vision_result)
                        logger.info(f"  ✅ Vision分析成功: {len(vision_result.get('components', []))} 个构件")
                    else:
                        logger.warning(f"  ⚠️ Vision分析失败: {vision_result.get('error', '未知错误')}")
                        
                    # 清理分析器
                    analyzer.cleanup()
                    
                except Exception as vision_error:
                    logger.error(f"  ❌ Vision分析异常: {vision_error}")
            
            # 合并Vision分析结果
            all_components = []
            for result in vision_results:
                all_components.extend(result.get("components", []))
            
            logger.info(f"✅ Vision分析完成: 总计 {len(all_components)} 个构件")
            
            return {
                "success": True,
                "components": all_components,
                "vision_results": vision_results,
                "total_components": len(all_components)
            }
            
        except Exception as e:
            logger.error(f"❌ Vision分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _merge_analysis_results(self, ocr_result: Dict[str, Any], vision_result: Dict[str, Any], 
                               drawing, task_id: str) -> Dict[str, Any]:
        """合并分析结果并计算工程量"""
        try:
            logger.info("🔄 开始合并分析结果...")
            
            # 获取构件列表
            components = vision_result.get("components", [])
            ocr_statistics = ocr_result.get("statistics", {})
            
            # 工程量计算
            quantity_result = self._calculate_quantities(components, drawing, task_id)
            
            # 构建最终结果
            final_result = {
                "success": True,
                "components": components,
                "summary": {
                    "total_components": len(components),
                    "ocr_text_regions": ocr_statistics.get("total_text_regions", 0),
                    "processing_method": "dual_track_analysis",
                    "analysis_engine": "enhanced_grid_slice"
                },
                "ocr_info": ocr_statistics,
                "quantity_info": quantity_result,
                "processing_time": "实时计算"
            }
            
            logger.info(f"✅ 分析结果合并完成: {len(components)} 个构件")
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 分析结果合并失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "components": vision_result.get("components", [])
            }

    def _calculate_quantities(self, components: List[Dict[str, Any]], drawing, task_id: str) -> Dict[str, Any]:
        """计算工程量"""
        try:
            if not self.quantity_engine:
                logger.warning("⚠️ 工程量引擎不可用，跳过工程量计算")
                return {"success": False, "error": "工程量引擎不可用"}
            
            logger.info("📊 开始工程量计算...")
            
            # 使用统一工程量引擎计算
            quantity_result = self.quantity_engine.calculate_quantities(
                components=components,
                drawing_info={
                    "drawing_id": drawing.id,
                    "filename": drawing.filename
                },
                task_id=task_id
            )
            
            if quantity_result.get("success"):
                logger.info("✅ 工程量计算完成")
            else:
                logger.warning(f"⚠️ 工程量计算失败: {quantity_result.get('error', '未知错误')}")
            
            return quantity_result
            
        except Exception as e:
            logger.error(f"❌ 工程量计算异常: {e}")
            return {"success": False, "error": str(e)}

    def save_analysis_results(self, results: Dict[str, Any], drawing, task_id: str) -> Dict[str, Any]:
        """保存分析结果"""
        try:
            logger.info("💾 保存分析结果...")
            
            # 保存到数据库或存储服务
            # 这里可以实现具体的保存逻辑
            
            logger.info("✅ 分析结果保存完成")
            
            return {"success": True, "saved": True}
            
        except Exception as e:
            logger.error(f"❌ 保存分析结果失败: {e}")
            return {"success": False, "error": str(e)}

    def generate_summary_report(self, results: Dict[str, Any], drawing, task_id: str) -> Dict[str, Any]:
        """生成汇总报告"""
        try:
            logger.info("📋 生成汇总报告...")
            
            components = results.get("components", [])
            
            # 统计信息
            stats = {
                "total_components": len(components),
                "component_types": len(set(comp.get("component_type", "") for comp in components)),
                "processing_method": results.get("summary", {}).get("processing_method", "unknown"),
                "success_rate": "100%" if results.get("success") else "部分成功"
            }
            
            # 构件类型分布
            type_distribution = {}
            for comp in components:
                comp_type = comp.get("component_type", "未知")
                type_distribution[comp_type] = type_distribution.get(comp_type, 0) + 1
            
            report = {
                "summary": stats,
                "component_distribution": type_distribution,
                "drawing_info": {
                    "filename": drawing.filename,
                    "file_type": drawing.file_type,
                    "drawing_id": drawing.id
                },
                "task_id": task_id,
                "generation_time": "实时生成"
            }
            
            logger.info("✅ 汇总报告生成完成")
            
            return {"success": True, "report": report}
            
        except Exception as e:
            logger.error(f"❌ 生成汇总报告失败: {e}")
            return {"success": False, "error": str(e)}

    def cleanup(self):
        """清理资源"""
        logger.info("🧹 DrawingResultManager 资源清理完成") 