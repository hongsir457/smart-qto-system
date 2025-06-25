# -*- coding: utf-8 -*-
"""
建筑专业文本校正模块
基于建筑施工图纸的制图规范和专业名词对OCR识别结果进行校正
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import json

logger = logging.getLogger(__name__)

class ConstructionTextCorrector:
    """建筑专业文本校正器"""
    
    def __init__(self):
        """初始化校正器"""
        self._load_dictionaries()
        self._compile_patterns()
        
    def _load_dictionaries(self):
        """加载建筑专业词典"""
        
        # 构件类型词典
        self.component_types = {
            # 柱类
            'KZ': ['框架柱', '抗震柱'],
            'GZ': ['构造柱'],
            'XZ': ['小柱'],
            'KZZ': ['框支柱'],
            'QZ': ['剪力墙柱'],
            'YZ': ['约束柱'],
            'JKZ': ['加强框架柱'],
            
            # 梁类
            'KL': ['框架梁'],
            'LL': ['连梁'],
            'JL': ['基础梁'],
            'GL': ['过梁'],
            'XL': ['小梁'],
            'WKL': ['屋面框架梁'],
            'LWL': ['楼梯梁'],
            'TL': ['挑梁'],
            'AL': ['暗梁'],
            'CL': ['次梁'],
            
            # 板类
            'KB': ['楼板', '现浇板'],
            'WB': ['屋面板'],
            'YJB': ['预制板'],
            'LTB': ['楼梯板'],
            'PB': ['平板'],
            'ZGB': ['钢筋混凝土板'],
            
            # 墙类
            'Q': ['剪力墙'],
            'QQ': ['砌体墙'],
            'FQ': ['分隔墙'],
            'WQ': ['围护墙'],
            'DQ': ['挡土墙'],
            
            # 基础类
            'JC': ['基础'],
            'DJ': ['独立基础'],
            'TJ': ['条形基础'],
            'FJ': ['筏板基础'],
            'ZJ': ['桩基础'],
            'CFG': ['CFG桩'],
            
            # 楼梯类
            'LT': ['楼梯'],
            'LTD': ['楼梯段'],
            'XD': ['休息平台'],
            
            # 其他
            'FT': ['封头'],
            'DP': ['挡板'],
            'YT': ['雨篷'],
        }
        
        # 材料等级词典
        self.concrete_grades = [
            'C10', 'C15', 'C20', 'C25', 'C30', 'C35', 'C40', 'C45', 'C50',
            'C55', 'C60', 'C65', 'C70', 'C75', 'C80'
        ]
        
        self.steel_grades = [
            'HPB300', 'HRB335', 'HRB400', 'HRB500', 'HRBF335', 'HRBF400', 'HRBF500',
            'Q235', 'Q345', 'Q390', 'Q420', 'Q460'
        ]
        
        # 尺寸单位词典
        self.dimension_units = [
            'mm', 'cm', 'm', '米', '毫米', '厘米'
        ]
        
        # 常见错误映射
        self.common_errors = {
            # 数字易错
            '0': ['O', 'o', '○'],
            '1': ['I', 'l', '|'],
            '2': ['Z'],
            '3': ['8'],
            '5': ['S', 's'],
            '6': ['G'],
            '8': ['B'],
            '9': ['g'],
            
            # 字母易错
            'B': ['8', '6'],
            'D': ['0', 'O'],
            'G': ['6', 'C'],
            'I': ['1', 'l'],
            'O': ['0', 'Q'],
            'Q': ['0', 'O'],
            'S': ['5'],
            'Z': ['2'],
            
            # 中文易错
            '框': ['框'],
            '梁': ['粱'],
            '柱': ['住'],
            '板': ['扳'],
            '墙': ['强'],
            '基': ['基'],
            '础': ['础'],
            '混': ['混'],
            '凝': ['凝'],
            '土': ['土'],
            '钢': ['钢'],
            '筋': ['筋'],
        }
        
        # 专业术语词典
        self.professional_terms = [
            '建筑结构', '结构设计', '施工图', '平面图', '立面图', '剖面图',
            '详图', '节点详图', '配筋图', '布置图', '模板图',
            '现浇', '预制', '装配式', '钢筋混凝土', '预应力',
            '抗震', '抗风', '荷载', '承载力', '刚度', '稳定性',
            '基础', '地基', '桩基', '承台', '地梁', '防水',
            '保温', '隔热', '防火', '防腐', '耐久性',
            '施工缝', '后浇带', '伸缩缝', '沉降缝', '抗震缝',
            '钢筋', '箍筋', '主筋', '分布筋', '构造筋', '锚固',
            '搭接', '连接', '焊接', '机械连接', '绑扎',
            '混凝土', '水泥', '砂浆', '外加剂', '掺合料',
            '模板', '支撑', '脚手架', '安全网', '防护栏',
            '质量', '检验', '验收', '监理', '试验', '检测'
        ]
        
    def _compile_patterns(self):
        """编译正则表达式模式"""
        
        # 构件编号模式
        self.component_pattern = re.compile(
            r'([A-Z]{1,4})[-_]?(\d+)[A-Z]?',
            re.IGNORECASE
        )
        
        # 尺寸模式（如 300×400, 500*600, 200x300）
        self.dimension_pattern = re.compile(
            r'(\d+)\s*[×x*]\s*(\d+)(?:\s*[×x*]\s*(\d+))?(?:mm|cm|m)?',
            re.IGNORECASE
        )
        
        # 材料等级模式
        self.concrete_pattern = re.compile(
            r'C\d{2,3}',
            re.IGNORECASE
        )
        
        self.steel_pattern = re.compile(
            r'(HPB|HRB|HRBF|Q)\d{3,4}',
            re.IGNORECASE
        )
        
        # 数字模式
        self.number_pattern = re.compile(r'\d+')
        
    def correct_text(self, text: str, confidence: float = 0.0) -> Dict[str, any]:
        """
        校正OCR识别的文本
        
        Args:
            text: 原始OCR文本
            confidence: OCR置信度
            
        Returns:
            Dict: 校正结果
        """
        try:
            original_text = text
            corrected_text = text
            corrections = []
            
            # 1. 构件编号校正
            corrected_text, component_corrections = self._correct_component_codes(corrected_text)
            corrections.extend(component_corrections)
            
            # 2. 尺寸标注校正
            corrected_text, dimension_corrections = self._correct_dimensions(corrected_text)
            corrections.extend(dimension_corrections)
            
            # 3. 材料等级校正
            corrected_text, material_corrections = self._correct_materials(corrected_text)
            corrections.extend(material_corrections)
            
            # 4. 专业术语校正
            corrected_text, term_corrections = self._correct_professional_terms(corrected_text)
            corrections.extend(term_corrections)
            
            # 5. 常见错误校正
            corrected_text, error_corrections = self._correct_common_errors(corrected_text)
            corrections.extend(error_corrections)
            
            # 计算校正信心度
            correction_confidence = self._calculate_correction_confidence(
                original_text, corrected_text, confidence, corrections
            )
            
            return {
                'original_text': original_text,
                'corrected_text': corrected_text,
                'corrections': corrections,
                'correction_confidence': correction_confidence,
                'is_corrected': len(corrections) > 0,
                'correction_count': len(corrections)
            }
            
        except Exception as e:
            logger.error(f"文本校正失败: {str(e)}")
            return {
                'original_text': text,
                'corrected_text': text,
                'corrections': [],
                'correction_confidence': confidence,
                'is_corrected': False,
                'correction_count': 0
            }
    
    def _correct_component_codes(self, text: str) -> Tuple[str, List[Dict]]:
        """校正构件编号"""
        corrections = []
        corrected_text = text
        
        # 查找可能的构件编号
        matches = self.component_pattern.finditer(text)
        
        for match in matches:
            original = match.group(0)
            prefix = match.group(1).upper()
            number = match.group(2)
            
            # 检查前缀是否在已知构件类型中
            best_match = self._find_best_component_match(prefix)
            
            if best_match and best_match != prefix:
                corrected = f"{best_match}-{number}"
                corrected_text = corrected_text.replace(original, corrected)
                
                corrections.append({
                    'type': 'component_code',
                    'original': original,
                    'corrected': corrected,
                    'reason': f'构件类型校正: {prefix} -> {best_match}',
                    'confidence': 0.9
                })
        
        return corrected_text, corrections
    
    def _find_best_component_match(self, prefix: str) -> Optional[str]:
        """查找最佳匹配的构件类型"""
        # 精确匹配
        if prefix in self.component_types:
            return prefix
            
        # 模糊匹配
        best_match = None
        best_score = 0.6  # 最低匹配阈值
        
        for known_prefix in self.component_types.keys():
            score = SequenceMatcher(None, prefix, known_prefix).ratio()
            if score > best_score:
                best_score = score
                best_match = known_prefix
                
        return best_match
    
    def _correct_dimensions(self, text: str) -> Tuple[str, List[Dict]]:
        """校正尺寸标注"""
        corrections = []
        corrected_text = text
        
        # 查找尺寸模式并规范化
        def replace_dimension(match):
            original = match.group(0)
            dim1 = match.group(1)
            dim2 = match.group(2)
            dim3 = match.group(3) if match.group(3) else None
            
            # 规范化尺寸格式
            if dim3:
                corrected = f"{dim1}×{dim2}×{dim3}"
            else:
                corrected = f"{dim1}×{dim2}"
            
            if original != corrected:
                corrections.append({
                    'type': 'dimension',
                    'original': original,
                    'corrected': corrected,
                    'reason': '尺寸格式规范化',
                    'confidence': 0.95
                })
            
            return corrected
        
        corrected_text = self.dimension_pattern.sub(replace_dimension, corrected_text)
        
        return corrected_text, corrections
    
    def _correct_materials(self, text: str) -> Tuple[str, List[Dict]]:
        """校正材料等级"""
        corrections = []
        corrected_text = text
        
        # 混凝土等级校正
        concrete_matches = self.concrete_pattern.finditer(text)
        for match in concrete_matches:
            original = match.group(0)
            grade = original.upper()
            
            # 检查是否为有效等级
            if grade in self.concrete_grades:
                if original != grade:
                    corrected_text = corrected_text.replace(original, grade)
                    corrections.append({
                        'type': 'concrete_grade',
                        'original': original,
                        'corrected': grade,
                        'reason': '混凝土等级格式校正',
                        'confidence': 0.9
                    })
            else:
                # 查找最接近的等级
                best_match = self._find_closest_concrete_grade(grade)
                if best_match:
                    corrected_text = corrected_text.replace(original, best_match)
                    corrections.append({
                        'type': 'concrete_grade',
                        'original': original,
                        'corrected': best_match,
                        'reason': f'混凝土等级校正: {grade} -> {best_match}',
                        'confidence': 0.8
                    })
        
        # 钢筋等级校正
        steel_matches = self.steel_pattern.finditer(text)
        for match in steel_matches:
            original = match.group(0)
            grade = original.upper()
            
            if grade in self.steel_grades:
                if original != grade:
                    corrected_text = corrected_text.replace(original, grade)
                    corrections.append({
                        'type': 'steel_grade',
                        'original': original,
                        'corrected': grade,
                        'reason': '钢筋等级格式校正',
                        'confidence': 0.9
                    })
            else:
                # 查找最接近的等级
                best_match = self._find_closest_steel_grade(grade)
                if best_match:
                    corrected_text = corrected_text.replace(original, best_match)
                    corrections.append({
                        'type': 'steel_grade',
                        'original': original,
                        'corrected': best_match,
                        'reason': f'钢筋等级校正: {grade} -> {best_match}',
                        'confidence': 0.8
                    })
        
        return corrected_text, corrections
    
    def _find_closest_concrete_grade(self, grade: str) -> Optional[str]:
        """查找最接近的混凝土等级"""
        best_match = None
        best_score = 0.7
        
        for known_grade in self.concrete_grades:
            score = SequenceMatcher(None, grade, known_grade).ratio()
            if score > best_score:
                best_score = score
                best_match = known_grade
                
        return best_match
    
    def _find_closest_steel_grade(self, grade: str) -> Optional[str]:
        """查找最接近的钢筋等级"""
        best_match = None
        best_score = 0.7
        
        for known_grade in self.steel_grades:
            score = SequenceMatcher(None, grade, known_grade).ratio()
            if score > best_score:
                best_score = score
                best_match = known_grade
                
        return best_match
    
    def _correct_professional_terms(self, text: str) -> Tuple[str, List[Dict]]:
        """校正专业术语"""
        corrections = []
        corrected_text = text
        
        # 对于每个专业术语，查找可能的错误识别
        for term in self.professional_terms:
            if len(term) > 1:  # 只处理多字符术语
                # 模糊匹配查找相似文本
                for i in range(len(corrected_text) - len(term) + 1):
                    substring = corrected_text[i:i+len(term)]
                    similarity = SequenceMatcher(None, substring, term).ratio()
                    
                    if 0.7 < similarity < 1.0:  # 相似但不完全相同
                        corrected_text = corrected_text.replace(substring, term, 1)
                        corrections.append({
                            'type': 'professional_term',
                            'original': substring,
                            'corrected': term,
                            'reason': f'专业术语校正 (相似度: {similarity:.2f})',
                            'confidence': similarity
                        })
                        break
        
        return corrected_text, corrections
    
    def _correct_common_errors(self, text: str) -> Tuple[str, List[Dict]]:
        """校正常见错误"""
        corrections = []
        corrected_text = text
        
        # 字符级别的错误校正
        for correct_char, error_chars in self.common_errors.items():
            for error_char in error_chars:
                if error_char in corrected_text:
                    # 只在特定上下文中进行替换
                    if self._should_replace_char(corrected_text, error_char, correct_char):
                        corrected_text = corrected_text.replace(error_char, correct_char)
                        corrections.append({
                            'type': 'character_error',
                            'original': error_char,
                            'corrected': correct_char,
                            'reason': '常见字符错误校正',
                            'confidence': 0.8
                        })
        
        return corrected_text, corrections
    
    def _should_replace_char(self, text: str, error_char: str, correct_char: str) -> bool:
        """判断是否应该替换字符（基于上下文）"""
        # 简单的上下文检查
        # 在数字上下文中，更倾向于数字
        # 在字母上下文中，更倾向于字母
        
        char_index = text.find(error_char)
        if char_index == -1:
            return False
            
        # 检查前后字符
        context_before = text[max(0, char_index-2):char_index]
        context_after = text[char_index+1:min(len(text), char_index+3)]
        context = context_before + context_after
        
        # 如果上下文主要是数字，倾向于数字校正
        if correct_char.isdigit():
            digit_count = sum(1 for c in context if c.isdigit())
            return digit_count >= len(context) * 0.5
        
        # 如果上下文主要是字母，倾向于字母校正
        if correct_char.isalpha():
            alpha_count = sum(1 for c in context if c.isalpha())
            return alpha_count >= len(context) * 0.5
        
        return True
    
    def _calculate_correction_confidence(self, original: str, corrected: str, 
                                       ocr_confidence: float, corrections: List[Dict]) -> float:
        """计算校正信心度"""
        if not corrections:
            return ocr_confidence
        
        # 基础信心度来自OCR
        base_confidence = ocr_confidence
        
        # 校正信心度的加权平均
        correction_weights = sum(correction['confidence'] for correction in corrections)
        correction_count = len(corrections)
        
        if correction_count > 0:
            avg_correction_confidence = correction_weights / correction_count
            # 结合OCR信心度和校正信心度
            final_confidence = (base_confidence + avg_correction_confidence) / 2
        else:
            final_confidence = base_confidence
        
        # 确保信心度在合理范围内
        return min(0.99, max(0.1, final_confidence))
    
    def batch_correct(self, text_list: List[Tuple[str, float]]) -> List[Dict]:
        """批量校正文本"""
        results = []
        
        for text, confidence in text_list:
            result = self.correct_text(text, confidence)
            results.append(result)
        
        return results
    
    def get_correction_statistics(self, results: List[Dict]) -> Dict:
        """获取校正统计信息"""
        total_texts = len(results)
        corrected_texts = sum(1 for r in results if r['is_corrected'])
        total_corrections = sum(r['correction_count'] for r in results)
        
        correction_types = {}
        for result in results:
            for correction in result['corrections']:
                correction_type = correction['type']
                correction_types[correction_type] = correction_types.get(correction_type, 0) + 1
        
        return {
            'total_texts': total_texts,
            'corrected_texts': corrected_texts,
            'correction_rate': corrected_texts / total_texts if total_texts > 0 else 0,
            'total_corrections': total_corrections,
            'avg_corrections_per_text': total_corrections / total_texts if total_texts > 0 else 0,
            'correction_types': correction_types
        }

# 创建全局实例
construction_text_corrector = ConstructionTextCorrector() 