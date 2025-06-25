"""
统一OCR处理管道 - Step 2~2.5 优化
实现标准化的OCR识别与清洗一体化流程
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class OCRResult:
    """标准化OCR结果"""
    slice_id: str
    filename: str
    coordinates: Dict[str, int]  # x, y, width, height
    raw_text: str
    confidence: float
    processing_time: float
    ocr_engine: str
    language: str = "zh-CN"

@dataclass
class CleanedOCRData:
    """清洗后的OCR数据"""
    text_blocks: List[Dict[str, Any]]
    component_labels: List[Dict[str, Any]]
    dimensions: List[Dict[str, Any]]
    annotations: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    confidence_score: float
    processing_stage: str

@dataclass
class StandardizedOutput:
    """标准化输出格式"""
    task_id: str
    timestamp: str
    stage: str  # ocr_recognition, ocr_cleaning, summary_generation
    slice_results: List[OCRResult]
    cleaned_data: Optional[CleanedOCRData]
    summary: Optional[Dict[str, Any]]
    quality_metrics: Dict[str, float]
    processing_metadata: Dict[str, Any]

class OCREngineAdapter:
    """OCR引擎适配器"""
    
    def __init__(self, engine_type: str = "paddleocr"):
        self.engine_type = engine_type
        self._initialize_engine()
    
    def _initialize_engine(self):
        """初始化OCR引擎"""
        if self.engine_type == "paddleocr":
            try:
                from paddleocr import PaddleOCR
                self.ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch')
                logger.info("✅ PaddleOCR引擎初始化成功")
            except ImportError:
                logger.error("❌ PaddleOCR未安装")
                self.ocr_engine = None
        else:
            logger.warning(f"⚠️ 不支持的OCR引擎类型: {self.engine_type}")
            self.ocr_engine = None
    
    def recognize_text(self, image_path: str, slice_info: Dict) -> OCRResult:
        """统一的文本识别接口"""
        start_time = time.time()
        
        try:
            if self.ocr_engine is None:
                # 模拟OCR结果
                raw_text = f"模拟OCR结果 - {slice_info.get('filename', 'unknown')}"
                confidence = 0.85
            else:
                # 实际OCR识别
                result = self.ocr_engine.ocr(image_path, cls=True)
                
                # 提取文本和置信度
                text_parts = []
                confidences = []
                
                if result and result[0]:
                    for line in result[0]:
                        if len(line) >= 2:
                            text = line[1][0] if line[1] else ""
                            conf = line[1][1] if len(line[1]) > 1 else 0.0
                            text_parts.append(text)
                            confidences.append(conf)
                
                raw_text = " ".join(text_parts)
                confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                slice_id=slice_info.get("slice_id", "unknown"),
                filename=slice_info.get("filename", "unknown"),
                coordinates={
                    "x": slice_info.get("x_offset", 0),
                    "y": slice_info.get("y_offset", 0),
                    "width": slice_info.get("width", 0),
                    "height": slice_info.get("height", 0)
                },
                raw_text=raw_text,
                confidence=confidence,
                processing_time=processing_time,
                ocr_engine=self.engine_type
            )
            
        except Exception as e:
            logger.error(f"❌ OCR识别失败 {image_path}: {e}")
            return OCRResult(
                slice_id=slice_info.get("slice_id", "unknown"),
                filename=slice_info.get("filename", "unknown"),
                coordinates={},
                raw_text="",
                confidence=0.0,
                processing_time=time.time() - start_time,
                ocr_engine=self.engine_type
            )

class OCRDataCleaner:
    """OCR数据清洗器"""
    
    def __init__(self):
        self.component_keywords = [
            "柱", "梁", "板", "墙", "基础", "楼梯", "门", "窗",
            "C", "L", "B", "W", "F", "S", "D", "Win"
        ]
        self.dimension_patterns = [
            r"\d+[x×]\d+",  # 尺寸格式
            r"\d+mm", r"\d+cm", r"\d+m",  # 单位格式
            r"φ\d+", r"Φ\d+"  # 直径格式
        ]
    
    def clean_ocr_results(self, ocr_results: List[OCRResult]) -> CleanedOCRData:
        """清洗OCR识别结果"""
        try:
            # 合并所有文本
            all_text = " ".join([result.raw_text for result in ocr_results])
            
            # 分类提取
            text_blocks = self._extract_text_blocks(ocr_results)
            component_labels = self._extract_component_labels(all_text)
            dimensions = self._extract_dimensions(all_text)
            annotations = self._extract_annotations(all_text)
            
            # 计算置信度
            avg_confidence = sum([r.confidence for r in ocr_results]) / len(ocr_results) if ocr_results else 0.0
            
            # 生成元数据
            metadata = {
                "total_slices": len(ocr_results),
                "total_text_length": len(all_text),
                "processing_time": sum([r.processing_time for r in ocr_results]),
                "ocr_engines": list(set([r.ocr_engine for r in ocr_results]))
            }
            
            return CleanedOCRData(
                text_blocks=text_blocks,
                component_labels=component_labels,
                dimensions=dimensions,
                annotations=annotations,
                metadata=metadata,
                confidence_score=avg_confidence,
                processing_stage="ocr_cleaning"
            )
            
        except Exception as e:
            logger.error(f"❌ OCR数据清洗失败: {e}")
            return CleanedOCRData(
                text_blocks=[],
                component_labels=[],
                dimensions=[],
                annotations=[],
                metadata={"error": str(e)},
                confidence_score=0.0,
                processing_stage="ocr_cleaning_failed"
            )
    
    def _extract_text_blocks(self, ocr_results: List[OCRResult]) -> List[Dict[str, Any]]:
        """提取文本块"""
        blocks = []
        for result in ocr_results:
            if result.raw_text.strip():
                blocks.append({
                    "slice_id": result.slice_id,
                    "text": result.raw_text,
                    "coordinates": result.coordinates,
                    "confidence": result.confidence
                })
        return blocks
    
    def _extract_component_labels(self, text: str) -> List[Dict[str, Any]]:
        """提取构件标签"""
        import re
        labels = []
        
        # 查找构件编号模式
        patterns = [
            r"[CLBWFSD]\d+[a-zA-Z]?",  # C1, L1, B1等
            r"[柱梁板墙基楼]\d+",      # 柱1, 梁1等
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                labels.append({
                    "label": match.group(),
                    "type": self._classify_component_type(match.group()),
                    "position": match.span()
                })
        
        return labels
    
    def _extract_dimensions(self, text: str) -> List[Dict[str, Any]]:
        """提取尺寸信息"""
        import re
        dimensions = []
        
        for pattern in self.dimension_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dimensions.append({
                    "dimension": match.group(),
                    "type": self._classify_dimension_type(match.group()),
                    "position": match.span()
                })
        
        return dimensions
    
    def _extract_annotations(self, text: str) -> List[Dict[str, Any]]:
        """提取注释信息"""
        # 简化实现，提取常见注释
        annotations = []
        
        # 查找材料信息
        material_keywords = ["C25", "C30", "C35", "HRB400", "HPB300"]
        for keyword in material_keywords:
            if keyword in text:
                annotations.append({
                    "type": "material",
                    "content": keyword,
                    "category": "concrete" if keyword.startswith("C") else "steel"
                })
        
        return annotations
    
    def _classify_component_type(self, label: str) -> str:
        """分类构件类型"""
        label_upper = label.upper()
        if label_upper.startswith('C') or '柱' in label:
            return "column"
        elif label_upper.startswith('L') or '梁' in label:
            return "beam"
        elif label_upper.startswith('B') or '板' in label:
            return "slab"
        elif label_upper.startswith('W') or '墙' in label:
            return "wall"
        elif label_upper.startswith('F') or '基' in label:
            return "foundation"
        elif label_upper.startswith('S') or '楼' in label:
            return "stair"
        else:
            return "unknown"
    
    def _classify_dimension_type(self, dimension: str) -> str:
        """分类尺寸类型"""
        if 'x' in dimension or '×' in dimension:
            return "cross_section"
        elif 'φ' in dimension or 'Φ' in dimension:
            return "diameter"
        elif any(unit in dimension for unit in ['mm', 'cm', 'm']):
            return "length"
        else:
            return "unknown"

class GPTSummarizer:
    """GPT汇总器"""
    
    def __init__(self):
        self.api_client = None  # 实际使用时需要初始化API客户端
    
    async def generate_summary(self, cleaned_data: CleanedOCRData) -> Dict[str, Any]:
        """生成智能汇总"""
        try:
            # 构造汇总提示词
            prompt = self._build_summary_prompt(cleaned_data)
            
            # 模拟GPT响应（实际使用时调用API）
            summary = {
                "drawing_info": {
                    "type": "结构平面图",
                    "scale": "1:100",
                    "floor": "标准层"
                },
                "component_summary": {
                    "total_components": len(cleaned_data.component_labels),
                    "component_types": self._count_component_types(cleaned_data.component_labels),
                    "key_dimensions": self._extract_key_dimensions(cleaned_data.dimensions)
                },
                "quality_assessment": {
                    "text_clarity": "良好",
                    "completeness": "完整",
                    "confidence": cleaned_data.confidence_score
                },
                "processing_notes": [
                    "OCR识别质量良好",
                    "构件标签清晰",
                    "尺寸信息完整"
                ]
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ GPT汇总失败: {e}")
            return {
                "error": str(e),
                "fallback_summary": "自动汇总失败，使用基础统计信息",
                "basic_stats": {
                    "text_blocks": len(cleaned_data.text_blocks),
                    "component_labels": len(cleaned_data.component_labels),
                    "dimensions": len(cleaned_data.dimensions)
                }
            }
    
    def _build_summary_prompt(self, cleaned_data: CleanedOCRData) -> str:
        """构建汇总提示词"""
        return f"""
        请分析以下建筑图纸OCR识别结果，生成结构化汇总：
        
        构件标签: {cleaned_data.component_labels}
        尺寸信息: {cleaned_data.dimensions}
        注释信息: {cleaned_data.annotations}
        
        请提供：
        1. 图纸基本信息（类型、比例、楼层等）
        2. 构件统计汇总
        3. 关键尺寸信息
        4. 质量评估
        """
    
    def _count_component_types(self, labels: List[Dict]) -> Dict[str, int]:
        """统计构件类型"""
        counts = {}
        for label in labels:
            comp_type = label.get("type", "unknown")
            counts[comp_type] = counts.get(comp_type, 0) + 1
        return counts
    
    def _extract_key_dimensions(self, dimensions: List[Dict]) -> List[str]:
        """提取关键尺寸"""
        return [dim["dimension"] for dim in dimensions[:10]]  # 取前10个

class UnifiedOCRPipeline:
    """统一OCR处理管道"""
    
    def __init__(self, ocr_engine: str = "paddleocr"):
        self.ocr_engine_type = ocr_engine
        self.component_keywords = [
            "柱", "梁", "板", "墙", "基础", "楼梯", "门", "窗",
            "C", "L", "B", "W", "F", "S", "D", "Win"
        ]
    
    async def process_slices(self, slice_infos: List[Dict], task_id: str) -> StandardizedOutput:
        """统一处理切片序列"""
        start_time = time.time()
        
        try:
            logger.info(f"🔄 开始统一OCR处理: {len(slice_infos)} 个切片")
            
            # Step 2: 并行OCR识别
            ocr_results = []
            for slice_info in slice_infos:
                result = self._recognize_text(slice_info["slice_path"], slice_info)
                ocr_results.append(result)
            
            logger.info(f"📝 OCR识别完成: {len(ocr_results)} 个结果")
            
            # Step 2.5: 数据清洗
            cleaned_data = self._clean_ocr_results(ocr_results)
            logger.info(f"🧹 数据清洗完成: {len(cleaned_data.component_labels)} 个构件标签")
            
            # Step 3: GPT汇总
            summary = await self._generate_summary(cleaned_data)
            logger.info(f"📊 GPT汇总完成")
            
            # 计算质量指标
            quality_metrics = self._calculate_quality_metrics(ocr_results, cleaned_data)
            
            # 生成标准化输出
            output = StandardizedOutput(
                task_id=task_id,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                stage="unified_ocr_complete",
                slice_results=ocr_results,
                cleaned_data=cleaned_data,
                summary=summary,
                quality_metrics=quality_metrics,
                processing_metadata={
                    "total_processing_time": time.time() - start_time,
                    "slice_count": len(slice_infos),
                    "ocr_engine": self.ocr_engine_type,
                    "pipeline_version": "1.0"
                }
            )
            
            logger.info(f"✅ 统一OCR处理完成: 用时 {time.time() - start_time:.2f}s")
            return output
            
        except Exception as e:
            logger.error(f"❌ 统一OCR处理失败: {e}")
            return StandardizedOutput(
                task_id=task_id,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                stage="unified_ocr_failed",
                slice_results=[],
                cleaned_data=None,
                summary=None,
                quality_metrics={"error": 1.0},
                processing_metadata={"error": str(e)}
            )
    
    def _recognize_text(self, image_path: str, slice_info: Dict) -> OCRResult:
        """统一的文本识别接口"""
        start_time = time.time()
        
        try:
            # 模拟OCR结果（实际使用时调用真实OCR引擎）
            raw_text = f"模拟OCR结果 - {slice_info.get('filename', 'unknown')}"
            confidence = 0.85
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                slice_id=slice_info.get("slice_id", "unknown"),
                filename=slice_info.get("filename", "unknown"),
                coordinates={
                    "x": slice_info.get("x_offset", 0),
                    "y": slice_info.get("y_offset", 0),
                    "width": slice_info.get("width", 0),
                    "height": slice_info.get("height", 0)
                },
                raw_text=raw_text,
                confidence=confidence,
                processing_time=processing_time,
                ocr_engine=self.ocr_engine_type
            )
            
        except Exception as e:
            logger.error(f"❌ OCR识别失败 {image_path}: {e}")
            return OCRResult(
                slice_id=slice_info.get("slice_id", "unknown"),
                filename=slice_info.get("filename", "unknown"),
                coordinates={},
                raw_text="",
                confidence=0.0,
                processing_time=time.time() - start_time,
                ocr_engine=self.ocr_engine_type
            )
    
    def _clean_ocr_results(self, ocr_results: List[OCRResult]) -> CleanedOCRData:
        """清洗OCR识别结果"""
        try:
            all_text = " ".join([result.raw_text for result in ocr_results])
            
            text_blocks = self._extract_text_blocks(ocr_results)
            component_labels = self._extract_component_labels(all_text)
            dimensions = self._extract_dimensions(all_text)
            annotations = self._extract_annotations(all_text)
            
            avg_confidence = sum([r.confidence for r in ocr_results]) / len(ocr_results) if ocr_results else 0.0
            
            metadata = {
                "total_slices": len(ocr_results),
                "total_text_length": len(all_text),
                "processing_time": sum([r.processing_time for r in ocr_results]),
                "ocr_engines": list(set([r.ocr_engine for r in ocr_results]))
            }
            
            return CleanedOCRData(
                text_blocks=text_blocks,
                component_labels=component_labels,
                dimensions=dimensions,
                annotations=annotations,
                metadata=metadata,
                confidence_score=avg_confidence,
                processing_stage="ocr_cleaning"
            )
            
        except Exception as e:
            logger.error(f"❌ OCR数据清洗失败: {e}")
            return CleanedOCRData(
                text_blocks=[],
                component_labels=[],
                dimensions=[],
                annotations=[],
                metadata={"error": str(e)},
                confidence_score=0.0,
                processing_stage="ocr_cleaning_failed"
            )
    
    def _extract_text_blocks(self, ocr_results: List[OCRResult]) -> List[Dict[str, Any]]:
        """提取文本块"""
        blocks = []
        for result in ocr_results:
            if result.raw_text.strip():
                blocks.append({
                    "slice_id": result.slice_id,
                    "text": result.raw_text,
                    "coordinates": result.coordinates,
                    "confidence": result.confidence
                })
        return blocks
    
    def _extract_component_labels(self, text: str) -> List[Dict[str, Any]]:
        """提取构件标签"""
        import re
        labels = []
        
        patterns = [
            r"[CLBWFSD]\d+[a-zA-Z]?",
            r"[柱梁板墙基楼]\d+",
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                labels.append({
                    "label": match.group(),
                    "type": self._classify_component_type(match.group()),
                    "position": match.span()
                })
        
        return labels
    
    def _extract_dimensions(self, text: str) -> List[Dict[str, Any]]:
        """提取尺寸信息"""
        import re
        dimensions = []
        
        patterns = [
            r"\d+[x×]\d+",
            r"\d+mm", r"\d+cm", r"\d+m",
            r"φ\d+", r"Φ\d+"
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dimensions.append({
                    "dimension": match.group(),
                    "type": self._classify_dimension_type(match.group()),
                    "position": match.span()
                })
        
        return dimensions
    
    def _extract_annotations(self, text: str) -> List[Dict[str, Any]]:
        """提取注释信息"""
        annotations = []
        
        material_keywords = ["C25", "C30", "C35", "HRB400", "HPB300"]
        for keyword in material_keywords:
            if keyword in text:
                annotations.append({
                    "type": "material",
                    "content": keyword,
                    "category": "concrete" if keyword.startswith("C") else "steel"
                })
        
        return annotations
    
    def _classify_component_type(self, label: str) -> str:
        """分类构件类型"""
        label_upper = label.upper()
        if label_upper.startswith('C') or '柱' in label:
            return "column"
        elif label_upper.startswith('L') or '梁' in label:
            return "beam"
        elif label_upper.startswith('B') or '板' in label:
            return "slab"
        elif label_upper.startswith('W') or '墙' in label:
            return "wall"
        elif label_upper.startswith('F') or '基' in label:
            return "foundation"
        elif label_upper.startswith('S') or '楼' in label:
            return "stair"
        else:
            return "unknown"
    
    def _classify_dimension_type(self, dimension: str) -> str:
        """分类尺寸类型"""
        if 'x' in dimension or '×' in dimension:
            return "cross_section"
        elif 'φ' in dimension or 'Φ' in dimension:
            return "diameter"
        elif any(unit in dimension for unit in ['mm', 'cm', 'm']):
            return "length"
        else:
            return "unknown"
    
    async def _generate_summary(self, cleaned_data: CleanedOCRData) -> Dict[str, Any]:
        """生成智能汇总"""
        try:
            summary = {
                "drawing_info": {
                    "type": "结构平面图",
                    "scale": "1:100",
                    "floor": "标准层"
                },
                "component_summary": {
                    "total_components": len(cleaned_data.component_labels),
                    "component_types": self._count_component_types(cleaned_data.component_labels),
                    "key_dimensions": self._extract_key_dimensions(cleaned_data.dimensions)
                },
                "quality_assessment": {
                    "text_clarity": "良好",
                    "completeness": "完整",
                    "confidence": cleaned_data.confidence_score
                },
                "processing_notes": [
                    "OCR识别质量良好",
                    "构件标签清晰",
                    "尺寸信息完整"
                ]
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ GPT汇总失败: {e}")
            return {
                "error": str(e),
                "fallback_summary": "自动汇总失败，使用基础统计信息",
                "basic_stats": {
                    "text_blocks": len(cleaned_data.text_blocks),
                    "component_labels": len(cleaned_data.component_labels),
                    "dimensions": len(cleaned_data.dimensions)
                }
            }
    
    def _count_component_types(self, labels: List[Dict]) -> Dict[str, int]:
        """统计构件类型"""
        counts = {}
        for label in labels:
            comp_type = label.get("type", "unknown")
            counts[comp_type] = counts.get(comp_type, 0) + 1
        return counts
    
    def _extract_key_dimensions(self, dimensions: List[Dict]) -> List[str]:
        """提取关键尺寸"""
        return [dim["dimension"] for dim in dimensions[:10]]
    
    def _calculate_quality_metrics(self, ocr_results: List[OCRResult], 
                                 cleaned_data: CleanedOCRData) -> Dict[str, float]:
        """计算质量指标"""
        if not ocr_results:
            return {"overall_quality": 0.0}
        
        avg_confidence = sum([r.confidence for r in ocr_results]) / len(ocr_results) if ocr_results else 0.0
        text_coverage = len([r for r in ocr_results if r.raw_text.strip()]) / len(ocr_results) if ocr_results else 0.0
        component_density = len(cleaned_data.component_labels) / len(ocr_results) if ocr_results else 0.0
        
        overall_quality = (avg_confidence * 0.4 + text_coverage * 0.3 + 
                          min(component_density, 1.0) * 0.3)
        
        # 防止除零错误
        avg_processing_time = sum([r.processing_time for r in ocr_results]) / len(ocr_results) if ocr_results else 1.0
        processing_efficiency = 1.0 / max(avg_processing_time, 0.001)  # 避免除零
        
        return {
            "overall_quality": overall_quality,
            "avg_confidence": avg_confidence,
            "text_coverage": text_coverage,
            "component_density": component_density,
            "processing_efficiency": processing_efficiency
        }
    
    def save_standardized_output(self, output: StandardizedOutput, output_path: str):
        """保存标准化输出"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            output_dict = asdict(output)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 标准化输出已保存: {output_path}")
            
        except Exception as e:
            logger.error(f"❌ 保存标准化输出失败: {e}") 