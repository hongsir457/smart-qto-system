#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工程量计算器
根据构件识别结果计算工程量
"""

import logging
import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ComponentQuantity:
    """构件工程量数据类"""
    component_type: str  # 构件类型
    name: str           # 构件名称
    dimensions: Dict[str, float]  # 尺寸信息
    quantity: int       # 数量
    volume: float       # 体积
    area: float         # 面积
    unit: str          # 单位
    calculation_method: str  # 计算方法说明

class QuantityCalculator:
    """工程量计算器"""
    
    def __init__(self):
        """初始化计算器"""
        self.component_handlers = {
            'wall': self._calculate_wall_quantity,
            'column': self._calculate_column_quantity,
            'beam': self._calculate_beam_quantity,
            'slab': self._calculate_slab_quantity,
            'foundation': self._calculate_foundation_quantity
        }
    
    def process_recognition_results(self, recognition_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理识别结果，计算工程量
        
        Args:
            recognition_results: 构件识别结果
            
        Returns:
            Dict: 完整的工程量计算结果
        """
        try:
            logger.info("🧮 开始工程量计算...")
            
            components = recognition_results.get('components', [])
            if not components:
                logger.warning("⚠️ 没有识别到构件，无法计算工程量")
                return self._create_empty_result()
            
            # 按构件类型分组
            grouped_components = self._group_components_by_type(components)
            
            # 计算各类构件工程量
            quantities = {}
            total_summary = {
                'total_volume': 0.0,
                'total_area': 0.0,
                'total_count': 0
            }
            
            for component_type, component_list in grouped_components.items():
                logger.info(f"📊 计算 {component_type} 工程量，共 {len(component_list)} 个构件")
                
                type_quantities = []
                type_summary = {'volume': 0.0, 'area': 0.0, 'count': 0}
                
                for component in component_list:
                    try:
                        quantity_result = self._calculate_component_quantity(component_type, component)
                        if quantity_result:
                            type_quantities.append(quantity_result.__dict__)
                            type_summary['volume'] += quantity_result.volume
                            type_summary['area'] += quantity_result.area
                            type_summary['count'] += quantity_result.quantity
                    except Exception as e:
                        logger.error(f"处理构件失败: {component.get('name', 'N/A')}, 错误: {e}", exc_info=True)
                
                quantities[component_type] = {
                    'items': type_quantities,
                    'summary': type_summary
                }
                
                # 累计到总计
                total_summary['total_volume'] += type_summary['volume']
                total_summary['total_area'] += type_summary['area']
                total_summary['total_count'] += type_summary['count']
            
            logger.info(f"✅ 工程量计算完成，总构件数: {total_summary['total_count']}")
            
            return {
                'status': 'success',
                'quantities': quantities,
                'total_summary': total_summary,
                'calculation_time': self._get_current_time(),
                'component_types_found': list(grouped_components.keys()),
                'total_components': len(components)
            }
            
        except Exception as e:
            logger.error(f"❌ 工程量计算失败: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error_message': str(e),
                'quantities': {},
                'total_summary': {'total_volume': 0.0, 'total_area': 0.0, 'total_count': 0}
            }
    
    def _group_components_by_type(self, components: List[Dict]) -> Dict[str, List[Dict]]:
        """按构件类型分组"""
        grouped = {}
        
        for component in components:
            component_type = self._normalize_component_type(component.get('type', ''))
            if component_type:
                if component_type not in grouped:
                    grouped[component_type] = []
                grouped[component_type].append(component)
        
        return grouped
    
    def _normalize_component_type(self, component_type: str) -> str:
        """标准化构件类型名称"""
        if not component_type:
            return ''
        
        component_type = component_type.lower().strip()
        
        # 墙体类型映射
        if any(keyword in component_type for keyword in ['墙', 'wall', '隔墙', '承重墙']):
            return 'wall'
        # 柱子类型映射
        elif any(keyword in component_type for keyword in ['柱', 'column', '立柱']):
            return 'column'
        # 梁类型映射
        elif any(keyword in component_type for keyword in ['梁', 'beam', '横梁', '主梁', '次梁']):
            return 'beam'
        # 板类型映射
        elif any(keyword in component_type for keyword in ['板', 'slab', '楼板', '屋面板']):
            return 'slab'
        # 基础类型映射
        elif any(keyword in component_type for keyword in ['基础', 'foundation', '地基', '承台']):
            return 'foundation'
        else:
            logger.warning(f"⚠️ 未识别的构件类型: {component_type}")
            return 'unknown'
    
    def _calculate_component_quantity(self, component_type: str, component: Any) -> Optional[ComponentQuantity]:
        """计算单个构件的工程量, 增加健壮性处理"""
        if isinstance(component, str):
            try:
                component = json.loads(component)
            except json.JSONDecodeError:
                logger.error(f"构件数据格式错误，无法解析JSON字符串: {component}")
                return None
        
        if not isinstance(component, dict):
            logger.error(f"构件数据类型错误，期望为dict，实际为{type(component)}: {component}")
            return None

        handler = self.component_handlers.get(component_type)
        if handler:
            try:
                return handler(component)
            except AttributeError as e:
                logger.error(f"计算构件 '{component.get('name', 'Unknown')}' 时发生属性错误: {e}. 构件数据: {component}", exc_info=True)
                return None
            except Exception as e:
                logger.error(f"计算构件 '{component.get('name', 'Unknown')}' 时发生未知错误: {e}. 构件数据: {component}", exc_info=True)
                return None
        else:
            logger.warning(f"⚠️ 没有找到构件类型 {component_type} 的计算方法")
            return None
    
    def _calculate_wall_quantity(self, component: Dict) -> Optional[ComponentQuantity]:
        """计算墙体工程量"""
        try:
            # 提取尺寸信息
            dimensions = self._extract_dimensions(component)
            length = dimensions.get('length', 0.0)
            height = dimensions.get('height', 0.0)
            thickness = dimensions.get('thickness', 0.24)  # 默认240mm
            
            if length == 0.0 or height == 0.0:
                logger.warning(f"⚠️ 墙体构件 '{component.get('name', 'N/A')}' 缺少关键尺寸(长度/高度)，跳过计算。尺寸: {dimensions}")
                return None

            quantity = component.get('quantity', 1)
            
            # 计算工程量
            volume = length * height * thickness * quantity  # 体积 = 长×高×厚×数量
            area = length * height * quantity  # 面积 = 长×高×数量
            
            return ComponentQuantity(
                component_type='wall',
                name=component.get('name', '墙体'),
                dimensions={'length': length, 'height': height, 'thickness': thickness},
                quantity=quantity,
                volume=volume,
                area=area,
                unit='m³/m²',
                calculation_method=f'体积={length}×{height}×{thickness}×{quantity}={volume:.2f}m³, 面积={length}×{height}×{quantity}={area:.2f}m²'
            )
            
        except Exception as e:
            logger.error(f"❌ 墙体工程量计算失败: {str(e)}", exc_info=True)
            return self._create_default_quantity('wall', component)
    
    def _calculate_column_quantity(self, component: Dict) -> Optional[ComponentQuantity]:
        """计算柱子工程量"""
        try:
            dimensions = self._extract_dimensions(component)
            length = dimensions.get('length', 0.0)
            width = dimensions.get('width', 0.0)
            height = dimensions.get('height', 0.0)

            if (length == 0.0 or width == 0.0) and dimensions.get('diameter', 0.0) == 0.0:
                 logger.warning(f"⚠️ 柱构件 '{component.get('name', 'N/A')}' 缺少关键截面尺寸(长/宽/直径)，跳过计算。尺寸: {dimensions}")
                 return None
            if height == 0.0:
                logger.warning(f"⚠️ 柱构件 '{component.get('name', 'N/A')}' 缺少高度，跳过计算。尺寸: {dimensions}")
                return None

            quantity = component.get('quantity', 1)
            
            # 计算工程量
            volume = length * width * height * quantity  # 体积 = 长×宽×高×数量
            area = length * width * quantity  # 截面积 = 长×宽×数量
            
            return ComponentQuantity(
                component_type='column',
                name=component.get('name', '柱子'),
                dimensions={'length': length, 'width': width, 'height': height},
                quantity=quantity,
                volume=volume,
                area=area,
                unit='m³/m²',
                calculation_method=f'体积={length}×{width}×{height}×{quantity}={volume:.2f}m³, 截面积={length}×{width}×{quantity}={area:.2f}m²'
            )
            
        except Exception as e:
            logger.error(f"❌ 柱子工程量计算失败: {str(e)}", exc_info=True)
            return self._create_default_quantity('column', component)
    
    def _calculate_beam_quantity(self, component: Dict) -> Optional[ComponentQuantity]:
        """计算梁工程量"""
        try:
            dimensions = self._extract_dimensions(component)
            length = dimensions.get('length', 0.0)
            width = dimensions.get('width', 0.0)
            height = dimensions.get('height', 0.0)

            if length == 0.0 or width == 0.0 or height == 0.0:
                logger.warning(f"⚠️ 梁构件 '{component.get('name', 'N/A')}' 缺少关键尺寸，跳过计算。尺寸: {dimensions}")
                return None
            
            quantity = component.get('quantity', 1)
            
            # 计算工程量
            volume = length * width * height * quantity  # 体积 = 长×宽×高×数量
            area = width * height * quantity  # 截面积 = 宽×高×数量
            
            return ComponentQuantity(
                component_type='beam',
                name=component.get('name', '梁'),
                dimensions={'length': length, 'width': width, 'height': height},
                quantity=quantity,
                volume=volume,
                area=area,
                unit='m³/m²',
                calculation_method=f'体积={length}×{width}×{height}×{quantity}={volume:.2f}m³, 截面积={width}×{height}×{quantity}={area:.2f}m²'
            )
            
        except Exception as e:
            logger.error(f"❌ 梁工程量计算失败: {str(e)}", exc_info=True)
            return self._create_default_quantity('beam', component)
    
    def _calculate_slab_quantity(self, component: Dict) -> Optional[ComponentQuantity]:
        """计算板工程量"""
        try:
            dimensions = self._extract_dimensions(component)
            length = dimensions.get('length', 0.0)
            width = dimensions.get('width', 0.0)
            thickness = dimensions.get('thickness', 0.15) # 默认150mm

            if length == 0.0 or width == 0.0 or thickness == 0.0:
                logger.warning(f"⚠️ 板构件 '{component.get('name', 'N/A')}' 缺少关键尺寸，跳过计算。尺寸: {dimensions}")
                return None

            quantity = component.get('quantity', 1)
            
            # 计算工程量
            volume = length * width * thickness * quantity  # 体积 = 长×宽×厚×数量
            area = length * width * quantity  # 面积 = 长×宽×数量
            
            return ComponentQuantity(
                component_type='slab',
                name=component.get('name', '板'),
                dimensions={'length': length, 'width': width, 'thickness': thickness},
                quantity=quantity,
                volume=volume,
                area=area,
                unit='m³/m²',
                calculation_method=f'面积={length}×{width}×{quantity}={area:.2f}m², 体积={length}×{width}×{thickness}×{quantity}={volume:.2f}m³'
            )
            
        except Exception as e:
            logger.error(f"❌ 板工程量计算失败: {str(e)}")
            return self._create_default_quantity('slab', component)
    
    def _calculate_foundation_quantity(self, component: Dict) -> Optional[ComponentQuantity]:
        """计算基础工程量"""
        try:
            dimensions = self._extract_dimensions(component)
            length = dimensions.get('length', 0.0)
            width = dimensions.get('width', 0.0)
            height = dimensions.get('height', 0.0)

            if length == 0.0 or width == 0.0 or height == 0.0:
                logger.warning(f"⚠️ 基础构件 '{component.get('name', 'N/A')}' 缺少关键尺寸，跳过计算。尺寸: {dimensions}")
                return None

            quantity = component.get('quantity', 1)

            # 计算工程量
            volume = length * width * height * quantity
            area = length * width * quantity  # 底面积 = 长×宽×数量
            
            return ComponentQuantity(
                component_type='foundation',
                name=component.get('name', '基础'),
                dimensions={'length': length, 'width': width, 'height': height},
                quantity=quantity,
                volume=volume,
                area=area,
                unit='m³/m²',
                calculation_method=f'体积={length}×{width}×{height}×{quantity}={volume:.2f}m³'
            )
            
        except Exception as e:
            logger.error(f"❌ 基础工程量计算失败: {str(e)}")
            return self._create_default_quantity('foundation', component)
    
    def _extract_dimensions(self, component: Dict) -> Dict[str, float]:
        """
        提取尺寸信息, 增加对字符串格式的兼容
        尺寸单位统一为米
        """
        dims_data = component.get('dimensions', component.get('size', {}))
        
        if isinstance(dims_data, str):
            try:
                dims_data = json.loads(dims_data.replace("'", "\""))
            except json.JSONDecodeError:
                logger.warning(f"尺寸格式错误，无法解析JSON字符串: {dims_data}")
                dims_data = {}

        if not isinstance(dims_data, dict):
             logger.warning(f"尺寸数据类型错误，期望为dict，实际为{type(dims_data)}: {dims_data}")
             return {}

        dimensions = {}
        # 常见尺寸关键词映射
        dimension_keys = {
            'length': ['length', '长', 'l'],
            'width': ['width', '宽', 'w', 'b'],
            'height': ['height', '高', 'h'],
            'thickness': ['thickness', '厚', 't'],
            'diameter': ['diameter', '直径', 'd']
        }

        for key, aliases in dimension_keys.items():
            for alias in aliases:
                if alias in dims_data:
                    value = self._to_float(dims_data[alias])
                    # 假定单位为mm，转换为m
                    if value > 10: # 简单判断，大于10的数值可能单位是mm
                        value /= 1000
                    dimensions[key] = value
                    break # 找到一个别名就跳出
        
        # 尝试从 bxh 格式解析
        if 'bxh' in dims_data and 'width' not in dimensions and 'height' not in dimensions:
            try:
                parts = str(dims_data['bxh']).split('x')
                if len(parts) == 2:
                    width = self._to_float(parts[0]) / 1000
                    height = self._to_float(parts[1]) / 1000
                    dimensions.setdefault('width', width)
                    dimensions.setdefault('height', height)
            except (ValueError, IndexError):
                pass
                
        return dimensions

    def _to_float(self, value: Any) -> float:
        """安全地将值转换为浮点数"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _create_default_quantity(self, component_type: str, component: Dict) -> ComponentQuantity:
        """创建默认工程量对象, 用于错误回退"""
        name = component.get('name', '未知构件')
        logger.warning(f"为构件 '{name}' ({component_type}) 创建默认(0)工程量对象")
        return ComponentQuantity(
            component_type=component_type,
            name=name,
            dimensions={'length': 1.0, 'width': 1.0, 'height': 1.0},
            quantity=component.get('quantity', 1),
            volume=1.0,
            area=1.0,
            unit='m³/m²',
            calculation_method='使用默认值计算'
        )
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """创建空的计算结果"""
        return {
            'status': 'success',
            'quantities': {},
            'total_summary': {'total_volume': 0.0, 'total_area': 0.0, 'total_count': 0},
            'calculation_time': self._get_current_time(),
            'component_types_found': [],
            'total_components': 0
        }
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 创建全局工程量计算器实例
quantity_calculator = QuantityCalculator()