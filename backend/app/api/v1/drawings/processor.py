"""
简化图纸处理器模块
从原drawings.py中提取的SimpleProcessor类
"""

import logging
import json
from typing import Dict, Any
from .config import ProcessingConfig, get_default_processing_config

logger = logging.getLogger(__name__)

class SimpleProcessor:
    """简化的图纸处理器，用于API演示"""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or get_default_processing_config()
        logger.info("简化图纸处理器初始化完成")
    
    def process_drawing(self, file_path: str, drawing_id: str, user_id: str) -> Dict[str, Any]:
        """模拟图纸处理过程"""
        logger.info(f"开始处理图纸: {drawing_id}")
        
        # 模拟处理结果
        return {
            "status": "success",
            "drawing_id": drawing_id,
            "user_id": user_id,
            "stages_completed": ["png_conversion", "ocr_recognition", "stage_one_analysis", "stage_two_analysis"],
            "ocr_result": {
                "status": "success",
                "text_regions": [
                    {
                        "text": "KZ1",
                        "confidence": 0.95,
                        "bbox": {"x_min": 100, "y_min": 100, "x_max": 150, "y_max": 130, "center_x": 125, "center_y": 115, "width": 50, "height": 30},
                        "bbox_area": 1500.0,
                        "text_length": 3,
                        "is_number": False,
                        "is_dimension": False,
                        "is_component_code": True
                    }
                ],
                "total_regions": 1,
                "all_text": "KZ1",
                "statistics": {"total_count": 1, "numeric_count": 0, "dimension_count": 0, "component_code_count": 1, "avg_confidence": 0.95},
                "processing_time": 2.0
            },
            "stage_one_result": self._get_mock_stage_one_result(),
            "stage_two_result": self._get_mock_stage_two_result(),
            "final_components": self._get_mock_final_components(),
            "total_components": 1,
            "processing_time": 15.5,
            "s3_urls": {"png_file": "https://example.com/drawing.png", "result_file": "https://example.com/result.json"}
        }
    
    def _get_mock_stage_one_result(self) -> Dict[str, Any]:
        """获取模拟的第一阶段分析结果"""
        return {
            "status": "success",
            "analysis_results": {
                "drawing_type": "结构",
                "title_block": {"project_name": "演示工程", "drawing_title": "结构施工图", "drawing_number": "S-01", "scale": "1:100"},
                "components": [{"code": "KZ1", "component_type": "框架柱", "dimensions": ["400×400"], "position": {"x": 125, "y": 115}, "confidence": 0.95}],
                "dimensions": [{"text": "400×400", "pattern": "(\\d+)×(\\d+)", "position": {"x": 190, "y": 115}, "confidence": 0.92}],
                "component_list": [{"code": "KZ1", "type": "框架柱", "dimensions": ["400×400"], "position": {"x": 125, "y": 115}, "confidence": 0.95, "dimension_count": 1}],
                "statistics": {"total_components": 1, "total_dimensions": 1, "avg_confidence": 0.95, "components_with_dimensions": 1}
            }
        }
    
    def _get_mock_stage_two_result(self) -> Dict[str, Any]:
        """获取模拟的第二阶段分析结果"""
        return {
            "status": "success",
            "analysis_results": {
                "components": [{
                    "code": "KZ1",
                    "type": "框架柱",
                    "dimensions": {"section": "400×400", "height": "3600", "concrete_grade": "C30"},
                    "material": {"concrete": "C30", "steel": "HRB400", "main_rebar": "8Φ20"},
                    "quantity": 4,
                    "position": {"floor": "1-3层", "grid": "A1"},
                    "attributes": {"load_bearing": True, "seismic_grade": "二级", "fire_resistance": "1.5h"}
                }],
                "analysis_summary": {
                    "initial_summary": "识别到主要结构构件包括框架柱",
                    "detail_summary": "详细分析了构件尺寸、材料等级",
                    "verification_summary": "最终验证确认构件信息准确",
                    "total_components": 1,
                    "analysis_rounds": 3
                },
                "quality_assessment": {"overall_confidence": 0.92, "completeness": "高", "accuracy": "excellent"},
                "recommendations": ["建议核实KZ1柱的配筋详图"],
                "processing_metadata": {"model_used": "gpt-4o", "provider": "openai"}
            }
        }
    
    def _get_mock_final_components(self) -> list:
        """获取模拟的最终构件列表"""
        return [{
            "code": "KZ1",
            "type": "框架柱",
            "dimensions": {"section": "400×400", "height": "3600"},
            "material": {"concrete": "C30", "steel": "HRB400"},
            "quantity": 4
        }]
    
    def export_components_to_excel(self, processing_result: Dict[str, Any], output_path: str) -> bool:
        """简化的Excel导出功能"""
        try:
            # 这里应该实现真正的Excel导出逻辑
            # 为了演示，我们创建一个空的Excel文件
            import pandas as pd
            
            components = processing_result.get('final_components', [])
            if components:
                df = pd.DataFrame(components)
                df.to_excel(output_path, index=False)
                return True
            return False
        except Exception as e:
            logger.error(f"Excel导出失败: {str(e)}")
            return False

# 全局处理器实例
_processor_instance = None

def get_processor() -> SimpleProcessor:
    """获取处理器实例（单例模式）"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = SimpleProcessor()
        logger.info("图纸处理器初始化完成")
    
    return _processor_instance 