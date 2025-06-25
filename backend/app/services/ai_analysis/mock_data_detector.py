#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟数据检测器 - 检测和处理AI生成的模拟数据
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MockDataDetector:
    """
    负责检测和处理AI生成的模拟数据
    """
    
    def __init__(self):
        """初始化模拟数据检测器"""
        logger.info("✅ MockDataDetector initialized")
    
    def check_for_mock_data_patterns(self, qto_data: Dict) -> bool:
        """检查QTO数据是否包含模拟数据的模式"""
        try:
            mock_indicators_found = []
            
            # 1. 检查项目信息中的模拟数据标识
            drawing_info = qto_data.get("drawing_info", {})
            project_name = drawing_info.get("project_name", "")
            title = drawing_info.get("title", "")
            
            project_mock_indicators = [
                "某建筑工程项目", "某建筑结构施工图", "某住宅楼", "某办公楼",
                "示例项目", "测试项目", "演示项目", "样例工程",
                "XX项目", "XXX工程", "demo", "example", "test",
                "某建筑", "某项目", "某工程", "某结构",
                "标题栏显示的", "图纸上的", "图纸标注的",
                "标题栏中的项目名称", "项目名称", "工程名称"
            ]
            
            for indicator in project_mock_indicators:
                if indicator.lower() in project_name.lower() or indicator.lower() in title.lower():
                    mock_indicators_found.append(f"项目名称包含模拟标识: '{indicator}'")
                    logger.warning(f"🚨 发现模拟数据标识: '{indicator}' in {project_name or title}")
            
            # 2. 检查构件编号的规律性模式
            components = qto_data.get("components", [])
            if len(components) >= 3:
                component_ids = [comp.get("component_id", "") for comp in components]
                
                # 检查KZ-1, KZ-2, KZ-3类型的连续编号
                kz_ids = [comp_id for comp_id in component_ids if comp_id.startswith("KZ-")]
                if len(kz_ids) >= 3:
                    kz_pattern = all(
                        comp_id == f"KZ-{i+1}" for i, comp_id in enumerate(kz_ids)
                    )
                    if kz_pattern:
                        mock_indicators_found.append("构件编号呈现规律性连续模式(KZ-1,KZ-2,KZ-3...)")
                        logger.warning("🚨 发现规律性构件编号模式")
                
                # 检查L-1, L-2, L-3类型的连续编号  
                l_ids = [comp_id for comp_id in component_ids if comp_id.startswith("L-")]
                if len(l_ids) >= 3:
                    l_pattern = all(
                        comp_id == f"L-{i+1}" for i, comp_id in enumerate(l_ids)
                    )
                    if l_pattern:
                        mock_indicators_found.append("构件编号呈现规律性连续模式(L-1,L-2,L-3...)")
                        logger.warning("🚨 发现规律性构件编号模式")
                
                # 检查B-1, B-2, B-3类型的连续编号
                b_ids = [comp_id for comp_id in component_ids if comp_id.startswith("B-")]
                if len(b_ids) >= 3:
                    b_pattern = all(
                        comp_id == f"B-{i+1}" for i, comp_id in enumerate(b_ids)
                    )
                    if b_pattern:
                        mock_indicators_found.append("构件编号呈现规律性连续模式(B-1,B-2,B-3...)")
                        logger.warning("🚨 发现规律性构件编号模式")
                
                # 检查是否所有编号都过于相似
                unique_prefixes = set(comp_id.split('-')[0] for comp_id in component_ids if '-' in comp_id)
                if len(unique_prefixes) == 1 and len(component_ids) > 2:
                    mock_indicators_found.append(f"所有构件使用相同前缀模式: {list(unique_prefixes)[0]}")
                    logger.warning(f"🚨 发现统一前缀模式: {list(unique_prefixes)[0]}")
            
            # 3. 检查尺寸数据的规律性
            if components:
                dimensions = []
                for comp in components:
                    width = comp.get("dimensions", {}).get("width")
                    height = comp.get("dimensions", {}).get("height")
                    length = comp.get("dimensions", {}).get("length")
                    dimensions.extend([d for d in [width, height, length] if d])
                
                # 检查是否有太多相同的尺寸值
                if len(dimensions) > 5:
                    from collections import Counter
                    dim_counts = Counter(dimensions)
                    most_common = dim_counts.most_common(1)[0]
                    if most_common[1] > len(dimensions) * 0.6:  # 如果超过60%的尺寸相同
                        mock_indicators_found.append(f"尺寸数据过于统一: {most_common[0]}出现{most_common[1]}次")
                        logger.warning(f"🚨 发现统一尺寸模式: {most_common}")
            
            # 4. 记录结果
            if mock_indicators_found:
                logger.warning(f"🚨 检测到{len(mock_indicators_found)}个模拟数据指标:")
                for indicator in mock_indicators_found:
                    logger.warning(f"   • {indicator}")
                return True
            else:
                logger.info("✅ 未检测到明显的模拟数据模式")
                return False
            
        except Exception as e:
            logger.error(f"❌ 模拟数据检测异常: {e}")
            return False
    
    def enhance_mock_data_detection(self, qto_data: Dict) -> Dict:
        """增强模拟数据检测，如果检测到模拟数据则返回增强的提示"""
        is_mock = self.check_for_mock_data_patterns(qto_data)
        
        if is_mock:
            logger.warning("🚨 检测到模拟数据，返回增强提示")
            return {
                "is_mock_detected": True,
                "enhancement_needed": True,
                "mock_data_warning": "检测到AI可能生成了模拟数据，建议重新分析"
            }
        else:
            return {
                "is_mock_detected": False,
                "enhancement_needed": False
            }
    
    def validate_response_authenticity(self, qto_data: Dict) -> List[str]:
        """验证响应的真实性，返回发现的问题列表"""
        issues = []
        
        try:
            # 1. 检查是否包含明显的模拟标识
            if self.check_for_mock_data_patterns(qto_data):
                issues.append("检测到模拟数据模式")
            
            # 2. 检查数据完整性
            components = qto_data.get("components", [])
            if not components:
                issues.append("未找到任何构件数据")
            
            # 3. 检查基本字段完整性
            drawing_info = qto_data.get("drawing_info", {})
            if not drawing_info.get("project_name") and not drawing_info.get("title"):
                issues.append("缺少项目基本信息")
            
            # 4. 检查构件数据质量
            for i, comp in enumerate(components):
                if not comp.get("component_id"):
                    issues.append(f"构件{i+1}缺少编号")
                if not comp.get("component_type"):
                    issues.append(f"构件{i+1}缺少类型")
                if not comp.get("dimensions"):
                    issues.append(f"构件{i+1}缺少尺寸信息")
            
            logger.info(f"验证完成，发现{len(issues)}个问题")
            return issues
            
        except Exception as e:
            logger.error(f"❌ 响应验证异常: {e}")
            return [f"验证过程出错: {str(e)}"] 