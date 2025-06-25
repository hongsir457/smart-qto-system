#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构件计算器
专门负责构件数量统计和基本参数计算
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ComponentInfo:
    """构件信息数据类"""
    type: str           # 构件类型：柱、梁、板、墙等
    code: str           # 构件编号
    width: float = 0.0  # 宽度(mm)
    height: float = 0.0 # 高度(mm)  
    length: float = 0.0 # 长度(mm)
    thickness: float = 0.0 # 厚度(mm)
    quantity: int = 1   # 数量

class ComponentCalculator:
    """构件计算器类"""
    
    def __init__(self):
        """初始化构件计算器"""
        self.component_types = {
            '柱': {'unit': '根', 'calc_method': 'count'},
            '梁': {'unit': '根', 'calc_method': 'count'},
            '板': {'unit': 'm²', 'calc_method': 'area'},
            '墙': {'unit': 'm²', 'calc_method': 'area'},
            '楼梯': {'unit': '个', 'calc_method': 'count'}
        }
    
    def classify_component(self, entity_data: Dict[str, Any]) -> Optional[ComponentInfo]:
        """
        分类识别构件
        
        Args:
            entity_data: 实体数据
            
        Returns:
            构件信息
        """
        try:
            # 基于几何特征判断构件类型
            width = entity_data.get('width', 0)
            height = entity_data.get('height', 0)
            length = entity_data.get('length', 0)
            
            # 简化的构件识别逻辑
            if width > 0 and height > 0:
                if width < 1000 and height < 1000:  # 小尺寸，可能是柱
                    component_type = '柱'
                    code = f'KZ{len(entity_data.get("entities", []))}'
                elif length > width and length > height:  # 长条形，可能是梁
                    component_type = '梁'
                    code = f'KL{len(entity_data.get("entities", []))}'
                else:  # 大面积，可能是板
                    component_type = '板'
                    code = f'KB{len(entity_data.get("entities", []))}'
            else:
                return None
            
            return ComponentInfo(
                type=component_type,
                code=code,
                width=width,
                height=height,
                length=length,
                quantity=1
            )
            
        except Exception as e:
            logger.error(f"构件分类失败: {e}")
            return None
    
    def calculate_component_metrics(self, component: ComponentInfo) -> Dict[str, Any]:
        """
        计算构件工程量指标
        
        Args:
            component: 构件信息
            
        Returns:
            计算结果
        """
        try:
            calc_method = self.component_types.get(component.type, {}).get('calc_method', 'count')
            unit = self.component_types.get(component.type, {}).get('unit', '个')
            
            if calc_method == 'area':
                # 面积计算 (m²)
                area = (component.width * component.length) / 1000000  # mm² → m²
                value = area * component.quantity
            elif calc_method == 'volume':
                # 体积计算 (m³)
                volume = (component.width * component.height * component.length) / 1000000000  # mm³ → m³
                value = volume * component.quantity
            else:
                # 数量计算
                value = component.quantity
            
            return {
                'component_code': component.code,
                'component_type': component.type,
                'quantity': component.quantity,
                'value': round(value, 3),
                'unit': unit,
                'dimensions': {
                    'width': component.width,
                    'height': component.height,
                    'length': component.length
                }
            }
            
        except Exception as e:
            logger.error(f"构件指标计算失败: {e}")
            return {
                'component_code': component.code,
                'component_type': component.type,
                'error': str(e)
            }
    
    def batch_calculate(self, components: List[ComponentInfo]) -> List[Dict[str, Any]]:
        """
        批量计算构件工程量
        
        Args:
            components: 构件列表
            
        Returns:
            计算结果列表
        """
        results = []
        
        for component in components:
            try:
                result = self.calculate_component_metrics(component)
                results.append(result)
            except Exception as e:
                logger.error(f"批量计算失败 {component.code}: {e}")
                results.append({
                    'component_code': component.code,
                    'error': str(e)
                })
        
        return results
    
    def group_by_type(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按构件类型分组
        
        Args:
            results: 计算结果列表
            
        Returns:
            分组结果
        """
        grouped = {}
        
        for result in results:
            component_type = result.get('component_type', '未知')
            if component_type not in grouped:
                grouped[component_type] = []
            grouped[component_type].append(result)
        
        return grouped 