# -*- coding: utf-8 -*-
"""
建筑专业文本校正模块
"""

import re
import logging
from typing import Dict, List, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class ConstructionTextCorrector:
    """建筑专业文本校正器"""
    
    def __init__(self):
        """初始化"""
        # 构件类型词典
        self.component_types = {
            'KZ': '框架柱', 'GZ': '构造柱', 'KL': '框架梁', 
            'LL': '连梁', 'KB': '楼板', 'Q': '剪力墙'
        }
        
        # 材料等级
        self.concrete_grades = ['C20', 'C25', 'C30', 'C35', 'C40']
        self.steel_grades = ['HPB300', 'HRB400', 'HRB500']
        
        # 编译模式
        self.component_pattern = re.compile(r'([A-Z]{1,3})[-_]?(\d+)', re.IGNORECASE)
        self.dimension_pattern = re.compile(r'(\d+)\s*[×x*]\s*(\d+)', re.IGNORECASE)
        
    def correct_text(self, text: str) -> Dict:
        """校正文本"""
        try:
            original = text
            corrected = text
            corrections = []
            
            # 构件编号校正
            for match in self.component_pattern.finditer(text):
                prefix = match.group(1).upper()
                if prefix in self.component_types:
                    old_text = match.group(0)
                    new_text = f"{prefix}-{match.group(2)}"
                    if old_text != new_text:
                        corrected = corrected.replace(old_text, new_text)
                        corrections.append({
                            'type': 'component',
                            'original': old_text,
                            'corrected': new_text
                        })
            
            # 尺寸标注校正
            def fix_dimension(match):
                return f"{match.group(1)}×{match.group(2)}"
            
            corrected = self.dimension_pattern.sub(fix_dimension, corrected)
            
            return {
                'original_text': original,
                'corrected_text': corrected,
                'corrections': corrections,
                'is_corrected': len(corrections) > 0
            }
            
        except Exception as e:
            logger.error(f"校正失败: {e}")
            return {
                'original_text': text,
                'corrected_text': text,
                'corrections': [],
                'is_corrected': False
            }

# 全局实例
text_corrector = ConstructionTextCorrector() 