import logging
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# 假设这些服务和工具类可以从app.services或app.utils中导入
# 路径需要根据项目实际结构调整
from ...utils.analysis_optimizations import GPTResponseParser, AnalysisLogger
from ..ocr_result_corrector import OCRResultCorrector
from ..s3_service import S3Service
from ..ai_analyzer import AIAnalyzerService
from ..enhanced_slice_models import EnhancedSliceInfo

logger = logging.getLogger(__name__)

class OCRTrackService:
    """
    OCR轨道服务
    负责OCR轨道1的全流程：汇总所有切片的OCR文本，调用大模型进行全图概览分析，并保存结果。
    """

    def __init__(self, ai_analyzer: AIAnalyzerService, storage_service: S3Service):
        """
        初始化OCR轨道服务
        
        Args:
            ai_analyzer: AI分析器实例
            storage_service: 存储服务实例
        """
        self.ai_analyzer = ai_analyzer
        self.storage_service = storage_service
        self.parser = GPTResponseParser()

    def extract_global_overview(self, 
                                enhanced_slices: List[EnhancedSliceInfo], 
                                drawing_info: Dict[str, Any], 
                                task_id: str) -> Dict[str, Any]:
        """
        执行全图OCR概览分析。
        
        Args:
            enhanced_slices: 包含OCR结果的增强切片列表
            drawing_info: 图纸信息
            task_id: 任务ID
            
        Returns:
            分析结果，包含是否成功和概览数据
        """
        start_time = time.time()
        AnalysisLogger.log_step("global_ocr_overview", "开始全图OCR概览分析")

        try:
            # 1. 汇总所有OCR文本
            text_regions = []
            for slice_info in enhanced_slices:
                if slice_info.ocr_results:
                    for item in slice_info.ocr_results:
                        text_regions.append({
                            "text": item.text,
                            "bbox": getattr(item, "bbox", None) or getattr(item, "position", None)
                        })

            if not text_regions:
                return {"success": False, "error": "没有OCR文本可进行全图概览分析"}

            # 2. 拼接纯文本 (使用OCRResultCorrector)
            try:
                corrector = OCRResultCorrector()
                ocr_plain_text = corrector.build_plain_text_from_regions(text_regions)
            except Exception as e:
                logger.warning(f"⚠️ OCRResultCorrector不可用，降级为简单拼接: {e}")
                ocr_plain_text = '\n'.join([r["text"] for r in text_regions])
            
            # 3. 构建Prompt并调用AI分析
            analysis_prompt = self._build_global_overview_prompt(ocr_plain_text, drawing_info)
            
            if not self.ai_analyzer:
                return {"success": False, "error": "AI分析器未初始化"}

            response = self.ai_analyzer.analyze_with_context(
                prompt=analysis_prompt,
                context_type="global_overview",
                task_id=task_id
            )

            if not response.get("success"):
                return {"success": False, "error": response.get("error", "AI分析失败")}
            
            # 4. 直接获取纯文本响应，不再解析JSON
            overview_text = response.get("analysis", "").strip()

            if not overview_text:
                return {"success": False, "error": "AI分析返回空内容"}
            
            # 5. 保存结果到S3
            self._save_overview_to_storage(overview_text, drawing_info, task_id)

            processing_time = time.time() - start_time
            AnalysisLogger.log_step("global_overview_completed", f"全图概览完成，耗时{processing_time:.2f}s")

            return {
                "success": True,
                "overview": overview_text, # 返回纯文本
                "ocr_text_count": len(ocr_plain_text.splitlines()),
                "processing_time": processing_time
            }

        except Exception as e:
            logger.error(f"❌ 全图OCR概览分析失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _build_global_overview_prompt(self, ocr_plain_text: str, drawing_info: Dict[str, Any]) -> str:
        """为全图OCR概览构建Prompt，要求输出纯文本"""
        prompt = f"""你是一位资深的土木工程师和造价师，你的任务是根据提供的建筑结构图纸OCR文本，生成一份全面、详细、结构化的全图概览文本。

**原始OCR文本：**
---
{ocr_plain_text}
---

**已知图纸信息（供参考）：**
- 项目名称: {drawing_info.get("project_name", "未知")}
- 图纸名称: {drawing_info.get("drawing_name", "未知")}

**你的任务与要求：**
请不要使用JSON格式。请生成一份人类易于阅读的纯文本报告，包含以下三个主要部分，并使用 Markdown 标题（例如 ## 标题）来分隔它们：

## 图纸基本信息
在这部分，请详细总结图纸的项目概况和核心设计参数。例如：项目名称、图纸类型（如结构平面图、加固图）、主要楼层、标高范围、设计的混凝土强度等级、抗震等级等。

## 构件清单
在这部分，请以清晰的列表或段落形式，详细列出图纸中所有识别到的构件。对于每个构件（如K-JKZ1, GZ1），需明确其类型（如加固柱、框架柱）、详细的截面尺寸（包括加固前后的变化）、具体的钢筋配置（纵筋、箍筋、拉筋的直径和间距）、标高范围和其他属性。对于同类型但有不同尺寸或配筋的构件，应分别说明。

## 技术说明
在这部分，请详细汇总图纸中所有的技术说明、施工工艺和质量要求。例如：新老结构结合面的处理方法（如凿毛）、钢筋的连接要求（如焊接长度）、植筋的深度要求、特殊构造（如梅花形布置）以及其他任何与施工相关的备注信息。
"""
        return prompt

    def _save_overview_to_storage(self, overview_text: str, drawing_info: Dict, task_id: str):
        """将概览文本保存到存储服务"""
        try:
            if not self.storage_service:
                logger.warning("⚠️ 存储服务未初始化，跳过保存GPT全图概览")
                return

            # 直接保存文本内容
            filename = f"global_overview_{task_id}.txt"
            folder = f"dual_track_results/{drawing_info.get('drawing_id', 'unknown')}/track_1_gpt_overview"
            
            result = self.storage_service.upload_txt_content(
                content=overview_text,
                file_name=filename,
                folder=folder
            )
            if result.get("success"):
                logger.info(f"💾 GPT全图概览文本已保存到: {result.get('s3_url')}")
            else:
                logger.error(f"❌ GPT全图概览文本保存失败: {result.get('error')}")
        except Exception as e:
            logger.error(f"❌ 保存GPT全图概览到存储时出错: {e}", exc_info=True) 