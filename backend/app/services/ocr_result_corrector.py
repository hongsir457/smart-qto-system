#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR结果智能纠正服务
用于在PaddleOCR合并后对结果进行智能纠正、文本对齐、匹配优化等处理
基于建筑工程行业字典、坐标位置等信息进行GPT纠正
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import re
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CorrectedOCRResult:
    """纠正后的OCR结果"""
    task_id: str
    original_result_key: str
    corrected_result_key: str
    
    # 纠正前后对比
    original_stats: Dict[str, Any]
    corrected_stats: Dict[str, Any]
    
    # 纠正后的内容
    drawing_basic_info: Dict[str, Any]          # 图纸基本信息
    component_list: List[Dict[str, Any]]        # 构件清单及基本属性
    global_notes: List[Dict[str, Any]]          # 全局说明备注文本
    text_regions_corrected: List[Dict[str, Any]] # 纠正后的文本区域
    
    # 纠正处理信息
    correction_summary: Dict[str, Any]
    processing_metadata: Dict[str, Any]
    timestamp: float

class OCRResultCorrector:
    """OCR结果智能纠正器"""
    
    def __init__(self, ai_analyzer=None, storage_service=None):
        self.ai_analyzer = ai_analyzer
        self.storage_service = storage_service
        
        # 建筑工程行业词典
        self.construction_dictionary = self._load_construction_dictionary()
        
        # 常见OCR错误模式
        self.ocr_error_patterns = self._load_ocr_error_patterns()
    
    def _load_construction_dictionary(self) -> Dict[str, List[str]]:
        """加载建筑工程行业词典"""
        return {
            "component_types": [
                "梁", "柱", "板", "墙", "基础", "楼梯", "屋面", "门", "窗",
                "KL", "KZ", "KB", "KQ", "JC", "LT", "WM", "M", "C",
                "框架梁", "框架柱", "框架板", "剪力墙", "条形基础", "独立基础"
            ],
            "materials": [
                "C20", "C25", "C30", "C35", "C40", "C50",
                "HRB400", "HRB500", "HPB300",
                "MU10", "MU15", "MU20", "M5", "M7.5", "M10"
            ],
            "dimensions": [
                "×", "x", "*", "mm", "m", "长", "宽", "高", "厚",
                "直径", "半径", "深度", "跨度"
            ],
            "axis_lines": [
                "轴", "轴线", "定位轴线", "A", "B", "C", "D", "E", "F", "G",
                "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"
            ],
            "drawing_info": [
                "图纸编号", "图号", "比例", "设计", "审核", "项目", "工程",
                "结构图", "建筑图", "平面图", "立面图", "剖面图", "详图"
            ],
            "specifications": [
                "规格", "型号", "等级", "强度", "配筋", "钢筋", "预埋件",
                "φ", "Φ", "@", "间距", "保护层", "搭接长度"
            ]
        }
    
    def _load_ocr_error_patterns(self) -> List[Dict[str, str]]:
        """加载常见OCR错误模式"""
        return [
            # 数字误识别
            {"pattern": r"0", "corrections": ["O", "o", "°"]},
            {"pattern": r"1", "corrections": ["l", "I", "|"]},
            {"pattern": r"5", "corrections": ["S", "s"]},
            {"pattern": r"8", "corrections": ["B"]},
            
            # 字母误识别
            {"pattern": r"O", "corrections": ["0", "Q"]},
            {"pattern": r"I", "corrections": ["1", "l", "|"]},
            {"pattern": r"S", "corrections": ["5"]},
            
            # 中文误识别
            {"pattern": r"梁", "corrections": ["粱", "樑"]},
            {"pattern": r"柱", "corrections": ["住", "注"]},
            {"pattern": r"板", "corrections": ["扳", "版"]},
            {"pattern": r"墙", "corrections": ["强", "牆"]},
            
            # 符号误识别
            {"pattern": r"×", "corrections": ["x", "*", "X"]},
            {"pattern": r"φ", "corrections": ["Φ", "ф", "¢"]},
            {"pattern": r"@", "corrections": ["＠", "a"]},
        ]
    
    async def correct_ocr_result(self, 
                               merged_ocr_key: str, 
                               drawing_id: int, 
                               task_id: str,
                               original_image_info: Dict[str, Any] = None) -> CorrectedOCRResult:
        """
        对合并的OCR结果进行智能纠正
        
        Args:
            merged_ocr_key: 合并OCR结果的存储键
            drawing_id: 图纸ID
            task_id: 任务ID
            original_image_info: 原始图像信息
            
        Returns:
            纠正后的OCR结果
        """
        logger.info(f"🔧 开始OCR结果智能分析: {merged_ocr_key}")
        start_time = time.time()
        
        try:
            # 1. 下载原始OCR结果
            original_result = await self._download_ocr_result(merged_ocr_key)
            if not original_result:
                raise ValueError(f"无法下载OCR结果: {merged_ocr_key}")
            
            # 2. 仅进行基本预处理（清理格式，不进行纠正）
            preprocessed_result = self._preprocess_ocr_text_simple(original_result)
            
            # 3. 直接使用GPT进行智能分析和结构化提取（跳过词典纠错）
            logger.info("🚀 跳过词典纠错，直接使用GPT智能分析...")
            gpt_analyzed = await self._apply_gpt_analysis_only(
                preprocessed_result, task_id, original_image_info
            )
            
            # 4. 获取自然语言文本（优先natural_language_summary，否则降级为gpt_response_text字段或空字符串）
            natural_language_text = gpt_analyzed.get("natural_language_summary")
            if not natural_language_text:
                # 兼容旧流程，尝试获取gpt_response_text
                natural_language_text = gpt_analyzed.get("gpt_response_text", "")
            if not natural_language_text:
                logger.warning("⚠️ 未获取到自然语言分析文本，保存空内容")
                natural_language_text = ""
            
            # 5. 保存自然语言文本到 analyzed_result.txt
            analyzed_key = f"ocr_results/{drawing_id}/analyzed_result.txt"
            storage_result = None
            if self.storage_service:
                try:
                    storage_result = await self.storage_service.upload_content_async(
                        content=natural_language_text,
                        key=analyzed_key,
                        content_type="text/plain"
                    )
                    logger.info(f"✅ 分析结果自然语言文本已保存: {analyzed_key}")
                except Exception as save_exc:
                    logger.error(f"❌ 分析结果自然语言文本保存失败: {save_exc}")
                    storage_result = {"success": False, "error": str(save_exc)}
            else:
                logger.error("❌ 存储服务未初始化，无法保存分析结果")
                storage_result = {"success": False, "error": "存储服务未初始化"}
            
            # 6. 构建返回结果（其余统计和结构体保持不变）
            corrected_ocr_result = CorrectedOCRResult(
                task_id=task_id,
                original_result_key=merged_ocr_key,
                corrected_result_key=analyzed_key,
                original_stats=self._extract_stats(original_result),
                corrected_stats={},
                drawing_basic_info={},
                component_list=[],
                global_notes=[],
                text_regions_corrected=[],
                correction_summary={},
                processing_metadata={
                    "processing_time": time.time() - start_time,
                    "analysis_method": "gpt_only_natural_language_txt",
                    "ai_model_used": self.ai_analyzer.__class__.__name__ if self.ai_analyzer else None,
                    "storage_info": storage_result
                },
                timestamp=time.time()
            )
            
            logger.info(f"✅ OCR结果自然语言分析文本保存完成: 耗时 {time.time() - start_time:.2f}s")
            
            return corrected_ocr_result
            
        except Exception as e:
            logger.error(f"❌ OCR结果智能分析失败: {e}")
            raise

    def _preprocess_ocr_text_simple(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """简单预处理OCR文本（不进行纠正）"""
        logger.info("🔧 开始简单OCR文本预处理（保持原文不变）...")
        
        # 复制原始结果
        preprocessed = json.loads(json.dumps(ocr_result))
        
        # 获取文本区域
        text_regions = preprocessed.get("merged_result", {}).get("all_text_regions", [])
        
        cleaned_regions = []
        for region in text_regions:
            text = region.get("text", "").strip()
            if not text:
                continue
            
            # 仅做基本清理，不进行纠正
            cleaned_text = self._clean_text_basic(text)
            if cleaned_text:
                region["text"] = cleaned_text
                region["original_text"] = text
                cleaned_regions.append(region)
        
        # 更新文本区域
        if "merged_result" in preprocessed:
            preprocessed["merged_result"]["all_text_regions"] = cleaned_regions
        
        logger.info(f"📝 简单预处理完成: {len(text_regions)} -> {len(cleaned_regions)} 个文本区域（保持原文）")
        return preprocessed
    
    def _clean_text_basic(self, text: str) -> str:
        """基本文本清理（不进行任何纠正）"""
        if not text:
            return ""
        
        # 仅去除多余空白，保持所有原始内容
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # 不进行任何纠正，保持OCR识别的原始结果
        return cleaned

    async def _apply_gpt_analysis_only(self, 
                                     ocr_result: Dict[str, Any], 
                                     task_id: str,
                                     original_image_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        使用GPT进行智能分析：纠正明显错误、全图还原、提取图纸基本信息、构件清单及构件属性
        注意：不使用词典纠错，而是让GPT基于上下文进行智能判断
        """
        logger.info("🤖 开始GPT智能分析：纠正明显错误、提取图纸信息和构件清单...")
        
        try:
            # 确保获取到正确的OCR数据
            if isinstance(ocr_result, dict) and "data" in ocr_result:
                # 如果ocr_result是下载结果的包装
                original_content_json = ocr_result["data"]
            else:
                # 直接使用ocr_result
                original_content_json = ocr_result
            
            # 提取OCR文本用于GPT分析
            merged_result = original_content_json.get("merged_ocr_result")
            if not merged_result:
                merged_result = original_content_json.get("merged_result")
            text_regions = []
            if merged_result:
                # 优先支持text_regions
                text_regions = merged_result.get("text_regions", [])
                # 兼容all_text_regions
                if not text_regions:
                    text_regions = merged_result.get("all_text_regions", [])
                # 兼容texts
                if not text_regions:
                    text_regions = merged_result.get("texts", [])
                # 兼容ocr_results
                if not text_regions:
                    text_regions = merged_result.get("ocr_results", [])
                # 兼容regions
                if not text_regions:
                    text_regions = merged_result.get("regions", [])
                # 兼容text_results
                if not text_regions:
                    text_regions = merged_result.get("text_results", [])
            
            logger.info(f"🔍 OCR结果数据结构调试:")
            logger.info(f"   - merged_result keys: {list(merged_result.keys()) if merged_result else 'None'}")
            logger.info(f"   - text_regions count: {len(text_regions) if text_regions else 0}")
            
            if not text_regions:
                logger.warning("⚠️ 未找到OCR文本区域，返回空结果")
                return {"success": False, "message": "未找到OCR文本区域", "text_regions": []}
            
            # 构建GPT分析提示词（文本区域排序、相邻合并、纯文本）
            prompt, ocr_plain_text = self._build_gpt_analysis_prompt(text_regions, original_image_info, return_plain_text=True)

            # 输出全图文本概览（前5行和后5行）
            plain_lines = ocr_plain_text.split('\n')
            preview_lines = plain_lines[:5] + (["..."] if len(plain_lines) > 10 else []) + plain_lines[-5:] if len(plain_lines) > 10 else plain_lines
            logger.info("📋 全图文本概览：\n" + '\n'.join(preview_lines))

            # 保存拼接纯文本到S3
            if self.storage_service:
                try:
                    drawing_id = original_content_json.get('meta', {}).get('drawing_id', 'unknown')
                    s3_key = f"ocr_results/{drawing_id}/ocr_plain_text_{task_id}.txt"
                    save_result = self.storage_service.upload_content_sync(
                        content=ocr_plain_text,
                        s3_key=s3_key,
                        content_type="text/plain"
                    )
                    if save_result.get("success"):
                        logger.info(f"✅ 拼接纯文本已保存到S3: {save_result.get('final_url')}")
                    else:
                        logger.warning(f"⚠️ 拼接纯文本保存到S3失败: {save_result.get('error')}")
                except Exception as save_exc:
                    logger.warning(f"⚠️ 拼接纯文本保存异常: {save_exc}")

            # 调用AI分析器
            if not self.ai_analyzer:
                logger.error("❌ AI分析器未初始化")
                return self._create_fallback_result(text_regions)
            
            # 使用AI分析器进行智能分析（prompt只包含拼接纯文本，不含原始json或大数组）
            analysis_response = await self.ai_analyzer.analyze_text_async(
                prompt=prompt,
                session_id=f"ocr_analysis_{task_id}",
                context_data={"task_type": "ocr_intelligent_analysis", "drawing_id": task_id}
            )
            
            if not analysis_response.get("success"):
                logger.error(f"❌ GPT分析失败: {analysis_response.get('error')}")
                return self._create_fallback_result(text_regions)
            
            # 解析GPT分析结果
            gpt_response_text = analysis_response.get("response", "")
            analyzed_result = self._parse_gpt_analysis_response(gpt_response_text, original_content_json)
            
            # 自动提取最终自然语言摘要
            final_summary = analyzed_result.get("natural_language_summary", "")
            
            # 保存大模型交互过程到Sealos
            if self.storage_service:
                try:
                    drawing_id = original_content_json.get('meta', {}).get('drawing_id', 'unknown')
                    interaction_key = f"ocr_results/{drawing_id}/gpt_interaction_{task_id}.json"
                    interaction_data = {
                        "prompt": prompt,
                        "raw_response": gpt_response_text,
                        "final_summary": final_summary,
                        "finish_reason": analysis_response.get("finish_reason", "unknown")
                    }
                    self.storage_service.upload_content_sync(
                        content=json.dumps(interaction_data, ensure_ascii=False, indent=2),
                        s3_key=interaction_key,
                        content_type="application/json"
                    )
                    logger.info(f"✅ 大模型交互过程已保存到S3: {interaction_key}")
                except Exception as e:
                    logger.warning(f"⚠️ 大模型交互过程保存失败: {e}")
            
            # 直接返回包含自然语言摘要的结果，不再调用postprocess
            return analyzed_result
            
        except Exception as e:
            logger.error(f"❌ GPT智能分析异常: {e}", exc_info=True)
            return self._create_fallback_result(text_regions if 'text_regions' in locals() else [])
    
    def _create_fallback_result(self, text_regions: List[Dict]) -> Dict[str, Any]:
        """创建备用结果"""
        return {
            "drawing_basic_info": {},
            "component_list": [],
            "global_notes": [],
            "analysis_summary": {"message": "GPT analysis failed, returning original OCR data."},
            "text_regions_analyzed": text_regions
        }

    def _build_gpt_analysis_prompt(self, 
                                 text_regions: List[dict], 
                                 image_info: Dict[str, Any] = None,
                                 return_plain_text: bool = False) -> str:
        """构建GPT分析提示词（文本区域排序、相邻合并、纯文本），可返回纯文本内容"""
        # 1. 按y升序、x升序排序
        sorted_regions = sorted(
            text_regions,
            key=lambda r: (r.get('bbox', r.get('box', [[0,0],[0,0],[0,0],[0,0]]))[0][1],
                           r.get('bbox', r.get('box', [[0,0],[0,0],[0,0],[0,0]]))[0][0])
        )
        # 2. 相邻合并（高度接近、x间距小）
        merged_lines = []
        line_buffer = []
        last_y = None
        last_h = None
        last_x2 = None
        y_threshold = 10  # 像素容差
        x_gap_threshold = 30  # x间距容差
        for region in sorted_regions:
            text = region.get('text', '').strip()
            if not text:
                continue
            box = region.get('bbox', region.get('box', [[0,0],[0,0],[0,0],[0,0]]))
            y = box[0][1]
            x1 = box[0][0]
            x2 = box[2][0]
            h = abs(box[2][1] - box[0][1])
            if last_y is not None and abs(y - last_y) <= y_threshold and last_h is not None and abs(h - last_h) <= y_threshold:
                # 同一行，判断x间距
                if last_x2 is not None and (x1 - last_x2) <= x_gap_threshold:
                    line_buffer.append(text)
                    last_x2 = x2
                    continue
                else:
                    merged_lines.append(' '.join(line_buffer))
                    line_buffer = [text]
                    last_x2 = x2
            else:
                if line_buffer:
                    merged_lines.append(' '.join(line_buffer))
                line_buffer = [text]
                last_x2 = x2
            last_y = y
            last_h = h
        if line_buffer:
            merged_lines.append(' '.join(line_buffer))
        # 3. 拼接为纯文本
        ocr_plain_text = '\n'.join(merged_lines)
        prompt = f"""你是一位经验丰富的建筑工程造价师，现在需要对PaddleOCR识别的文本结果进行智能分析和结构化提取。

## 重要说明
- 文本已按图纸顺序排序，并自动合并相邻文本框为一句
- 你的任务是：**对OCR识别文本进行智能排序、归纳、合成，并纠正OCR过程中的明显识别错误**（如数字/字母混淆、常见错别字、格式混乱等）。
- 输出内容应为**结构清晰、语义连贯的高质量自然语言摘要**，而不是OCR原文的简单拼接。
- 对于不确定的内容，请合理推断或在备注中说明。
- 优先保持数字、材料标号、构件编号的原始形式，除非明显错误。

## 任务说明
对以下OCR识别的文本进行分析、纠错、分类整理，提取出建筑图纸的关键信息。

## OCR识别的原始文本（每行为一段，顺序与图纸分布一致）
{ocr_plain_text}

## 建筑工程专业知识参考
1. **构件类型**: 梁(KL)、柱(KZ)、板(KB)、墙(KQ)、基础(JC)、楼梯(LT)等
2. **材料等级**: C20、C25、C30、C35、C40、C50、HRB400、HRB500等
3. **尺寸表示**: 长×宽×高、φ直径、@间距等
4. **轴线编号**: A、B、C、D...轴，1、2、3、4...轴
5. **图纸信息**: 图号、比例、项目名称、设计单位等

## 分析原则
1. **智能排序与归纳**：根据建筑图纸常识，对内容进行合理排序、归纳、合成，提升可读性和专业性。
2. **纠正明显错误**：如数字/字母混淆、常见错别字、格式混乱等，需智能纠正。
3. **保持原文优先**: 对于数字、材料标号(如C20)、尺寸(如33.170)等，除非明显错误，否则保持不变。
4. **构件编号保护**: K-JKZ1、GZ1等构件编号通常是正确的，请保持原样。
5. **合理推测**: 只有在文本明显不符合建筑规范时才进行调整。
6. **上下文分析**: 结合图纸整体内容判断文本的合理性。

## 输出要求
请按以下**自然语言摘要**格式输出分析后的结果，保持简洁以便作为后续Vision分析的上下文：

**格式要求：**
1. 用简洁的自然语言描述，不要输出JSON格式
2. 控制总字数在300字以内
3. 重点突出关键信息：图纸类型、主要构件、材料等级

**输出模板：**
```
图纸信息：[图纸类型] [项目名称] [图纸比例]

构件概览：
- 主要构件类型：[梁、柱、板等]
- 构件编号示例：[KL1、Z1、B1等，列举5-8个代表性编号]
- 材料等级：[C30、HRB400等]
- 轴线分布：[A-D轴、1-5轴等]

技术特点：
- 结构体系：[框架结构、剪力墙结构等]
- 构件数量：约[X]个主要构件
- 图纸复杂度：[简单/中等/复杂]

施工要点：
- [关键的施工说明或技术要求，1-2条]
```

**示例输出：**
```
图纸信息：结构平面图 某办公楼工程 1:100

构件概览：
- 主要构件类型：框架梁、框架柱、现浇板
- 构件编号示例：KL1、KL2、KZ1、KZ2、B1
- 材料等级：C30混凝土、HRB400钢筋
- 轴线分布：A-F轴、1-6轴

技术特点：
- 结构体系：钢筋混凝土框架结构
- 构件数量：约15个主要构件
- 图纸复杂度：中等

施工要点：
- 梁柱节点需加强配筋
- 板厚度120mm，双向配筋
```

## 注意事项
1. **必须对OCR文本进行智能排序、归纳、合成，并纠正明显识别错误**。
2. 优先保持OCR原文，特别是数字、材料标号、构件编号。
3. 根据建筑工程常识判断文本的合理性。
4. 对于不确定的内容，保持原文并在备注中说明。
5. 确保输出的自然语言摘要格式正确，可以直接解析。
6. **避免过度纠正**，保持OCR识别结果的原始性和准确性。
"""
        if return_plain_text:
            return prompt, ocr_plain_text
        return prompt
    
    def _parse_gpt_analysis_response(self, 
                                   gpt_response: str, 
                                   original_result: Dict[str, Any]) -> Dict[str, Any]:
        """解析GPT分析响应 - 支持自然语言格式，若为JSON则自动转为自然语言摘要"""
        logger.info("📊 解析GPT分析响应...")
        
        try:
            # 检查是否是新的自然语言格式
            if "图纸信息：" in gpt_response and "构件概览：" in gpt_response:
                # 解析自然语言格式
                parsed_response = self._parse_natural_language_response(gpt_response)
                parsed_response["text_regions_analyzed"] = original_result.get("merged_result", {}).get("all_text_regions", [])
                parsed_response["natural_language_summary"] = gpt_response.strip()
                logger.info("✅ 自然语言格式分析响应解析成功")
                return parsed_response
            # 检查是否为JSON格式
            if gpt_response.strip().startswith("{") or gpt_response.strip().startswith("["):
                try:
                    json_content = gpt_response.strip()
                    parsed_json = json.loads(json_content)
                    # 自动转为自然语言摘要
                    summary_lines = []
                    if isinstance(parsed_json, dict):
                        # 图纸信息
                        drawing_info = parsed_json.get("drawing_basic_info", {})
                        summary_lines.append(f"图纸信息：{drawing_info.get('drawing_type', '')} {drawing_info.get('project_name', '')} {drawing_info.get('scale', '')}")
                        summary_lines.append("")
                        # 构件概览
                        summary_lines.append("构件概览：")
                        comp_types = set()
                        comp_ids = []
                        materials = set()
                        for comp in parsed_json.get("component_list", []):
                            if comp.get("component_type"): comp_types.add(comp["component_type"])
                            if comp.get("component_id"): comp_ids.append(comp["component_id"])
                            if comp.get("material"): materials.add(comp["material"])
                        summary_lines.append(f"- 主要构件类型：{ '、'.join(list(comp_types)[:5]) }")
                        summary_lines.append(f"- 构件编号示例：{ '、'.join(comp_ids[:8]) }")
                        summary_lines.append(f"- 材料等级：{ '、'.join(list(materials)[:3]) }")
                        summary_lines.append(f"- 轴线分布：{drawing_info.get('axis_lines', '')}")
                        summary_lines.append("")
                        # 技术特点
                        summary_lines.append("技术特点：")
                        summary_lines.append(f"- 结构体系：{drawing_info.get('structure_type', '')}")
                        summary_lines.append(f"- 构件数量：约{len(parsed_json.get('component_list', []))}个主要构件")
                        summary_lines.append(f"- 图纸复杂度：{drawing_info.get('complexity', '')}")
                        summary_lines.append("")
                        # 施工要点
                        summary_lines.append("施工要点：")
                        notes = [n.get('content','') for n in parsed_json.get('global_notes', []) if n.get('content')]
                        for note in notes[:2]:
                            summary_lines.append(f"- {note}")
                        summary_text = '\n'.join(summary_lines)
                        parsed_json["natural_language_summary"] = summary_text
                        parsed_json["text_regions_analyzed"] = original_result.get("merged_result", {}).get("all_text_regions", [])
                        logger.info("✅ JSON格式自动转为自然语言摘要")
                        return parsed_json
                except Exception as e:
                    logger.error(f"❌ JSON转自然语言失败: {e}")
            # 兼容旧的JSON代码块格式
            if "```json" in gpt_response:
                json_start = gpt_response.find("```json") + 7
                json_end = gpt_response.find("```", json_start)
                json_content = gpt_response[json_start:json_end].strip()
                try:
                    parsed_json = json.loads(json_content)
                    # 自动转为自然语言摘要
                    summary_lines = []
                    if isinstance(parsed_json, dict):
                        drawing_info = parsed_json.get("drawing_basic_info", {})
                        summary_lines.append(f"图纸信息：{drawing_info.get('drawing_type', '')} {drawing_info.get('project_name', '')} {drawing_info.get('scale', '')}")
                        summary_lines.append("")
                        summary_lines.append("构件概览：")
                        comp_types = set()
                        comp_ids = []
                        materials = set()
                        for comp in parsed_json.get("component_list", []):
                            if comp.get("component_type"): comp_types.add(comp["component_type"])
                            if comp.get("component_id"): comp_ids.append(comp["component_id"])
                            if comp.get("material"): materials.add(comp["material"])
                        summary_lines.append(f"- 主要构件类型：{ '、'.join(list(comp_types)[:5]) }")
                        summary_lines.append(f"- 构件编号示例：{ '、'.join(comp_ids[:8]) }")
                        summary_lines.append(f"- 材料等级：{ '、'.join(list(materials)[:3]) }")
                        summary_lines.append(f"- 轴线分布：{drawing_info.get('axis_lines', '')}")
                        summary_lines.append("")
                        summary_lines.append("技术特点：")
                        summary_lines.append(f"- 结构体系：{drawing_info.get('structure_type', '')}")
                        summary_lines.append(f"- 构件数量：约{len(parsed_json.get('component_list', []))}个主要构件")
                        summary_lines.append(f"- 图纸复杂度：{drawing_info.get('complexity', '')}")
                        summary_lines.append("")
                        summary_lines.append("施工要点：")
                        notes = [n.get('content','') for n in parsed_json.get('global_notes', []) if n.get('content')]
                        for note in notes[:2]:
                            summary_lines.append(f"- {note}")
                        summary_text = '\n'.join(summary_lines)
                        parsed_json["natural_language_summary"] = summary_text
                        parsed_json["text_regions_analyzed"] = original_result.get("merged_result", {}).get("all_text_regions", [])
                        logger.info("✅ JSON代码块自动转为自然语言摘要")
                        return parsed_json
                except Exception as e:
                    logger.error(f"❌ JSON代码块转自然语言失败: {e}")
            # 兜底：原样返回
            logger.info("🔄 返回原始结果作为备用")
            return {
                "drawing_basic_info": {},
                "component_list": [],
                "global_notes": [],
                "analysis_summary": {"error": "未能解析为自然语言或JSON"},
                "text_regions_analyzed": original_result.get("merged_result", {}).get("all_text_regions", []),
                "natural_language_summary": gpt_response[:300] + "..." if len(gpt_response) > 300 else gpt_response
            }
            
        except Exception as e:
            logger.error(f"❌ GPT分析响应解析失败: {e}")
            logger.info("🔄 返回原始结果作为备用")
            return {
                "drawing_basic_info": {},
                "component_list": [],
                "global_notes": [],
                "analysis_summary": {"error": f"GPT响应解析失败: {e}"},
                "text_regions_analyzed": original_result.get("merged_result", {}).get("all_text_regions", []),
                "natural_language_summary": gpt_response[:300] + "..." if len(gpt_response) > 300 else gpt_response
            }

    def _parse_natural_language_response(self, response_text: str) -> Dict[str, Any]:
        """解析自然语言格式的GPT响应"""
        try:
            parsed_data = {
                "drawing_basic_info": {},
                "component_list": [],
                "global_notes": [],
                "analysis_summary": {}
            }
            
            lines = response_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('```'):
                    continue
                
                # 识别各个部分
                if line.startswith('图纸信息：'):
                    info_text = line.replace('图纸信息：', '').strip()
                    info_parts = info_text.split(' ')
                    if len(info_parts) >= 1:
                        parsed_data["drawing_basic_info"]["drawing_type"] = info_parts[0]
                    if len(info_parts) >= 2:
                        parsed_data["drawing_basic_info"]["project_name"] = info_parts[1]
                    if len(info_parts) >= 3:
                        parsed_data["drawing_basic_info"]["scale"] = info_parts[2]
                
                elif line.startswith('构件概览：'):
                    current_section = "components"
                
                elif line.startswith('技术特点：'):
                    current_section = "technical"
                
                elif line.startswith('施工要点：'):
                    current_section = "construction"
                
                elif line.startswith('- ') and current_section:
                    content = line[2:].strip()
                    
                    if current_section == "components":
                        if content.startswith('构件编号示例：'):
                            # 提取构件编号
                            ids_text = content.replace('构件编号示例：', '')
                            component_ids = [id.strip() for id in ids_text.split('、') if id.strip()]
                            for comp_id in component_ids[:5]:  # 限制数量
                                parsed_data["component_list"].append({
                                    "component_id": comp_id,
                                    "component_type": "未指定",
                                    "material": "",
                                    "dimensions": "",
                                    "location": "",
                                    "specifications": ""
                                })
                        
                        elif content.startswith('材料等级：'):
                            material_text = content.replace('材料等级：', '')
                            # 将材料信息添加到已有构件中
                            materials = [m.strip() for m in material_text.split('、') if m.strip()]
                            if materials and parsed_data["component_list"]:
                                for comp in parsed_data["component_list"]:
                                    comp["material"] = materials[0]  # 使用第一个材料等级
                    
                    elif current_section in ["technical", "construction"]:
                        parsed_data["global_notes"].append({
                            "note_type": "技术说明" if current_section == "technical" else "施工说明",
                            "content": content,
                            "importance": "medium"
                        })
            
            # 生成分析摘要
            parsed_data["analysis_summary"] = {
                "total_components": len(parsed_data["component_list"]),
                "total_notes": len(parsed_data["global_notes"]),
                "processing_method": "natural_language_analysis",
                "confidence_level": "high"
            }
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"❌ 解析自然语言响应失败: {e}")
            return {
                "drawing_basic_info": {},
                "component_list": [],
                "global_notes": [],
                "analysis_summary": {"error": f"自然语言解析失败: {e}"}
            }

    async def _download_ocr_result(self, ocr_key: str) -> Optional[Dict[str, Any]]:
        """下载OCR合并结果"""
        logger.info(f"🔽 正在下载OCR结果: {ocr_key}")
        try:
            if not self.storage_service:
                logger.error("存储服务未初始化")
                return {"success": False, "error": "存储服务未初始化"}
            
            download_result = await self.storage_service.download_content_async(ocr_key)
            
            if download_result is None:
                logger.error(f"❌ 下载OCR结果失败，文件可能不存在或无法访问: {ocr_key}")
                return {"success": False, "error": f"文件下载失败: {ocr_key}"}

            # 假设下载内容已经是解析后的JSON字典
            return {"success": True, "data": download_result}

        except Exception as e:
            logger.error(f"❌ 下载OCR结果异常: {e}", exc_info=True)
            return {"success": False, "error": f"下载时发生异常: {e}"}
    
    def _postprocess_analyzed_result(self, analyzed_result: Dict[str, Any]) -> Dict[str, Any]:
        """后处理分析结果"""
        logger.info("🔧 开始后处理分析结果...")
        
        # 确保基本结构存在
        processed = {
            "drawing_basic_info": analyzed_result.get("drawing_basic_info", {}),
            "component_list": analyzed_result.get("component_list", []),
            "global_notes": analyzed_result.get("global_notes", []),
            "text_regions_analyzed": analyzed_result.get("text_regions_analyzed", []),
            "analysis_summary": analyzed_result.get("analysis_summary", {})
        }
        
        # 验证和清理数据
        if isinstance(processed["component_list"], list):
            # 确保每个构件有基本字段
            for component in processed["component_list"]:
                if not isinstance(component, dict):
                    continue
                    
                # 确保必要字段存在
                required_fields = ["component_id", "component_type", "material"]
                for field in required_fields:
                    if field not in component:
                        component[field] = ""
        
        # 保留自然语言摘要字段
        if "natural_language_summary" in analyzed_result:
            processed["natural_language_summary"] = analyzed_result["natural_language_summary"]
            
        logger.info("✅ 分析结果后处理完成")
        return processed
    
    def _calculate_processing_stats(self, 
                                  original_result: Dict[str, Any], 
                                  analyzed_result: Dict[str, Any]) -> Dict[str, Any]:
        """计算处理统计信息"""
        original_texts = len(original_result.get("merged_result", {}).get("all_text_regions", []))
        analyzed_components = len(analyzed_result.get("component_list", []))
        analyzed_notes = len(analyzed_result.get("global_notes", []))
        
        return {
            "original_text_count": original_texts,
            "extracted_components": analyzed_components,
            "extracted_notes": analyzed_notes,
            "processing_method": "gpt_analysis_only",
            "summary": f"提取了{analyzed_components}个构件和{analyzed_notes}条说明"
        }
    
    def _extract_stats(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """提取结果统计信息"""
        text_regions = result.get("merged_result", {}).get("all_text_regions", [])
        return {
            "total_text_regions": len(text_regions),
            "total_characters": sum(len(region.get("text", "")) for region in text_regions),
            "avg_confidence": sum(region.get("confidence", 0.0) for region in text_regions) / len(text_regions) if text_regions else 0.0
        } 