# -*- coding: utf-8 -*-
"""
AI Mock Data Detector - 模拟数据检测器
从ai_analyzer.py中提取出来的模拟数据检测功能
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class MockDataDetector:
    """模拟数据检测器"""
    
    def __init__(self):
        self.project_mock_indicators = [
            "某建筑工程项目", "某建筑结构施工图", "某住宅楼", "某办公楼",
            "示例项目", "测试项目", "演示项目", "样例工程",
            "XX项目", "XXX工程", "demo", "example", "test",
            "某建筑", "某项目", "某工程", "某结构",
            "标题栏显示的", "图纸上的", "图纸标注的",
            "标题栏中的项目名称", "项目名称", "工程名称"
        ]
        logger.info(" MockDataDetector initialized")
    
    def check_for_mock_data_patterns(self, qto_data: Dict) -> bool:
        """检查QTO数据是否包含模拟数据的模式"""
        try:
            mock_indicators_found = []
            
            # 1. 检查项目信息中的模拟数据标识
            drawing_info = qto_data.get("drawing_info", {})
            project_name = drawing_info.get("project_name", "")
            title = drawing_info.get("title", "")
            
            for indicator in self.project_mock_indicators:
                if indicator.lower() in project_name.lower() or indicator.lower() in title.lower():
                    mock_indicators_found.append(f"项目名称包含模拟标识: '{indicator}'")
                    logger.warning(f" 发现模拟数据标识: '{indicator}' in {project_name or title}")
            
            # 2. 检查构件编号的规律性模式
            components = qto_data.get("components", [])
            if len(components) >= 3:
                component_ids = [comp.get("component_id", "") for comp in components]
                
                # 检查连续编号模式
                for prefix in ["KZ-", "L-", "B-"]:
                    prefix_ids = [comp_id for comp_id in component_ids if comp_id.startswith(prefix)]
                    if len(prefix_ids) >= 3:
                        pattern_match = all(
                            comp_id == f"{prefix}{i+1}" for i, comp_id in enumerate(prefix_ids)
                        )
                        if pattern_match:
                            mock_indicators_found.append(f"构件编号呈现规律性连续模式({prefix}1,{prefix}2,{prefix}3...)")
                            logger.warning(" 发现规律性构件编号模式")
                
                # 检查是否所有编号都过于相似
                unique_prefixes = set(comp_id.split('-')[0] for comp_id in component_ids if '-' in comp_id)
                if len(unique_prefixes) == 1 and len(component_ids) > 2:
                    mock_indicators_found.append("所有构件使用相同类型前缀")
            
            # 3. 综合评估
            if mock_indicators_found:
                logger.warning(f" 发现 {len(mock_indicators_found)} 个模拟数据特征:")
                for indicator in mock_indicators_found:
                    logger.warning(f"   - {indicator}")
                return True
            else:
                logger.info(" 数据检查通过，未发现明显的模拟数据特征")
                return False
                
        except Exception as e:
            logger.error(f"检查模拟数据模式时出错: {e}")
            return False
