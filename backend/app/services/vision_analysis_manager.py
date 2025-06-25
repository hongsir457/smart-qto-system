# -*- coding: utf-8 -*-
"""
Vision分析管理器：负责基于OCR增强提示的Vision分析、单切片Vision推理、结果解析等
"""
import logging
from typing import Dict, Any, List
import base64
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)

class VisionAnalysisManager:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def analyze_slices_with_enhanced_vision(self, drawing_info: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Step 4: 基于OCR增强提示的Vision分析（支持切片范围限制）"""
        if not self.analyzer.ai_analyzer or not self.analyzer.ai_analyzer.is_available():
            return {"success": False, "error": "AI分析器不可用"}
        try:
            analyzed_count = 0
            enhanced_analysis_count = 0
            failed_count = 0
            skipped_count = 0
            slice_range = drawing_info.get('slice_range', {})
            slice_indices = slice_range.get('slice_indices', [])
            vision_cache = getattr(self.analyzer, '_vision_cache', {})
            for i, slice_info in enumerate(self.analyzer.enhanced_slices):
                if slice_indices and i not in slice_indices:
                    skipped_count += 1
                    logger.debug(f"⏭️ 跳过切片 {slice_info.row}_{slice_info.col} (不在当前批次范围)")
                    continue
                cache_key = f"{slice_info.row}_{slice_info.col}"
                if cache_key in vision_cache:
                    self.analyzer.slice_components[cache_key] = vision_cache[cache_key]
                    analyzed_count += 1
                    logger.info(f"♻️ 复用切片 {cache_key} 的Vision分析结果: {len(vision_cache[cache_key])} 个构件")
                    continue
                logger.info(f"👁️ Vision分析切片 {slice_info.row}_{slice_info.col}")
                if slice_info.enhanced_prompt:
                    prompt = slice_info.enhanced_prompt
                    enhanced_analysis_count += 1
                else:
                    prompt = self.generate_basic_vision_prompt(slice_info, drawing_info)
                vision_result = self.analyze_single_slice_with_vision(
                    slice_info, prompt, f"{task_id}_vision_{slice_info.row}_{slice_info.col}"
                )
                if vision_result["success"]:
                    components = self.parse_vision_components(vision_result["data"], slice_info)
                    self.analyzer.slice_components[f"{slice_info.row}_{slice_info.col}"] = components
                    analyzed_count += 1
                    logger.info(f"✅ 切片 {slice_info.row}_{slice_info.col} Vision分析成功: {len(components)} 个构件")
                else:
                    logger.error(f"❌ 切片 {slice_info.row}_{slice_info.col} Vision分析失败: {vision_result.get('error')}")
                    self.analyzer.slice_components[f"{slice_info.row}_{slice_info.col}"] = []
                    failed_count += 1
            total = len(self.analyzer.enhanced_slices)
            success_rate = analyzed_count / total if total else 0
            enhancement_rate = enhanced_analysis_count / total if total else 0
            logger.info(f"📊 Vision分析完成: 成功 {analyzed_count}/{total} ({success_rate:.1%})")
            logger.info(f"📈 OCR增强率: {enhanced_analysis_count}/{total} ({enhancement_rate:.1%})")
            return {
                "success": True,
                "statistics": {
                    "analyzed_slices": analyzed_count,
                    "enhanced_slices": enhanced_analysis_count,
                    "failed_slices": failed_count,
                    "success_rate": success_rate,
                    "enhancement_rate": enhancement_rate
                }
            }
        except Exception as e:
            logger.error(f"❌ Vision分析失败: {e}")
            return {"success": False, "error": str(e)}

    def generate_basic_vision_prompt(self, slice_info, drawing_info: Dict[str, Any]) -> str:
        tile_pos = f"第{slice_info.row}行第{slice_info.col}列"
        prompt_parts = []
        overview = getattr(self.analyzer, 'global_drawing_overview', None)
        if overview:
            prompt_parts.append("🌍 全图概览信息：")
            if overview.get('natural_language_summary'):
                prompt_parts.append("【全图分析摘要】")
                prompt_parts.append(overview['natural_language_summary'])
                prompt_parts.append("")
            else:
                drawing_info_overview = overview.get('drawing_info', {})
                if drawing_info_overview:
                    prompt_parts.append(f"- 图纸类型: {drawing_info_overview.get('drawing_type', '未知')}")
                    prompt_parts.append(f"- 工程名称: {drawing_info_overview.get('project_name', '未知')}")
                    prompt_parts.append(f"- 图纸比例: {drawing_info_overview.get('scale', '未知')}")
                component_ids = overview.get('component_ids', [])
                if component_ids:
                    prompt_parts.append(f"- 全图构件编号: {', '.join(component_ids[:10])}{'...' if len(component_ids) > 10 else ''}")
                component_types = overview.get('component_types', [])
                if component_types:
                    prompt_parts.append(f"- 主要构件类型: {', '.join(component_types)}")
                material_grades = overview.get('material_grades', [])
                if material_grades:
                    prompt_parts.append(f"- 材料等级: {', '.join(material_grades)}")
                prompt_parts.append("")
        prompt_parts.append(f"📄 当前图像为结构图切片（{tile_pos}）")
        prompt_parts.append(f"图纸比例：{drawing_info.get('scale', '1:100')}，图号 {drawing_info.get('drawing_number', 'Unknown')}")
        prompt_parts.append("")
        prompt_parts.append("请进行构件几何识别分析（重点：形状和尺寸，非文本）：")
        prompt_parts.append("- 识别构件几何形状：梁（矩形）、柱（圆形/方形）、板（面状）、墙（线状）")
        prompt_parts.append("- 测量构件精确尺寸：长度、宽度、高度、厚度（基于图纸比例）")
        prompt_parts.append("- 确定构件空间位置：边界框坐标、轴线位置")
        prompt_parts.append("- 分析构件连接关系：与其他构件的连接和支撑")
        prompt_parts.append("- 计算工程量参数：面积、体积等几何数据")
        prompt_parts.append("")
        prompt_parts.append("注意：专注构件的几何特征识别，为工程量计算提供数据")
        prompt_parts.append("返回JSON格式，包含详细的几何参数和工程量数据。")
        return "\n".join(prompt_parts)

    def analyze_single_slice_with_vision(self, slice_info, prompt: str, vision_task_id: str) -> Dict[str, Any]:
        try:
            with open(slice_info.slice_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            system_prompt = """你是专业的结构工程师，专门分析建筑结构图纸。\n\n双轨协同分析要求：\n1. 📝 OCR轨道：OCR已提供文本信息（构件编号、尺寸、材料等）\n2. 👁️ Vision轨道：专注识别构件的几何形状、空间位置、连接关系、结构特征\n3. 🔀 协同验证：将OCR文本与Vision识别的构件进行匹配和验证\n4. 📊 工程量导向：为工程量计算提供准确的构件几何数据\n\nVision分析重点（构件识别，非文本识别）：\n- 构件几何形状：矩形梁、圆形柱、板块轮廓、墙体边界等\n- 构件空间位置：在图纸中的精确坐标和边界框\n- 构件尺寸测量：基于图纸比例的实际尺寸计算\n- 构件连接关系：梁柱连接、板梁支撑、墙体交接等\n- 构件结构特征：配筋方向、开洞位置、节点详情等\n\n工程量计算所需数据：\n- 精确的构件边界框（用于面积/体积计算）\n- 构件的几何参数（长、宽、高、厚度等）\n- 构件在结构中的作用（承重、围护、装饰等）\n- 构件的材料属性（混凝土、钢筋、砌体等）\n\n🔧 边界框格式要求：\nbbox字段必须为 {\"x\": 数值, \"y\": 数值, \"width\": 数值, \"height\": 数值} 格式\n其中 x, y 为左上角坐标（像素），width, height 为宽度和高度（像素）\n\n请严格按照以下JSON格式返回：\n{\n  \"components\": [\n    {\n      \"component_id\": \"构件编号（来自OCR）\",\n      \"component_type\": \"构件类型（基于Vision识别的几何形状）\",\n      \"geometry\": {\n        \"shape\": \"几何形状（矩形/圆形/多边形等）\",\n        \"dimensions\": {\n          \"length\": \"长度（mm）\",\n          \"width\": \"宽度（mm）\", \n          \"height\": \"高度（mm）\",\n          \"thickness\": \"厚度（mm）\"\n        },\n        \"area\": \"面积（m²）\",\n        \"volume\": \"体积（m³）\"\n      },\n      \"material\": \"材料等级（来自OCR）\",\n      \"location\": {\n        \"coordinates\": \"轴线位置\",\n        \"bbox\": {\"x\": 数值, \"y\": 数值, \"width\": 数值, \"height\": 数值},\n        \"floor_level\": \"楼层标高\"\n      },\n      \"structural_role\": \"结构作用（承重/围护/装饰）\",\n      \"connections\": [\"连接的其他构件ID\"],\n      \"confidence\": 0.95,\n      \"ocr_match\": \"匹配的OCR文本\",\n      \"vision_features\": \"Vision识别的关键特征\"\n    }\n  ]\n}"""
            user_content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}", "detail": "high"}}
            ]
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=2000,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            response_text = response.choices[0].message.content
            import json
            try:
                data = json.loads(response_text)
            except Exception as e:
                logger.error(f"Vision响应解析JSON失败: {e}, 原始内容: {response_text}")
                data = {"components": []}
            return {"success": True, "data": data, "raw_response": response_text, "analysis_method": "dual_track_vision"}
        except Exception as e:
            logger.error(f"❌ 双轨协同Vision分析失败: {e}")
            return {"success": False, "error": str(e)}

    def parse_vision_components(self, vision_data: Dict[str, Any], slice_info) -> List:
        from app.schemas.component import DrawingComponent
        components_from_vision = []
        raw_components = vision_data.get("components", [])
        if not raw_components:
            logger.warning(f"切片 {slice_info.filename} 的Vision分析未返回任何构件")
            return []
        for i, comp_data in enumerate(raw_components):
            try:
                component_id_str = comp_data.get("component_id", f"unknown_{slice_info.filename}_{i}")
                component_type_str = comp_data.get("component_type", "未知")
                bbox_raw = comp_data.get("location", {}).get("bbox", None)
                bbox_local = None
                if isinstance(bbox_raw, dict) and all(k in bbox_raw for k in ["x", "y", "width", "height"]):
                    bbox_local = [bbox_raw["x"], bbox_raw["y"], bbox_raw["width"], bbox_raw["height"]]
                elif isinstance(bbox_raw, list) and len(bbox_raw) == 4:
                    bbox_local = bbox_raw
                if not bbox_local or not isinstance(bbox_local, list) or len(bbox_local) != 4:
                    logger.warning(f"构件 {component_id_str} 缺少有效的bbox，尝试生成默认值")
                    bbox_local = [0, 0, 100, 50]
                preliminary_component = {
                    "id": f"{slice_info.filename}_{component_id_str}",
                    "component_type": component_type_str,
                    "component_id": component_id_str,
                    "position": {
                        "slice_id": slice_info.filename,
                        "bbox_local": tuple(bbox_local),
                        "bbox_global": (0, 0, 0, 0)
                    },
                    "source_modules": ["Vision"],
                    "confidence": {
                        "vision_confidence": comp_data.get("confidence", 0.8),
                        "fusion_confidence": comp_data.get("confidence", 0.8)
                    },
                    "floor": vision_data.get("drawing_info", {}).get("floor_level"),
                    "drawing_name": vision_data.get("drawing_info", {}).get("title"),
                    "raw_vision_data": comp_data
                }
                components_from_vision.append(preliminary_component)
                logger.debug(f"✅ 成功解析构件 {component_id_str}，bbox: {bbox_local}")
            except Exception as e:
                logger.error(f"解析Vision构件时出错: {e} - 数据: {comp_data}")
                continue
        logger.info(f"切片 {slice_info.filename} 解析出 {len(components_from_vision)} 个构件")
        return components_from_vision 