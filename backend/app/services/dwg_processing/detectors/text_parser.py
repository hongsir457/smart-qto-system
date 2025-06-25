#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本解析器
专门负责DWG图纸中文本信息的解析和提取
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class TextParser:
    """文本解析器类"""
    
    def __init__(self):
        """初始化文本解析器"""
        self.drawing_number_patterns = [
            r'图\s*号[：:]\s*([A-Za-z0-9\-\/]+)',
            r'Drawing\s*No[\.:]?\s*([A-Za-z0-9\-\/]+)',
            r'DWG\s*NO[\.:]?\s*([A-Za-z0-9\-\/]+)',
            r'([A-Za-z0-9]{2,}-[A-Za-z0-9]{2,})',  # 格式如：XX-XX
        ]
        
        self.scale_patterns = [
            r'比例[：:]\s*1\s*[:：]\s*(\d+)',
            r'Scale\s*[:：]?\s*1\s*[:：]\s*(\d+)',
            r'1\s*[:：]\s*(\d+)',
        ]
        
        self.title_patterns = [
            r'图\s*名[：:]\s*([^：:\n]+)',
            r'Title\s*[:：]?\s*([^：:\n]+)',
            r'工程名称[：:]\s*([^：:\n]+)',
        ]
    
    def extract_texts_from_area(self, 
                               doc: Any, 
                               bounds: Tuple[float, float, float, float],
                               max_texts: int = 100) -> List[Dict[str, Any]]:
        """
        从指定区域提取文本
        
        Args:
            doc: DXF文档对象
            bounds: 区域边界 (min_x, min_y, max_x, max_y)
            max_texts: 最大文本数量
            
        Returns:
            文本信息列表
        """
        try:
            texts = []
            min_x, min_y, max_x, max_y = bounds
            
            if not hasattr(doc, 'modelspace'):
                return texts
                
            modelspace = doc.modelspace()
            count = 0
            
            for entity in modelspace:
                if count >= max_texts:
                    break
                    
                try:
                    if entity.dxftype() in ['TEXT', 'MTEXT']:
                        text_info = self._extract_text_entity(entity)
                        
                        if text_info and self._is_text_in_bounds(text_info, bounds):
                            texts.append(text_info)
                            count += 1
                            
                except Exception as e:
                    # 单个文本实体处理失败，继续处理其他
                    continue
            
            return texts
            
        except Exception as e:
            logger.error(f"区域文本提取失败: {e}")
            return []
    
    def _extract_text_entity(self, entity: Any) -> Optional[Dict[str, Any]]:
        """提取文本实体信息"""
        try:
            text_content = ""
            position = (0, 0)
            height = 10
            
            if entity.dxftype() == 'TEXT':
                text_content = entity.dxf.text
                position = (entity.dxf.insert[0], entity.dxf.insert[1])
                height = getattr(entity.dxf, 'height', 10)
                
            elif entity.dxftype() == 'MTEXT':
                text_content = entity.plain_text()
                position = (entity.dxf.insert[0], entity.dxf.insert[1])
                height = getattr(entity.dxf, 'char_height', 10)
            
            if text_content.strip():
                return {
                    'text': text_content.strip(),
                    'position': position,
                    'height': height,
                    'type': entity.dxftype()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"文本实体提取失败: {e}")
            return None
    
    def _is_text_in_bounds(self, text_info: Dict[str, Any], bounds: Tuple[float, float, float, float]) -> bool:
        """检查文本是否在边界内"""
        try:
            min_x, min_y, max_x, max_y = bounds
            x, y = text_info['position']
            
            return min_x <= x <= max_x and min_y <= y <= max_y
            
        except Exception:
            return False
    
    def parse_drawing_number(self, texts: List[Dict[str, Any]]) -> Optional[str]:
        """
        解析图号
        
        Args:
            texts: 文本信息列表
            
        Returns:
            图号
        """
        try:
            # 合并所有文本
            all_text = " ".join([t['text'] for t in texts])
            
            # 尝试各种模式匹配
            for pattern in self.drawing_number_patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    drawing_number = match.group(1).strip()
                    if len(drawing_number) >= 2:  # 图号至少2个字符
                        return drawing_number
            
            # 如果没有匹配到，尝试找包含数字和字母的较短文本
            for text_info in texts:
                text = text_info['text']
                if re.match(r'^[A-Za-z0-9\-\/]{2,10}$', text):
                    return text
            
            return None
            
        except Exception as e:
            logger.error(f"图号解析失败: {e}")
            return None
    
    def parse_scale(self, texts: List[Dict[str, Any]]) -> Optional[str]:
        """
        解析比例
        
        Args:
            texts: 文本信息列表
            
        Returns:
            比例信息
        """
        try:
            all_text = " ".join([t['text'] for t in texts])
            
            for pattern in self.scale_patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    scale_value = match.group(1)
                    return f"1:{scale_value}"
            
            # 查找常见比例格式
            common_scales = ['1:100', '1:200', '1:50', '1:500', '1:1000']
            for scale in common_scales:
                if scale in all_text:
                    return scale
            
            return None
            
        except Exception as e:
            logger.error(f"比例解析失败: {e}")
            return None
    
    def parse_title(self, texts: List[Dict[str, Any]]) -> Optional[str]:
        """
        解析图纸标题
        
        Args:
            texts: 文本信息列表
            
        Returns:
            图纸标题
        """
        try:
            all_text = " ".join([t['text'] for t in texts])
            
            for pattern in self.title_patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    if len(title) >= 2:
                        return title
            
            # 查找可能的标题（较长的中文文本）
            for text_info in texts:
                text = text_info['text']
                # 查找包含中文且长度适中的文本作为标题
                if re.search(r'[\u4e00-\u9fff]', text) and 3 <= len(text) <= 20:
                    # 排除一些常见的非标题文本
                    exclude_keywords = ['比例', '图号', '日期', '审核', '设计', '制图']
                    if not any(keyword in text for keyword in exclude_keywords):
                        return text
            
            return None
            
        except Exception as e:
            logger.error(f"标题解析失败: {e}")
            return None
    
    def parse_dimensions(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析尺寸标注
        
        Args:
            texts: 文本信息列表
            
        Returns:
            尺寸信息列表
        """
        try:
            dimensions = []
            
            # 尺寸模式：数字+单位
            dimension_pattern = r'(\d+(?:\.\d+)?)\s*(mm|m|cm)?'
            
            for text_info in texts:
                text = text_info['text']
                
                # 查找尺寸标注
                matches = re.findall(dimension_pattern, text)
                for match in matches:
                    value, unit = match
                    try:
                        numeric_value = float(value)
                        if 10 <= numeric_value <= 10000:  # 合理的尺寸范围
                            dimensions.append({
                                'value': numeric_value,
                                'unit': unit or 'mm',
                                'text': text,
                                'position': text_info['position']
                            })
                    except ValueError:
                        continue
            
            return dimensions
            
        except Exception as e:
            logger.error(f"尺寸解析失败: {e}")
            return []
    
    def group_texts_by_proximity(self, texts: List[Dict[str, Any]], threshold: float = 100.0) -> List[List[Dict[str, Any]]]:
        """
        按位置邻近性分组文本
        
        Args:
            texts: 文本信息列表
            threshold: 距离阈值
            
        Returns:
            分组后的文本列表
        """
        try:
            if not texts:
                return []
            
            groups = []
            used = set()
            
            for i, text1 in enumerate(texts):
                if i in used:
                    continue
                    
                group = [text1]
                used.add(i)
                
                for j, text2 in enumerate(texts):
                    if j in used:
                        continue
                        
                    distance = self._calculate_distance(text1['position'], text2['position'])
                    if distance <= threshold:
                        group.append(text2)
                        used.add(j)
                
                groups.append(group)
            
            return groups
            
        except Exception as e:
            logger.error(f"文本分组失败: {e}")
            return [texts]  # 返回原始列表作为单个组
    
    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """计算两点距离"""
        try:
            x1, y1 = pos1
            x2, y2 = pos2
            return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        except:
            return float('inf') 