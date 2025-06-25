"""
跨模态验证引擎 - Step 3~4 优化
实现OCR轨道与Vision轨道的交叉验证与反馈机制
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """验证结果"""
    element_id: str
    ocr_confidence: float
    vision_confidence: float
    consistency_score: float
    validation_status: str  # consistent, inconsistent, missing, conflicted
    discrepancy_details: Optional[Dict[str, Any]]
    recommended_action: str

@dataclass
class CrossModalAlignment:
    """跨模态对齐结果"""
    matched_pairs: List[Dict[str, Any]]
    ocr_only_elements: List[Dict[str, Any]]
    vision_only_elements: List[Dict[str, Any]]
    alignment_confidence: float
    spatial_consistency: float

@dataclass
class FeedbackLoop:
    """反馈循环数据"""
    iteration: int
    ocr_adjustments: List[Dict[str, Any]]
    vision_refinements: List[Dict[str, Any]]
    convergence_score: float
    improvement_metrics: Dict[str, float]

class SpatialAlignmentEngine:
    """空间对齐引擎"""
    
    def __init__(self):
        self.coordinate_tolerance = 50  # 像素容差
        self.size_tolerance_ratio = 0.2  # 尺寸容差比例
    
    def align_ocr_vision_elements(self, ocr_elements: List[Dict], 
                                vision_elements: List[Dict]) -> CrossModalAlignment:
        """对齐OCR和Vision识别的元素"""
        try:
            logger.info(f"🔄 开始跨模态空间对齐: OCR {len(ocr_elements)} vs Vision {len(vision_elements)}")
            
            matched_pairs = []
            ocr_matched = set()
            vision_matched = set()
            
            # 基于空间位置匹配元素
            for i, ocr_elem in enumerate(ocr_elements):
                best_match = None
                best_score = 0.0
                best_j = -1
                
                for j, vision_elem in enumerate(vision_elements):
                    if j in vision_matched:
                        continue
                    
                    # 计算空间匹配度
                    spatial_score = self._calculate_spatial_similarity(ocr_elem, vision_elem)
                    
                    # 计算语义匹配度
                    semantic_score = self._calculate_semantic_similarity(ocr_elem, vision_elem)
                    
                    # 综合匹配度
                    overall_score = spatial_score * 0.7 + semantic_score * 0.3
                    
                    if overall_score > best_score and overall_score > 0.5:
                        best_score = overall_score
                        best_match = vision_elem
                        best_j = j
                
                if best_match is not None:
                    matched_pairs.append({
                        "ocr_element": ocr_elem,
                        "vision_element": best_match,
                        "match_confidence": best_score,
                        "ocr_index": i,
                        "vision_index": best_j
                    })
                    ocr_matched.add(i)
                    vision_matched.add(best_j)
            
            # 收集未匹配的元素
            ocr_only_elements = [elem for i, elem in enumerate(ocr_elements) if i not in ocr_matched]
            vision_only_elements = [elem for i, elem in enumerate(vision_elements) if i not in vision_matched]
            
            # 计算对齐置信度
            alignment_confidence = len(matched_pairs) / max(len(ocr_elements), len(vision_elements)) if ocr_elements or vision_elements else 0.0
            
            # 计算空间一致性
            spatial_consistency = self._calculate_spatial_consistency(matched_pairs)
            
            result = CrossModalAlignment(
                matched_pairs=matched_pairs,
                ocr_only_elements=ocr_only_elements,
                vision_only_elements=vision_only_elements,
                alignment_confidence=alignment_confidence,
                spatial_consistency=spatial_consistency
            )
            
            logger.info(f"✅ 跨模态对齐完成: 匹配 {len(matched_pairs)} 对, 对齐度 {alignment_confidence:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 跨模态对齐失败: {e}")
            return CrossModalAlignment(
                matched_pairs=[],
                ocr_only_elements=ocr_elements,
                vision_only_elements=vision_elements,
                alignment_confidence=0.0,
                spatial_consistency=0.0
            )
    
    def _calculate_spatial_similarity(self, ocr_elem: Dict, vision_elem: Dict) -> float:
        """计算空间相似度"""
        try:
            # 提取坐标信息
            ocr_coords = ocr_elem.get("coordinates", {})
            vision_coords = vision_elem.get("bbox", {})
            
            if not ocr_coords or not vision_coords:
                return 0.0
            
            # 计算中心点距离
            ocr_center_x = ocr_coords.get("x", 0) + ocr_coords.get("width", 0) / 2
            ocr_center_y = ocr_coords.get("y", 0) + ocr_coords.get("height", 0) / 2
            
            vision_center_x = vision_coords.get("x", 0) + vision_coords.get("width", 0) / 2
            vision_center_y = vision_coords.get("y", 0) + vision_coords.get("height", 0) / 2
            
            distance = ((ocr_center_x - vision_center_x) ** 2 + (ocr_center_y - vision_center_y) ** 2) ** 0.5
            
            # 距离相似度 (距离越小，相似度越高)
            distance_score = max(0, 1 - distance / self.coordinate_tolerance)
            
            # 尺寸相似度
            ocr_area = ocr_coords.get("width", 0) * ocr_coords.get("height", 0)
            vision_area = vision_coords.get("width", 0) * vision_coords.get("height", 0)
            
            if ocr_area > 0 and vision_area > 0:
                size_ratio = min(ocr_area, vision_area) / max(ocr_area, vision_area)
                size_score = size_ratio
            else:
                size_score = 0.0
            
            # 综合空间相似度
            spatial_similarity = distance_score * 0.6 + size_score * 0.4
            
            return spatial_similarity
            
        except Exception as e:
            logger.error(f"❌ 空间相似度计算失败: {e}")
            return 0.0
    
    def _calculate_semantic_similarity(self, ocr_elem: Dict, vision_elem: Dict) -> float:
        """计算语义相似度"""
        try:
            ocr_text = ocr_elem.get("text", "").lower()
            vision_label = vision_elem.get("label", "").lower()
            
            if not ocr_text or not vision_label:
                return 0.0
            
            # 简单的文本匹配
            if ocr_text == vision_label:
                return 1.0
            elif ocr_text in vision_label or vision_label in ocr_text:
                return 0.7
            else:
                # 基于关键词匹配
                ocr_keywords = set(ocr_text.split())
                vision_keywords = set(vision_label.split())
                
                if ocr_keywords & vision_keywords:
                    return 0.5
                else:
                    return 0.0
                    
        except Exception as e:
            logger.error(f"❌ 语义相似度计算失败: {e}")
            return 0.0
    
    def _calculate_spatial_consistency(self, matched_pairs: List[Dict]) -> float:
        """计算空间一致性"""
        if not matched_pairs:
            return 0.0
        
        consistent_pairs = 0
        for pair in matched_pairs:
            spatial_score = self._calculate_spatial_similarity(
                pair["ocr_element"], pair["vision_element"]
            )
            if spatial_score > 0.7:
                consistent_pairs += 1
        
        return consistent_pairs / len(matched_pairs)

class ConsistencyValidator:
    """一致性验证器"""
    
    def __init__(self):
        self.confidence_threshold = 0.6
        self.consistency_threshold = 0.7
    
    def validate_cross_modal_consistency(self, alignment: CrossModalAlignment) -> List[ValidationResult]:
        """验证跨模态一致性"""
        try:
            logger.info(f"🔍 开始一致性验证: {len(alignment.matched_pairs)} 个匹配对")
            
            validation_results = []
            
            # 验证匹配对的一致性
            for pair in alignment.matched_pairs:
                result = self._validate_matched_pair(pair)
                validation_results.append(result)
            
            # 处理仅OCR识别的元素
            for ocr_elem in alignment.ocr_only_elements:
                result = ValidationResult(
                    element_id=ocr_elem.get("slice_id", "unknown"),
                    ocr_confidence=ocr_elem.get("confidence", 0.0),
                    vision_confidence=0.0,
                    consistency_score=0.0,
                    validation_status="missing_vision",
                    discrepancy_details={"reason": "Vision轨道未识别"},
                    recommended_action="vision_reprocess"
                )
                validation_results.append(result)
            
            # 处理仅Vision识别的元素
            for vision_elem in alignment.vision_only_elements:
                result = ValidationResult(
                    element_id=vision_elem.get("id", "unknown"),
                    ocr_confidence=0.0,
                    vision_confidence=vision_elem.get("confidence", 0.0),
                    consistency_score=0.0,
                    validation_status="missing_ocr",
                    discrepancy_details={"reason": "OCR轨道未识别"},
                    recommended_action="ocr_reprocess"
                )
                validation_results.append(result)
            
            logger.info(f"✅ 一致性验证完成: {len(validation_results)} 个验证结果")
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ 一致性验证失败: {e}")
            return []
    
    def _validate_matched_pair(self, pair: Dict) -> ValidationResult:
        """验证匹配对"""
        ocr_elem = pair["ocr_element"]
        vision_elem = pair["vision_element"]
        match_confidence = pair["match_confidence"]
        
        ocr_confidence = ocr_elem.get("confidence", 0.0)
        vision_confidence = vision_elem.get("confidence", 0.0)
        
        # 计算一致性得分
        consistency_score = match_confidence
        
        # 确定验证状态
        if consistency_score >= self.consistency_threshold:
            if ocr_confidence >= self.confidence_threshold and vision_confidence >= self.confidence_threshold:
                validation_status = "consistent"
                recommended_action = "accept"
            else:
                validation_status = "low_confidence"
                recommended_action = "manual_review"
        else:
            validation_status = "inconsistent"
            recommended_action = "investigate"
        
        # 分析差异细节
        discrepancy_details = self._analyze_discrepancies(ocr_elem, vision_elem)
        
        return ValidationResult(
            element_id=ocr_elem.get("slice_id", "unknown"),
            ocr_confidence=ocr_confidence,
            vision_confidence=vision_confidence,
            consistency_score=consistency_score,
            validation_status=validation_status,
            discrepancy_details=discrepancy_details,
            recommended_action=recommended_action
        )
    
    def _analyze_discrepancies(self, ocr_elem: Dict, vision_elem: Dict) -> Dict[str, Any]:
        """分析差异细节"""
        discrepancies = {}
        
        # 文本差异
        ocr_text = ocr_elem.get("text", "")
        vision_label = vision_elem.get("label", "")
        if ocr_text != vision_label:
            discrepancies["text_mismatch"] = {
                "ocr_text": ocr_text,
                "vision_label": vision_label
            }
        
        # 坐标差异
        ocr_coords = ocr_elem.get("coordinates", {})
        vision_coords = vision_elem.get("bbox", {})
        if ocr_coords and vision_coords:
            coord_diff = {
                "x_diff": abs(ocr_coords.get("x", 0) - vision_coords.get("x", 0)),
                "y_diff": abs(ocr_coords.get("y", 0) - vision_coords.get("y", 0))
            }
            if coord_diff["x_diff"] > 20 or coord_diff["y_diff"] > 20:
                discrepancies["coordinate_mismatch"] = coord_diff
        
        return discrepancies

class FeedbackLoopManager:
    """反馈循环管理器"""
    
    def __init__(self):
        self.max_iterations = 3
        self.convergence_threshold = 0.85
    
    async def execute_feedback_loop(self, validation_results: List[ValidationResult], 
                                  ocr_data: Dict, vision_data: Dict) -> FeedbackLoop:
        """执行反馈循环优化"""
        try:
            logger.info(f"🔄 开始反馈循环优化: {len(validation_results)} 个验证结果")
            
            iteration = 1
            current_convergence = self._calculate_convergence_score(validation_results)
            
            ocr_adjustments = []
            vision_refinements = []
            
            # 分析需要调整的项目
            for result in validation_results:
                if result.validation_status in ["inconsistent", "low_confidence"]:
                    if result.recommended_action == "ocr_reprocess":
                        ocr_adjustments.append({
                            "element_id": result.element_id,
                            "adjustment_type": "reprocess",
                            "reason": result.discrepancy_details
                        })
                    elif result.recommended_action == "vision_reprocess":
                        vision_refinements.append({
                            "element_id": result.element_id,
                            "refinement_type": "reprocess",
                            "reason": result.discrepancy_details
                        })
            
            # 计算改进指标
            improvement_metrics = {
                "consistency_improvement": max(0, current_convergence - 0.5),
                "ocr_adjustments_count": len(ocr_adjustments),
                "vision_refinements_count": len(vision_refinements),
                "convergence_rate": current_convergence
            }
            
            feedback_loop = FeedbackLoop(
                iteration=iteration,
                ocr_adjustments=ocr_adjustments,
                vision_refinements=vision_refinements,
                convergence_score=current_convergence,
                improvement_metrics=improvement_metrics
            )
            
            logger.info(f"✅ 反馈循环完成: 收敛度 {current_convergence:.3f}")
            return feedback_loop
            
        except Exception as e:
            logger.error(f"❌ 反馈循环失败: {e}")
            return FeedbackLoop(
                iteration=0,
                ocr_adjustments=[],
                vision_refinements=[],
                convergence_score=0.0,
                improvement_metrics={"error": str(e)}
            )
    
    def _calculate_convergence_score(self, validation_results: List[ValidationResult]) -> float:
        """计算收敛度"""
        if not validation_results:
            return 0.0
        
        consistent_count = len([r for r in validation_results if r.validation_status == "consistent"])
        return consistent_count / len(validation_results)

class CrossModalValidationEngine:
    """跨模态验证引擎"""
    
    def __init__(self):
        self.spatial_aligner = SpatialAlignmentEngine()
        self.consistency_validator = ConsistencyValidator()
        self.feedback_manager = FeedbackLoopManager()
    
    async def validate_cross_modal_results(self, ocr_output: Dict, vision_output: Dict, 
                                         task_id: str) -> Dict[str, Any]:
        """验证跨模态结果"""
        try:
            logger.info(f"🔄 开始跨模态验证: 任务 {task_id}")
            start_time = time.time()
            
            # 1. 提取元素数据
            ocr_elements = self._extract_ocr_elements(ocr_output)
            vision_elements = self._extract_vision_elements(vision_output)
            
            logger.info(f"📊 提取元素: OCR {len(ocr_elements)}, Vision {len(vision_elements)}")
            
            # 2. 空间对齐
            alignment = self.spatial_aligner.align_ocr_vision_elements(ocr_elements, vision_elements)
            
            # 3. 一致性验证
            validation_results = self.consistency_validator.validate_cross_modal_consistency(alignment)
            
            # 4. 反馈循环
            feedback_loop = await self.feedback_manager.execute_feedback_loop(
                validation_results, ocr_output, vision_output
            )
            
            # 5. 生成验证报告
            validation_report = {
                "task_id": task_id,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "processing_time": time.time() - start_time,
                "alignment_summary": asdict(alignment),
                "validation_results": [asdict(r) for r in validation_results],
                "feedback_loop": asdict(feedback_loop),
                "overall_metrics": {
                    "alignment_confidence": alignment.alignment_confidence,
                    "spatial_consistency": alignment.spatial_consistency,
                    "convergence_score": feedback_loop.convergence_score,
                    "total_elements": len(ocr_elements) + len(vision_elements),
                    "matched_pairs": len(alignment.matched_pairs),
                    "consistency_rate": len([r for r in validation_results if r.validation_status == "consistent"]) / len(validation_results) if validation_results else 0
                }
            }
            
            logger.info(f"✅ 跨模态验证完成: 对齐度 {alignment.alignment_confidence:.3f}, 一致性 {validation_report['overall_metrics']['consistency_rate']:.3f}")
            
            return {
                "success": True,
                "validation_report": validation_report
            }
            
        except Exception as e:
            logger.error(f"❌ 跨模态验证失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "validation_report": None
            }
    
    def _extract_ocr_elements(self, ocr_output: Dict) -> List[Dict]:
        """提取OCR元素"""
        elements = []
        
        # 从标准化OCR输出中提取元素
        if "slice_results" in ocr_output:
            for result in ocr_output["slice_results"]:
                if result.get("raw_text", "").strip():
                    elements.append({
                        "slice_id": result.get("slice_id", ""),
                        "text": result.get("raw_text", ""),
                        "coordinates": result.get("coordinates", {}),
                        "confidence": result.get("confidence", 0.0)
                    })
        
        return elements
    
    def _extract_vision_elements(self, vision_output: Dict) -> List[Dict]:
        """提取Vision元素"""
        elements = []
        
        # 从Vision输出中提取元素
        if "detected_components" in vision_output:
            for i, component in enumerate(vision_output["detected_components"]):
                elements.append({
                    "id": f"vision_{i}",
                    "label": component.get("label", ""),
                    "bbox": component.get("bbox", {}),
                    "confidence": component.get("confidence", 0.0),
                    "type": component.get("type", "unknown")
                })
        
        return elements 