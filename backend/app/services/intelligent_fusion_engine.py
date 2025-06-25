"""智能融合引擎 - Step 5 优化"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class FusionCandidate:
    """融合候选项"""
    element_id: str
    source: str  # ocr, vision, hybrid
    confidence: float
    attributes: Dict[str, Any]
    spatial_info: Dict[str, Any]
    fusion_score: float
    conflict_indicators: List[str]

@dataclass
class ConflictResolution:
    """冲突解决方案"""
    conflict_id: str
    conflict_type: str
    candidates: List[FusionCandidate]
    resolution_strategy: str
    selected_candidate: Optional[FusionCandidate]
    confidence_boost: float
    resolution_reason: str

@dataclass
class FusedComponent:
    """融合后的构件"""
    component_id: str
    label: str
    type: str
    dimensions: Dict[str, Any]
    position: Dict[str, Any]
    confidence: float
    source_fusion: Dict[str, Any]
    attributes: Dict[str, Any]
    quality_score: float

class ConfidenceCalculator:
    """置信度计算器"""
    
    def __init__(self):
        self.source_weights = {
            "ocr": 0.6,
            "vision": 0.7,
            "hybrid": 0.85
        }
        self.quality_factors = {
            "spatial_consistency": 0.3,
            "semantic_clarity": 0.3,
            "cross_validation": 0.4
        }
    
    def calculate_fusion_confidence(self, candidates: List[FusionCandidate]) -> float:
        """计算融合置信度"""
        try:
            if not candidates:
                return 0.0
            
            # 基础置信度加权平均
            weighted_confidence = 0.0
            total_weight = 0.0
            
            for candidate in candidates:
                source_weight = self.source_weights.get(candidate.source, 0.5)
                weight = source_weight * candidate.confidence
                weighted_confidence += weight * candidate.confidence
                total_weight += weight
            
            base_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
            
            # 一致性加成
            consistency_bonus = self._calculate_consistency_bonus(candidates)
            
            # 多源验证加成
            multi_source_bonus = self._calculate_multi_source_bonus(candidates)
            
            # 综合置信度
            final_confidence = min(1.0, base_confidence + consistency_bonus + multi_source_bonus)
            
            return final_confidence
            
        except Exception as e:
            logger.error(f"❌ 融合置信度计算失败: {e}")
            return 0.0
    
    def _calculate_consistency_bonus(self, candidates: List[FusionCandidate]) -> float:
        """计算一致性加成"""
        if len(candidates) < 2:
            return 0.0
        
        # 检查属性一致性
        consistent_attributes = 0
        total_attributes = 0
        
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                attrs1 = candidates[i].attributes
                attrs2 = candidates[j].attributes
                
                common_keys = set(attrs1.keys()) & set(attrs2.keys())
                for key in common_keys:
                    total_attributes += 1
                    if attrs1[key] == attrs2[key]:
                        consistent_attributes += 1
        
        consistency_ratio = consistent_attributes / total_attributes if total_attributes > 0 else 0.0
        return consistency_ratio * 0.1  # 最多10%加成
    
    def _calculate_multi_source_bonus(self, candidates: List[FusionCandidate]) -> float:
        """计算多源验证加成"""
        sources = set(candidate.source for candidate in candidates)
        
        if len(sources) >= 2:
            return 0.05  # 多源验证5%加成
        else:
            return 0.0

class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self):
        self.resolution_strategies = {
            "spatial_conflict": self._resolve_spatial_conflict,
            "attribute_conflict": self._resolve_attribute_conflict,
            "semantic_conflict": self._resolve_semantic_conflict,
            "confidence_conflict": self._resolve_confidence_conflict
        }
    
    def resolve_conflicts(self, conflict_groups: List[List[FusionCandidate]]) -> List[ConflictResolution]:
        """解决冲突"""
        try:
            logger.info(f"🔧 开始冲突解决: {len(conflict_groups)} 个冲突组")
            
            resolutions = []
            
            for i, candidates in enumerate(conflict_groups):
                if len(candidates) <= 1:
                    continue
                
                # 识别冲突类型
                conflict_type = self._identify_conflict_type(candidates)
                
                # 选择解决策略
                resolution_strategy = self._select_resolution_strategy(conflict_type)
                
                # 执行冲突解决
                resolution = self._execute_resolution(
                    f"conflict_{i}", conflict_type, candidates, resolution_strategy
                )
                
                resolutions.append(resolution)
            
            logger.info(f"✅ 冲突解决完成: {len(resolutions)} 个解决方案")
            return resolutions
            
        except Exception as e:
            logger.error(f"❌ 冲突解决失败: {e}")
            return []
    
    def _identify_conflict_type(self, candidates: List[FusionCandidate]) -> str:
        """识别冲突类型"""
        # 检查空间冲突
        spatial_variance = self._calculate_spatial_variance(candidates)
        if spatial_variance > 0.3:
            return "spatial_conflict"
        
        # 检查属性冲突
        if self._has_attribute_conflicts(candidates):
            return "attribute_conflict"
        
        # 检查语义冲突
        if self._has_semantic_conflicts(candidates):
            return "semantic_conflict"
        
        # 默认为置信度冲突
        return "confidence_conflict"
    
    def _calculate_spatial_variance(self, candidates: List[FusionCandidate]) -> float:
        """计算空间方差"""
        if len(candidates) < 2:
            return 0.0
        
        positions = []
        for candidate in candidates:
            spatial_info = candidate.spatial_info
            if spatial_info:
                x = spatial_info.get("x", 0)
                y = spatial_info.get("y", 0)
                positions.append((x, y))
        
        if len(positions) < 2:
            return 0.0
        
        # 计算位置方差
        mean_x = sum(pos[0] for pos in positions) / len(positions)
        mean_y = sum(pos[1] for pos in positions) / len(positions)
        
        variance = sum((pos[0] - mean_x) ** 2 + (pos[1] - mean_y) ** 2 for pos in positions) / len(positions)
        
        return min(1.0, variance / 10000)  # 归一化
    
    def _has_attribute_conflicts(self, candidates: List[FusionCandidate]) -> bool:
        """检查属性冲突"""
        if len(candidates) < 2:
            return False
        
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                attrs1 = candidates[i].attributes
                attrs2 = candidates[j].attributes
                
                common_keys = set(attrs1.keys()) & set(attrs2.keys())
                for key in common_keys:
                    if attrs1[key] != attrs2[key]:
                        return True
        
        return False
    
    def _has_semantic_conflicts(self, candidates: List[FusionCandidate]) -> bool:
        """检查语义冲突"""
        labels = [candidate.attributes.get("label", "") for candidate in candidates]
        unique_labels = set(label.lower() for label in labels if label)
        
        return len(unique_labels) > 1
    
    def _select_resolution_strategy(self, conflict_type: str) -> str:
        """选择解决策略"""
        return conflict_type  # 简化实现，直接使用冲突类型作为策略
    
    def _execute_resolution(self, conflict_id: str, conflict_type: str, 
                          candidates: List[FusionCandidate], strategy: str) -> ConflictResolution:
        """执行冲突解决"""
        resolver_func = self.resolution_strategies.get(strategy, self._resolve_confidence_conflict)
        
        selected_candidate, confidence_boost, reason = resolver_func(candidates)
        
        return ConflictResolution(
            conflict_id=conflict_id,
            conflict_type=conflict_type,
            candidates=candidates,
            resolution_strategy=strategy,
            selected_candidate=selected_candidate,
            confidence_boost=confidence_boost,
            resolution_reason=reason
        )
    
    def _resolve_spatial_conflict(self, candidates: List[FusionCandidate]) -> Tuple[FusionCandidate, float, str]:
        """解决空间冲突"""
        # 选择空间信息最完整且置信度最高的候选项
        best_candidate = max(candidates, key=lambda c: (
            len(c.spatial_info), c.confidence
        ))
        
        return best_candidate, 0.05, "选择空间信息最完整的候选项"
    
    def _resolve_attribute_conflict(self, candidates: List[FusionCandidate]) -> Tuple[FusionCandidate, float, str]:
        """解决属性冲突"""
        # 选择属性最丰富的候选项
        best_candidate = max(candidates, key=lambda c: (
            len(c.attributes), c.confidence
        ))
        
        return best_candidate, 0.03, "选择属性信息最丰富的候选项"
    
    def _resolve_semantic_conflict(self, candidates: List[FusionCandidate]) -> Tuple[FusionCandidate, float, str]:
        """解决语义冲突"""
        # 优先选择vision源的结果
        vision_candidates = [c for c in candidates if c.source == "vision"]
        if vision_candidates:
            best_candidate = max(vision_candidates, key=lambda c: c.confidence)
            return best_candidate, 0.08, "优先选择Vision识别结果"
        
        # 否则选择置信度最高的
        best_candidate = max(candidates, key=lambda c: c.confidence)
        return best_candidate, 0.02, "选择置信度最高的候选项"
    
    def _resolve_confidence_conflict(self, candidates: List[FusionCandidate]) -> Tuple[FusionCandidate, float, str]:
        """解决置信度冲突"""
        best_candidate = max(candidates, key=lambda c: c.confidence)
        return best_candidate, 0.0, "选择置信度最高的候选项"

class ComponentFuser:
    """构件融合器"""
    
    def __init__(self):
        self.confidence_calculator = ConfidenceCalculator()
    
    def fuse_components(self, resolved_conflicts: List[ConflictResolution], 
                       single_candidates: List[FusionCandidate]) -> List[FusedComponent]:
        """融合构件"""
        try:
            logger.info(f"🔄 开始构件融合: {len(resolved_conflicts)} 个冲突解决 + {len(single_candidates)} 个单独候选")
            
            fused_components = []
            
            # 处理冲突解决后的构件
            for resolution in resolved_conflicts:
                if resolution.selected_candidate:
                    fused_component = self._create_fused_component(
                        resolution.selected_candidate, 
                        resolution.confidence_boost,
                        f"conflict_resolved_{resolution.conflict_id}"
                    )
                    fused_components.append(fused_component)
            
            # 处理单独的候选项
            for candidate in single_candidates:
                fused_component = self._create_fused_component(
                    candidate, 0.0, f"single_{candidate.element_id}"
                )
                fused_components.append(fused_component)
            
            logger.info(f"✅ 构件融合完成: {len(fused_components)} 个融合构件")
            return fused_components
            
        except Exception as e:
            logger.error(f"❌ 构件融合失败: {e}")
            return []
    
    def _create_fused_component(self, candidate: FusionCandidate, 
                              confidence_boost: float, component_id: str) -> FusedComponent:
        """创建融合构件"""
        
        # 提取构件信息
        label = candidate.attributes.get("label", "unknown")
        comp_type = candidate.attributes.get("type", "unknown")
        
        # 提取尺寸信息
        dimensions = {
            "width": candidate.spatial_info.get("width", 0),
            "height": candidate.spatial_info.get("height", 0),
            "depth": candidate.attributes.get("depth", 0)
        }
        
        # 提取位置信息
        position = {
            "x": candidate.spatial_info.get("x", 0),
            "y": candidate.spatial_info.get("y", 0),
            "z": candidate.spatial_info.get("z", 0)
        }
        
        # 计算最终置信度
        final_confidence = min(1.0, candidate.confidence + confidence_boost)
        
        # 计算质量评分
        quality_score = self._calculate_quality_score(candidate, final_confidence)
        
        return FusedComponent(
            component_id=component_id,
            label=label,
            type=comp_type,
            dimensions=dimensions,
            position=position,
            confidence=final_confidence,
            source_fusion={
                "primary_source": candidate.source,
                "fusion_score": candidate.fusion_score,
                "confidence_boost": confidence_boost
            },
            attributes=candidate.attributes.copy(),
            quality_score=quality_score
        )
    
    def _calculate_quality_score(self, candidate: FusionCandidate, final_confidence: float) -> float:
        """计算质量评分"""
        # 基础质量评分
        base_score = final_confidence
        
        # 属性完整性加成
        attribute_completeness = len(candidate.attributes) / 10  # 假设最多10个属性
        completeness_bonus = min(0.1, attribute_completeness * 0.1)
        
        # 空间信息完整性加成
        spatial_completeness = len(candidate.spatial_info) / 6  # 假设最多6个空间属性
        spatial_bonus = min(0.1, spatial_completeness * 0.1)
        
        return min(1.0, base_score + completeness_bonus + spatial_bonus)

class IntelligentFusionEngine:
    """智能融合引擎"""
    
    def __init__(self):
        self.confidence_calculator = ConfidenceCalculator()
        self.conflict_resolver = ConflictResolver()
        self.component_fuser = ComponentFuser()
    
    async def fuse_multi_modal_results(self, ocr_results: Dict, vision_results: Dict, 
                                     validation_report: Dict, task_id: str) -> Dict[str, Any]:
        """融合多模态结果"""
        try:
            logger.info(f"🔄 开始智能融合: 任务 {task_id}")
            start_time = time.time()
            
            # 1. 准备融合候选项
            fusion_candidates = self._prepare_fusion_candidates(
                ocr_results, vision_results, validation_report
            )
            
            logger.info(f"📊 准备融合候选: {len(fusion_candidates)} 个候选项")
            
            # 2. 分组冲突候选项
            conflict_groups, single_candidates = self._group_conflict_candidates(fusion_candidates)
            
            logger.info(f"🔍 冲突分组: {len(conflict_groups)} 个冲突组, {len(single_candidates)} 个单独候选")
            
            # 3. 解决冲突
            resolved_conflicts = self.conflict_resolver.resolve_conflicts(conflict_groups)
            
            # 4. 融合构件
            fused_components = self.component_fuser.fuse_components(resolved_conflicts, single_candidates)
            
            # 5. 生成融合报告
            fusion_report = {
                "task_id": task_id,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "processing_time": time.time() - start_time,
                "fusion_summary": {
                    "total_candidates": len(fusion_candidates),
                    "conflict_groups": len(conflict_groups),
                    "resolved_conflicts": len(resolved_conflicts),
                    "single_candidates": len(single_candidates),
                    "fused_components": len(fused_components)
                },
                "fused_components": [asdict(comp) for comp in fused_components],
                "quality_metrics": self._calculate_fusion_quality_metrics(fused_components),
                "conflict_resolutions": [asdict(res) for res in resolved_conflicts]
            }
            
            logger.info(f"✅ 智能融合完成: {len(fused_components)} 个融合构件")
            
            return {
                "success": True,
                "fusion_report": fusion_report
            }
            
        except Exception as e:
            logger.error(f"❌ 智能融合失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "fusion_report": None
            }
    
    def _prepare_fusion_candidates(self, ocr_results: Dict, vision_results: Dict, 
                                 validation_report: Dict) -> List[FusionCandidate]:
        """准备融合候选项"""
        candidates = []
        
        # 从OCR结果创建候选项
        if "slice_results" in ocr_results:
            for result in ocr_results["slice_results"]:
                candidate = FusionCandidate(
                    element_id=result.get("slice_id", ""),
                    source="ocr",
                    confidence=result.get("confidence", 0.0),
                    attributes={
                        "label": result.get("raw_text", ""),
                        "type": "text_element"
                    },
                    spatial_info=result.get("coordinates", {}),
                    fusion_score=result.get("confidence", 0.0),
                    conflict_indicators=[]
                )
                candidates.append(candidate)
        
        # 从Vision结果创建候选项
        if "detected_components" in vision_results:
            for i, component in enumerate(vision_results["detected_components"]):
                candidate = FusionCandidate(
                    element_id=f"vision_{i}",
                    source="vision",
                    confidence=component.get("confidence", 0.0),
                    attributes={
                        "label": component.get("label", ""),
                        "type": component.get("type", "unknown")
                    },
                    spatial_info=component.get("bbox", {}),
                    fusion_score=component.get("confidence", 0.0),
                    conflict_indicators=[]
                )
                candidates.append(candidate)
        
        return candidates
    
    def _group_conflict_candidates(self, candidates: List[FusionCandidate]) -> Tuple[List[List[FusionCandidate]], List[FusionCandidate]]:
        """分组冲突候选项"""
        conflict_groups = []
        single_candidates = []
        processed = set()
        
        for i, candidate in enumerate(candidates):
            if i in processed:
                continue
            
            # 查找与当前候选项冲突的其他候选项
            conflict_group = [candidate]
            processed.add(i)
            
            for j, other_candidate in enumerate(candidates[i+1:], i+1):
                if j in processed:
                    continue
                
                if self._has_spatial_overlap(candidate, other_candidate):
                    conflict_group.append(other_candidate)
                    processed.add(j)
            
            if len(conflict_group) > 1:
                conflict_groups.append(conflict_group)
            else:
                single_candidates.append(candidate)
        
        return conflict_groups, single_candidates
    
    def _has_spatial_overlap(self, candidate1: FusionCandidate, candidate2: FusionCandidate) -> bool:
        """检查空间重叠"""
        spatial1 = candidate1.spatial_info
        spatial2 = candidate2.spatial_info
        
        if not spatial1 or not spatial2:
            return False
        
        # 简化的重叠检测
        x1, y1 = spatial1.get("x", 0), spatial1.get("y", 0)
        w1, h1 = spatial1.get("width", 0), spatial1.get("height", 0)
        
        x2, y2 = spatial2.get("x", 0), spatial2.get("y", 0)
        w2, h2 = spatial2.get("width", 0), spatial2.get("height", 0)
        
        # 检查矩形重叠
        overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
        
        overlap_area = overlap_x * overlap_y
        area1 = w1 * h1
        area2 = w2 * h2
        
        # 如果重叠面积超过任一候选项面积的30%，则认为有冲突
        if area1 > 0 and overlap_area / area1 > 0.3:
            return True
        if area2 > 0 and overlap_area / area2 > 0.3:
            return True
        
        return False
    
    def _calculate_fusion_quality_metrics(self, fused_components: List[FusedComponent]) -> Dict[str, float]:
        """计算融合质量指标"""
        if not fused_components:
            return {"overall_quality": 0.0}
        
        # 平均置信度
        avg_confidence = sum(comp.confidence for comp in fused_components) / len(fused_components)
        
        # 平均质量评分
        avg_quality = sum(comp.quality_score for comp in fused_components) / len(fused_components)
        
        # 高质量构件比例
        high_quality_ratio = len([comp for comp in fused_components if comp.quality_score > 0.8]) / len(fused_components)
        
        # 源分布多样性
        sources = [comp.source_fusion["primary_source"] for comp in fused_components]
        source_diversity = len(set(sources)) / 3  # 假设最多3种源
        
        return {
            "overall_quality": (avg_confidence + avg_quality) / 2,
            "avg_confidence": avg_confidence,
            "avg_quality_score": avg_quality,
            "high_quality_ratio": high_quality_ratio,
            "source_diversity": source_diversity,
            "total_components": len(fused_components)
        } 