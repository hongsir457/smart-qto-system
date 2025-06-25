# -*- coding: utf-8 -*-
"""
全图概览管理器：负责全图OCR智能分析、自然语言解析、结果复用等
"""
import logging
from typing import Dict, Any
import re
import json
import os

logger = logging.getLogger(__name__)

class GlobalOverviewManager:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def extract_global_ocr_overview_optimized(self, drawing_info: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        try:
            from app.utils.analysis_optimizations import GPTResponseParser, AnalysisLogger
            from app.services.ocr_result_corrector import OCRResultCorrector
            start_time = self.analyzer.time.time()
            AnalysisLogger.log_step("global_ocr_overview", "开始全图OCR概览分析")
            text_regions = []
            for slice_info in self.analyzer.enhanced_slices:
                if slice_info.ocr_results:
                    for item in slice_info.ocr_results:
                        text_regions.append({
                            "text": item.text,
                            "bbox": getattr(item, "bbox", None) or getattr(item, "position", None)
                        })
            if not text_regions:
                return {"success": False, "error": "没有OCR文本可分析"}
            try:
                sorted_regions = sorted(text_regions, key=lambda x: (
                    x.get("bbox", [0, 0, 0, 0])[1],
                    x.get("bbox", [0, 0, 0, 0])[0]
                ))
                ocr_plain_text = '\n'.join([r["text"] for r in sorted_regions if r.get("text", "").strip()])
            except Exception as e:
                logger.warning(f"⚠️ 文本排序失败，使用简单拼接: {e}")
                ocr_plain_text = '\n'.join([r["text"] for r in text_regions if r.get("text", "").strip()])
            lines = ocr_plain_text.splitlines()
            logger.info(f"📋 全图文本概览（前5行）: {' | '.join(lines[:5])}")
            logger.info(f"📋 全图文本概览（后5行）: {' | '.join(lines[-5:])}")
            analysis_prompt = self.build_global_overview_prompt(ocr_plain_text, drawing_info)
            if not self.analyzer.ai_analyzer:
                return {"success": False, "error": "AI分析器未初始化"}
            parser = GPTResponseParser()
            response = self.analyzer.ai_analyzer.analyze_with_context(
                prompt=analysis_prompt,
                context_type="global_overview",
                task_id=task_id
            )
            if not response.get("success"):
                return {"success": False, "error": response.get("error", "AI分析失败")}
            try:
                raw_analysis = response.get("analysis", "")
                overview_data = self.parse_natural_language_overview(raw_analysis)
                if not overview_data:
                    return {"success": False, "error": "响应解析失败 - 无法解析自然语言响应"}
            except Exception as parse_e:
                logger.error(f"自然语言响应解析失败: {parse_e}")
                return {"success": False, "error": f"响应解析失败: {parse_e}"}
            processing_time = self.analyzer.time.time() - start_time
            AnalysisLogger.log_step("global_overview_completed", f"全图概览完成，耗时{processing_time:.2f}s")
            return {
                "success": True,
                "overview": overview_data,
                "ocr_text_count": len(lines),
                "processing_time": processing_time
            }
        except Exception as e:
            logger.error(f"❌ 全图OCR概览分析失败: {e}")
            return {"success": False, "error": str(e)}

    def build_global_overview_prompt(self, ocr_plain_text: str, drawing_info: Dict[str, Any]) -> str:
        prompt = f"""
你是一位专业的建筑工程量计算专家。请分析以下从建筑图纸中提取的OCR文本（已按顺序排序、相邻合并），并提供结构化的全图概览信息。

图纸信息：
- 文件名：{drawing_info.get('drawing_name', '未知')}
- 图纸类型：{drawing_info.get('drawing_type', '建筑图纸')}

OCR提取的纯文本内容：
{ocr_plain_text[:4000]}
{'...(文本过长，已截断)' if len(ocr_plain_text) > 4000 else ''}

请按以下**自然语言格式**简洁地总结分析结果（注意：不要返回JSON格式，直接用自然语言描述）：

**图纸基本信息：**
- 工程名称：[识别出的工程名称]
- 图纸类型：[具体的图纸类型，如结构平面图、配筋图等]
- 图纸比例：[识别出的比例，如1:100等]
- 图纸编号：[识别出的图纸编号]

**构件概览：**
- 主要构件编号：[列出关键的构件编号，如KL1、Z1、B1等，限制在10个以内]
- 构件类型：[如框架梁、柱、板、墙等]
- 材料等级：[如C30、HRB400等]
- 轴线编号：[如A、B、C、1、2、3等，限制在8个以内]

**图纸特点：**
- 构件总数估计：[大致的构件数量]
- 主要结构类型：[如框架结构、剪力墙结构等]
- 复杂程度：[简单/中等/复杂]

要求：
1. 用简洁的自然语言描述，不要冗长
2. 重点提取工程量计算相关的关键信息
3. 如果某些信息无法识别，标注为"未识别"
4. 总字数控制在500字以内
5. 严格按照上述格式输出，便于后续解析
"""
        return prompt

    def parse_natural_language_overview(self, raw_analysis: str) -> Dict[str, Any]:
        try:
            overview_data = {
                "drawing_info": {},
                "component_ids": [],
                "component_types": [],
                "material_grades": [],
                "axis_lines": [],
                "summary": {},
                "natural_language_summary": raw_analysis[:500]
            }
            if not raw_analysis or len(raw_analysis.strip()) < 10:
                return overview_data
            project_name_match = re.search(r'工程名称[：:]\s*([^\n\r]+)', raw_analysis, re.IGNORECASE)
            if project_name_match:
                overview_data["drawing_info"]["project_name"] = project_name_match.group(1).strip()
            drawing_type_match = re.search(r'图纸类型[：:]\s*([^\n\r]+)', raw_analysis, re.IGNORECASE)
            if drawing_type_match:
                overview_data["drawing_info"]["drawing_type"] = drawing_type_match.group(1).strip()
            scale_match = re.search(r'图纸比例[：:]\s*([^\n\r]+)', raw_analysis, re.IGNORECASE)
            if scale_match:
                overview_data["drawing_info"]["scale"] = scale_match.group(1).strip()
            drawing_number_match = re.search(r'图纸编号[：:]\s*([^\n\r]+)', raw_analysis, re.IGNORECASE)
            if drawing_number_match:
                overview_data["drawing_info"]["drawing_number"] = drawing_number_match.group(1).strip()
            component_patterns = [r'\b[A-Z]{1,2}\d{1,4}\b', r'\b[A-Z]\d+-\d+\b', r'\b\d+[A-Z]{1,2}\b']
            for pattern in component_patterns:
                matches = re.findall(pattern, raw_analysis, re.IGNORECASE)
                for match in matches:
                    if match.upper() not in overview_data["component_ids"]:
                        overview_data["component_ids"].append(match.upper())
            overview_data["component_ids"] = overview_data["component_ids"][:10]
            type_keywords = ['框架梁', '柱', '板', '墙', '基础', '楼梯', '梁', '柱子', '墙体', '楼板']
            for keyword in type_keywords:
                if keyword in raw_analysis and keyword not in overview_data["component_types"]:
                    overview_data["component_types"].append(keyword)
            material_patterns = [r'\bC\d{2}\b', r'\bHRB\d{3}\b', r'\bQ\d{3}\b', r'\bMU\d{1,2}\b']
            for pattern in material_patterns:
                matches = re.findall(pattern, raw_analysis, re.IGNORECASE)
                for match in matches:
                    if match.upper() not in overview_data["material_grades"]:
                        overview_data["material_grades"].append(match.upper())
            axis_patterns = [r'\b[A-Z]-[A-Z]\b', r'\b\d+-\d+\b', r'\b[A-Z]\d*\b', r'\b\d+\b']
            for pattern in axis_patterns:
                matches = re.findall(pattern, raw_analysis)
                for match in matches:
                    if len(match) <= 3 and match not in overview_data["axis_lines"]:
                        overview_data["axis_lines"].append(match)
            overview_data["axis_lines"] = overview_data["axis_lines"][:8]
            total_components_match = re.search(r'构件总数[：:]?\s*(\d+)', raw_analysis, re.IGNORECASE)
            if total_components_match:
                overview_data["summary"]["total_components"] = int(total_components_match.group(1))
            else:
                overview_data["summary"]["total_components"] = len(overview_data["component_ids"])
            structure_type_match = re.search(r'主要结构类型[：:]\s*([^\n\r]+)', raw_analysis, re.IGNORECASE)
            if structure_type_match:
                overview_data["summary"]["main_structure_type"] = structure_type_match.group(1).strip()
            complexity_match = re.search(r'复杂程度[：:]\s*([^\n\r]+)', raw_analysis, re.IGNORECASE)
            if complexity_match:
                overview_data["summary"]["drawing_complexity"] = complexity_match.group(1).strip()
            logger.info(f"✅ 自然语言解析完成: {len(overview_data['component_ids'])} 个构件编号, {len(overview_data['component_types'])} 种构件类型")
            return overview_data
        except Exception as e:
            logger.error(f"❌ 自然语言解析失败: {e}")
            return {
                "drawing_info": {},
                "component_ids": [],
                "component_types": [],
                "material_grades": [],
                "axis_lines": [],
                "summary": {},
                "natural_language_summary": raw_analysis[:500] if raw_analysis else ""
            }

    def reuse_ocr_analysis_overview(self, shared_slice_results: Dict[str, Any], image_path: str) -> Dict[str, Any]:
        try:
            slice_info = shared_slice_results.get(image_path)
            if not slice_info:
                image_name = os.path.basename(image_path)
                for path, info in shared_slice_results.items():
                    if os.path.basename(path) == image_name:
                        slice_info = info
                        break
            if not slice_info:
                return {"success": False, "error": "在共享结果中未找到OCR分析数据"}
            ocr_analysis_result = None
            if hasattr(slice_info, 'analyzed_result') and slice_info.analyzed_result:
                ocr_analysis_result = slice_info.analyzed_result
            elif isinstance(slice_info, dict) and 'analyzed_result' in slice_info:
                ocr_analysis_result = slice_info['analyzed_result']
            if not ocr_analysis_result:
                if hasattr(slice_info, 'gpt_analysis') and slice_info.gpt_analysis:
                    ocr_analysis_result = slice_info.gpt_analysis
                elif isinstance(slice_info, dict) and 'gpt_analysis' in slice_info:
                    ocr_analysis_result = slice_info['gpt_analysis']
            if not ocr_analysis_result:
                if hasattr(slice_info, 'ocr_corrected_result') and slice_info.ocr_corrected_result:
                    ocr_analysis_result = slice_info.ocr_corrected_result
                elif isinstance(slice_info, dict) and 'ocr_corrected_result' in slice_info:
                    ocr_analysis_result = slice_info['ocr_corrected_result']
            if not ocr_analysis_result:
                return {"success": False, "error": "在共享结果中未找到OCR智能分析结果"}
            overview_data = self.extract_overview_from_ocr_analysis(ocr_analysis_result)
            if overview_data:
                logger.info(f"✅ 成功复用OCR智能分析结果")
                return {
                    "success": True,
                    "overview": overview_data
                }
            else:
                return {"success": False, "error": "OCR智能分析结果格式不正确"}
        except Exception as e:
            logger.error(f"❌ 复用OCR智能分析结果失败: {e}")
            return {"success": False, "error": str(e)}

    def extract_overview_from_ocr_analysis(self, ocr_analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            overview_data = {
                "drawing_info": {},
                "component_ids": [],
                "component_types": [],
                "material_grades": [],
                "axis_lines": [],
                "summary": {},
                "natural_language_summary": ""
            }
            if isinstance(ocr_analysis_result, dict):
                if ocr_analysis_result.get('natural_language_summary'):
                    overview_data["natural_language_summary"] = ocr_analysis_result['natural_language_summary']
                    logger.info("✅ 使用自然语言摘要格式的OCR分析结果")
                    summary_text = ocr_analysis_result['natural_language_summary']
                    if "图纸信息：" in summary_text:
                        lines = summary_text.split('\n')
                        for line in lines:
                            if line.startswith('图纸信息：'):
                                info_text = line.replace('图纸信息：', '').strip()
                                info_parts = info_text.split(' ')
                                if len(info_parts) >= 1:
                                    overview_data["drawing_info"]["drawing_type"] = info_parts[0]
                                if len(info_parts) >= 2:
                                    overview_data["drawing_info"]["project_name"] = info_parts[1]
                                if len(info_parts) >= 3:
                                    overview_data["drawing_info"]["scale"] = info_parts[2]
                                break
                    return overview_data
                drawing_info = ocr_analysis_result.get('drawing_basic_info', {})
                if drawing_info:
                    overview_data["drawing_info"] = {
                        "project_name": drawing_info.get('project_name', ''),
                        "drawing_type": drawing_info.get('drawing_type', ''),
                        "scale": drawing_info.get('scale', ''),
                        "drawing_number": drawing_info.get('drawing_number', '')
                    }
                components = ocr_analysis_result.get('component_list', [])
                for comp in components:
                    if isinstance(comp, dict):
                        comp_id = comp.get('component_id', '')
                        comp_type = comp.get('component_type', '')
                        material = comp.get('material', '')
                        if comp_id and comp_id not in overview_data["component_ids"]:
                            overview_data["component_ids"].append(comp_id)
                        if comp_type and comp_type not in overview_data["component_types"]:
                            overview_data["component_types"].append(comp_type)
                        if material and material not in overview_data["material_grades"]:
                            overview_data["material_grades"].append(material)
                axes = ocr_analysis_result.get('axes', [])
                if isinstance(axes, list):
                    overview_data["axis_lines"] = axes[:8]
                overview_data["summary"] = {
                    "total_components": len(overview_data["component_ids"]),
                    "main_structure_type": ocr_analysis_result.get('structure_type', ''),
                    "drawing_complexity": ocr_analysis_result.get('complexity', '')
                }
                overview_data["natural_language_summary"] = self.generate_summary_from_analysis(overview_data)
            return overview_data
        except Exception as e:
            logger.error(f"❌ 提取概览数据失败: {e}")
            return {}

    def generate_summary_from_analysis(self, overview_data: Dict[str, Any]) -> str:
        try:
            summary_parts = []
            drawing_info = overview_data.get("drawing_info", {})
            if drawing_info.get("project_name"):
                summary_parts.append(f"工程名称：{drawing_info['project_name']}")
            if drawing_info.get("drawing_type"):
                summary_parts.append(f"图纸类型：{drawing_info['drawing_type']}")
            if drawing_info.get("scale"):
                summary_parts.append(f"图纸比例：{drawing_info['scale']}")
            component_ids = overview_data.get("component_ids", [])
            if component_ids:
                summary_parts.append(f"主要构件编号：{', '.join(component_ids[:10])}")
            component_types = overview_data.get("component_types", [])
            if component_types:
                summary_parts.append(f"构件类型：{', '.join(component_types)}")
            material_grades = overview_data.get("material_grades", [])
            if material_grades:
                summary_parts.append(f"材料等级：{', '.join(material_grades)}")
            summary_info = overview_data.get("summary", {})
            if summary_info.get("total_components"):
                summary_parts.append(f"构件总数估计：{summary_info['total_components']}")
            return "；".join(summary_parts)
        except Exception as e:
            logger.error(f"❌ 生成自然语言摘要失败: {e}")
            return "无法生成摘要" 