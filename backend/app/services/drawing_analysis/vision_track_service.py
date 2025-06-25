import logging
import json
import re
import base64
from typing import Dict, Any, List, Optional

import openai

from app.core.config import settings
from ..enhanced_slice_models import EnhancedSliceInfo, OCRTextItem
from ...schemas.component import DrawingComponent, ComponentPosition, ComponentConfidence
from ..ai_analyzer import AIAnalyzerService

logger = logging.getLogger(__name__)


class VisionTrackService:
    """
    Vision轨道服务
    负责Vision轨道2的全流程：OCR增强、调用Vision模型分析、解析构件。
    """

    def __init__(self, ai_analyzer: AIAnalyzerService):
        """
        初始化Vision轨道服务
        
        Args:
            ai_analyzer: AI分析器实例
        """
        self.ai_analyzer = ai_analyzer
        self.component_patterns = self._default_component_patterns()
        self.vision_cache = {} # 可选的内存缓存

    def analyze_slices(self, 
                       enhanced_slices: List[EnhancedSliceInfo], 
                       global_overview: str,
                       drawing_info: Dict[str, Any], 
                       task_id: str) -> Dict[str, Any]:
        """
        对所有切片执行Vision分析（轨道2）
        
        Args:
            enhanced_slices: 增强切片列表
            global_overview: 全局概览信息 (来自OCR轨道1，现在是纯文本字符串)
            drawing_info: 原始图纸信息
            task_id: 任务ID
            
        Returns:
            包含所有切片分析结果的字典
        """
        try:
            # 1. OCR智能分类与增强提示生成
            self._enhance_slices_with_ocr(enhanced_slices, global_overview)
            
            # 2. 循环分析每个切片
            slice_components = {}
            analyzed_count = 0
            failed_count = 0

            for slice_info in enhanced_slices:
                cache_key = f"{slice_info.row}_{slice_info.col}"
                if cache_key in self.vision_cache:
                    slice_components[cache_key] = self.vision_cache[cache_key]
                    analyzed_count += 1
                    logger.info(f"♻️ 复用切片 {cache_key} 的Vision分析结果")
                    continue

                logger.info(f"👁️ Vision分析切片 {slice_info.row}_{slice_info.col}")
                
                prompt = slice_info.enhanced_prompt or self._generate_basic_vision_prompt(slice_info, global_overview, drawing_info)
                
                vision_result = self._analyze_single_slice(
                    slice_info, prompt, f"{task_id}_vision_{slice_info.row}_{slice_info.col}"
                )
                
                if vision_result["success"]:
                    components = self._parse_vision_components(vision_result["data"], slice_info)
                    slice_components[cache_key] = components
                    self.vision_cache[cache_key] = components # 缓存结果
                    analyzed_count += 1
                else:
                    slice_components[cache_key] = []
                    failed_count += 1
            
            return {"success": True, "slice_components": slice_components}

        except Exception as e:
            logger.error(f"❌ Vision轨道分析失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _enhance_slices_with_ocr(self, enhanced_slices: List[EnhancedSliceInfo], global_overview: str):
        """OCR智能分类与增强提示生成"""
        for slice_info in enhanced_slices:
            if not slice_info.ocr_results:
                continue
            self._classify_ocr_texts(slice_info.ocr_results)
            slice_info.enhanced_prompt = self._generate_enhanced_prompt(slice_info, global_overview)

    def _classify_ocr_texts(self, ocr_results: List[OCRTextItem]):
        """对OCR文本进行智能分类"""
        for ocr_item in ocr_results:
            text = ocr_item.text.strip()
            for category, patterns in self.component_patterns.items():
                if any(re.match(p, text, re.IGNORECASE) for p in patterns):
                    ocr_item.category = category
                    break

    def _generate_enhanced_prompt(self, slice_info: EnhancedSliceInfo, global_overview: str) -> str:
        """生成OCR增强的Vision分析提示"""
        prompt_parts = [f"📄 当前图像为结构图切片（第{slice_info.row}行第{slice_info.col}列）"]
        
        # 添加全局概览信息 (现在是纯文本)
        if global_overview:
            prompt_parts.append("\n🌍 以下是作为参考的全图概览分析报告：")
            prompt_parts.append("---")
            prompt_parts.append(global_overview)
            prompt_parts.append("---")

        # 添加单切片OCR信息
        categorized_items = {}
        for item in slice_info.ocr_results:
            categorized_items.setdefault(item.category, []).append(item.text)
        
        if categorized_items:
            prompt_parts.append("\n🔍 当前切片OCR识别信息：")
            for category, texts in categorized_items.items():
                if category != "unknown":
                    prompt_parts.append(f"- {category}: {', '.join(texts)}")

        prompt_parts.append("\n👁️ Vision构件识别要求：请识别构件几何形状、尺寸和位置。")
        return "\n".join(prompt_parts)

    def _generate_basic_vision_prompt(self, slice_info: EnhancedSliceInfo, global_overview: Dict, drawing_info: Dict) -> str:
        """生成基础Vision分析提示"""
        return self._generate_enhanced_prompt(slice_info, global_overview) # 复用逻辑

    def _analyze_single_slice(self, slice_info: EnhancedSliceInfo, prompt: str, vision_task_id: str) -> Dict[str, Any]:
        """执行单个切片的Vision分析"""
        try:
            with open(slice_info.slice_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            system_prompt = "你是专业的结构工程师，专门分析建筑结构图纸。请识别构件的几何形状、空间位置、尺寸，并以指定的JSON格式返回。"
            
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}", "detail": "high"}}
                    ]}
                ],
                max_tokens=2000,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            response_text = response.choices[0].message.content
            result_data = json.loads(response_text)
            return {"success": True, "data": result_data}
        except Exception as e:
            logger.error(f"❌ 切片Vision分析API调用失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _parse_vision_components(self, vision_data: Dict[str, Any], slice_info: EnhancedSliceInfo) -> List[Dict]:
        """从Vision API的响应中解析构件列表"""
        components = []
        raw_components = vision_data.get("components", [])
        for i, comp_data in enumerate(raw_components):
            try:
                bbox_local_raw = comp_data.get("location", {}).get("bbox", [0, 0, 0, 0])
                if isinstance(bbox_local_raw, dict):
                     bbox_local = [bbox_local_raw.get('x',0), bbox_local_raw.get('y',0), bbox_local_raw.get('width',0), bbox_local_raw.get('height',0)]
                else:
                     bbox_local = bbox_local_raw

                component = {
                    "id": f"{slice_info.filename}_{comp_data.get('component_id', f'comp_{i}')}",
                    "component_type": comp_data.get("component_type", "未知"),
                    "component_id": comp_data.get("component_id"),
                    "position": {
                        "slice_id": slice_info.filename,
                        "bbox_local": tuple(bbox_local),
                        "bbox_global": (0, 0, 0, 0) # 占位符
                    },
                    "source_modules": ["Vision"],
                    "confidence": {"vision_confidence": comp_data.get("confidence", 0.8)},
                    "raw_vision_data": comp_data
                }
                components.append(component)
            except Exception as e:
                logger.error(f"解析Vision构件时出错: {e} - 数据: {comp_data}")
                continue
        return components

    def _default_component_patterns(self) -> Dict[str, List[str]]:
        return {
            'component_id': [r'^[A-Z]{1,2}\d{2,4}$', r'^[A-Z]{1,2}-\d{1,3}$'],
            'dimension': [r'^\d{2,4}[xX×]\d{2,4}', r'^[bBhH]?\d{2,4}$'],
            'material': [r'^C\d{2}$', r'^HRB\d{3}$'],
            'axis': [r'^[A-Z]-[A-Z]$', r'^\d+-\d+$']
        } 