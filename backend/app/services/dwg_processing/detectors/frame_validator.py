#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图框验证器 - 基于建筑制图标准
专门负责验证图框是否符合GB/T 50001-2017标准
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class FrameValidator:
    """图框验证器类"""
    
    def __init__(self):
        """初始化图框验证器"""
        self.standard_keywords = {
            'drawing_number': ['图号', 'DWG NO', 'Drawing No', '图 号'],
            'title': ['图名', '工程名称', 'Title', '标题'],
            'scale': ['比例', 'Scale', '比 例'],
            'designer': ['设计', 'Designer', '设计者'],
            'checker': ['校核', 'Checker', '校核者'],
            'approver': ['审核', 'Approver', '审核者'],
            'date': ['日期', 'Date', '时间'],
            'project': ['工程', 'Project', '项目'],
            'phase': ['阶段', 'Phase', '设计阶段'],
            'version': ['版本', 'Version', '版 本'],
        }
        
        self.profession_keywords = {
            'architecture': ['建筑', '建施', 'ARCH', 'ARCHITECTURE', '建筑设计'],
            'structure': ['结构', '结施', 'STRUCT', 'STRUCTURE', '结构设计'],
            'electrical': ['电气', '电施', 'ELEC', 'ELECTRICAL', '电气设计'],
            'plumbing': ['给排水', '给水', '排水', 'PLUMB', 'WATER', '给排水设计'],
            'hvac': ['暖通', '通风', 'HVAC', 'VENTILATION', '暖通设计'],
            'landscape': ['景观', '园林', 'LANDSCAPE', 'GARDEN', '景观设计'],
            'interior': ['装修', '室内', 'INTERIOR', 'DECORATION', '装修设计'],
            'fire': ['消防', 'FIRE', 'SAFETY', '消防设计'],
        }
        
        self.phase_keywords = ['方案', '初设', '施工图', 'SCHEME', 'PRELIMINARY', 'CONSTRUCTION']
        
        logger.info("图框验证器初始化完成")
    
    def validate_frame_by_standard(self, modelspace: Any, frame_candidate: Dict[str, Any]) -> float:
        """
        根据建筑制图标准验证图框，返回标准符合度得分（0-10分）
        
        Args:
            modelspace: DXF模型空间
            frame_candidate: 候选图框
            
        Returns:
            标准符合度得分
        """
        bounds = frame_candidate['bounds']
        score = 0.0
        
        try:
            # 图签区域验证（权重3.0）
            title_block_score = self._validate_title_block_standard(modelspace, bounds)
            score += title_block_score * 3.0
            
            # 边框完整性验证（权重2.0）
            border_score = self._validate_border_integrity(modelspace, bounds)
            score += border_score * 2.0
            
            # 标准文本验证（权重2.5）
            text_score = self._validate_standard_texts(modelspace, bounds)
            score += text_score * 2.5
            
            # 印章位置验证（权重1.5）
            seal_score = self._validate_standard_seal_positions(modelspace, bounds)
            score += seal_score * 1.5
            
            # 尺寸标准验证（权重1.0）
            size_score = self._get_size_standard_score(frame_candidate)
            score += size_score * 1.0
            
            # 记录详细得分
            frame_candidate['standard_compliance'] = score
            frame_candidate['compliance_details'] = {
                'title_block': title_block_score,
                'border_integrity': border_score,
                'standard_texts': text_score,
                'seal_positions': seal_score,
                'size_standard': size_score
            }
            
            # 设置图框类型
            if score >= 7.0:
                frame_candidate['frame_type'] = frame_candidate.get('frame_type', 'Standard') + '_EXCELLENT'
            elif score >= 5.0:
                frame_candidate['frame_type'] = frame_candidate.get('frame_type', 'Standard') + '_GOOD'
            elif score >= 3.0:
                frame_candidate['frame_type'] = frame_candidate.get('frame_type', 'Standard') + '_ACCEPTABLE'
            else:
                frame_candidate['frame_type'] = frame_candidate.get('frame_type', 'NonStandard') + '_POOR'
            
            logger.debug(f"图框标准验证详情: 图签={title_block_score:.2f}, 边框={border_score:.2f}, "
                        f"文本={text_score:.2f}, 印章={seal_score:.2f}, 尺寸={size_score:.2f}, 总分={score:.2f}")
                        
        except Exception as e:
            logger.error(f"验证图框标准时出错: {e}")
            frame_candidate['standard_compliance'] = 0.0
            
        return score
    
    def _validate_title_block_standard(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """验证图签区域是否符合GB/T 50001-2017标准"""
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        
        # 图签通常位于右下角
        title_block_bounds = (
            max_x - min(180, width * 0.3),
            min_y,
            max_x,
            min_y + min(80, height * 0.2)
        )
        
        score = 0.0
        title_texts = self._find_texts_in_specific_area(modelspace, title_block_bounds, max_texts=50)
        
        if len(title_texts) < 3:
            return 0.0
        
        # 检查标准内容
        standard_content = {
            'project_name': 0, 'drawing_title': 0, 'drawing_number': 0, 'scale': 0,
            'designer': 0, 'checker': 0, 'approver': 0, 'date': 0,
            'profession': 0, 'phase': 0, 'version': 0, 'unit': 0,
        }
        
        all_text = " ".join(title_texts).upper()
        
        # 检查图号
        if any(keyword in all_text for keyword in self.standard_keywords['drawing_number']):
            standard_content['drawing_number'] = 1
            score += 0.5
        
        # 检查图名/标题
        if any(keyword in all_text for keyword in self.standard_keywords['title']):
            standard_content['drawing_title'] = 1
            score += 0.3
        
        # 检查比例
        if any(keyword in all_text for keyword in self.standard_keywords['scale']):
            standard_content['scale'] = 1
            score += 0.3
        
        # 检查专业
        for profession_type, keywords in self.profession_keywords.items():
            if any(keyword in all_text for keyword in keywords):
                standard_content['profession'] = 1
                score += 0.2
                break
        
        # 检查设计阶段
        if any(keyword in all_text for keyword in self.phase_keywords):
            standard_content['phase'] = 1
            score += 0.2
        
        # 检查责任人
        for role in ['designer', 'checker', 'approver']:
            if any(keyword in all_text for keyword in self.standard_keywords[role]):
                standard_content[role] = 1
                score += 0.1
        
        # 检查日期
        date_patterns = [r'\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}', r'\d{4}\.\d{1,2}', r'\d{4}年\d{1,2}月']
        for pattern in date_patterns:
            if re.search(pattern, all_text):
                standard_content['date'] = 1
                score += 0.1
                break
        
        # 文本数量奖励
        if len(title_texts) >= 10:
            score += 0.2
        elif len(title_texts) >= 6:
            score += 0.1
        
        return min(score, 3.0)  # 最大3分
    
    def _validate_border_integrity(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """验证边框完整性"""
        min_x, min_y, max_x, max_y = bounds
        tolerance = 10  # 10个单位的容差
        
        # 检查四条边框线
        edges = {
            'top': (min_x, max_y, max_x, max_y),      # 上边
            'bottom': (min_x, min_y, max_x, min_y),   # 下边  
            'left': (min_x, min_y, min_x, max_y),     # 左边
            'right': (max_x, min_y, max_x, max_y)     # 右边
        }
        
        found_edges = 0
        entity_count = 0
        
        for entity in modelspace:
            entity_count += 1
            if entity_count > 2000:  # 限制检查数量
                break
                
            if entity.dxftype() == 'LINE':
                try:
                    start = entity.dxf.start
                    end = entity.dxf.end
                    
                    for edge_name, (ex1, ey1, ex2, ey2) in edges.items():
                        # 检查线段是否接近边框线
                        if edge_name in ['top', 'bottom']:  # 水平线
                            if (abs(start.y - ey1) < tolerance and abs(end.y - ey1) < tolerance and
                                abs(start.x - ex1) < tolerance * 5 and abs(end.x - ex2) < tolerance * 5):
                                found_edges += 1
                                break
                        else:  # 垂直线
                            if (abs(start.x - ex1) < tolerance and abs(end.x - ex1) < tolerance and
                                abs(start.y - ey1) < tolerance * 5 and abs(end.y - ey2) < tolerance * 5):
                                found_edges += 1
                                break
                except Exception:
                    continue
        
        # 边框完整性得分
        border_score = found_edges / 4.0  # 最多4条边
        return min(border_score * 2.0, 2.0)  # 最大2分
    
    def _validate_standard_texts(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """验证标准文本"""
        texts = self._find_texts_in_specific_area(modelspace, bounds, max_texts=100)
        
        if len(texts) < 5:
            return 0.0
        
        all_text = " ".join(texts).upper()
        score = 0.0
        
        # 检查尺寸标注
        dimension_patterns = [r'\d+[\.\d]*', r'φ\d+', r'R\d+', r'M\d+']
        dimension_count = 0
        for pattern in dimension_patterns:
            dimension_count += len(re.findall(pattern, all_text))
        
        if dimension_count >= 20:
            score += 0.5
        elif dimension_count >= 10:
            score += 0.3
        elif dimension_count >= 5:
            score += 0.1
        
        # 检查轴线编号
        axis_patterns = [r'[A-Z]\d*', r'\d+[A-Z]', r'[①②③④⑤⑥⑦⑧⑨⑩]']
        axis_count = 0
        for pattern in axis_patterns:
            axis_count += len(re.findall(pattern, all_text))
        
        if axis_count >= 10:
            score += 0.3
        elif axis_count >= 5:
            score += 0.2
        
        # 检查房间标注
        room_keywords = ['客厅', '卧室', '厨房', '卫生间', '阳台', '书房', '餐厅', 'LIVING', 'BEDROOM', 'KITCHEN']
        room_count = sum(1 for keyword in room_keywords if keyword in all_text)
        
        if room_count >= 5:
            score += 0.3
        elif room_count >= 3:
            score += 0.2
        
        # 文本密度奖励
        text_density = len(texts) / ((bounds[2] - bounds[0]) * (bounds[3] - bounds[1]) / 10000)
        if text_density >= 5:
            score += 0.2
        elif text_density >= 2:
            score += 0.1
        
        return min(score, 2.5)  # 最大2.5分
    
    def _validate_standard_seal_positions(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """验证标准印章位置"""
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        
        # 印章通常位于图签区域的特定位置
        seal_areas = [
            # 右下角图签区域
            (max_x - min(160, width * 0.25), min_y, max_x - 20, min_y + min(60, height * 0.15)),
            # 右侧中部
            (max_x - min(100, width * 0.15), min_y + height * 0.3, max_x, min_y + height * 0.7),
        ]
        
        score = 0.0
        
        for seal_area in seal_areas:
            seal_score = self._detect_seal_positions_fast(modelspace, seal_area)
            score += seal_score
        
        return min(score, 1.5)  # 最大1.5分
    
    def _detect_seal_positions_fast(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """快速检测印章位置"""
        min_x, min_y, max_x, max_y = bounds
        seal_indicators = 0
        entity_count = 0
        
        for entity in modelspace:
            entity_count += 1
            if entity_count > 1000:  # 限制检查数量
                break
                
            try:
                if entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    if min_x <= center.x <= max_x and min_y <= center.y <= max_y:
                        radius = entity.dxf.radius
                        if 10 <= radius <= 50:  # 印章大小范围
                            seal_indicators += 1
                            
                elif entity.dxftype() in ['TEXT', 'MTEXT']:
                    if entity.dxftype() == 'TEXT':
                        position = entity.dxf.insert
                        text = entity.dxf.text
                    else:
                        position = entity.dxf.insert
                        text = entity.plain_text()
                    
                    if (min_x <= position.x <= max_x and min_y <= position.y <= max_y):
                        # 检查印章相关文字
                        seal_keywords = ['注册', '执业', '印章', '章', 'SEAL', 'STAMP', '工程师', '建筑师']
                        if any(keyword in text for keyword in seal_keywords):
                            seal_indicators += 1
                            
            except Exception:
                continue
        
        # 印章指示器得分
        if seal_indicators >= 3:
            return 0.5
        elif seal_indicators >= 1:
            return 0.3
        else:
            return 0.0
    
    def _get_size_standard_score(self, frame_candidate: Dict[str, Any]) -> float:
        """获取尺寸标准得分"""
        if 'size_match' not in frame_candidate:
            return 0.0
        
        size_match = frame_candidate['size_match']
        
        if size_match == 'exact':
            return 1.0
        elif size_match == 'approximate':
            return 0.7
        elif size_match in ['relaxed', 'text_derived', 'density_derived']:
            return 0.3
        else:
            return 0.0
    
    def _find_texts_in_specific_area(self, 
                                   modelspace: Any, 
                                   bounds: Tuple[float, float, float, float], 
                                   max_texts: int = 50) -> List[str]:
        """在指定区域查找文本"""
        texts = []
        min_x, min_y, max_x, max_y = bounds
        text_count = 0
        
        for entity in modelspace:
            if text_count >= max_texts:
                break
                
            try:
                if entity.dxftype() == 'TEXT':
                    position = entity.dxf.insert
                    if min_x <= position.x <= max_x and min_y <= position.y <= max_y:
                        text_content = entity.dxf.text.strip()
                        if text_content:
                            texts.append(text_content)
                            text_count += 1
                            
                elif entity.dxftype() == 'MTEXT':
                    position = entity.dxf.insert
                    if min_x <= position.x <= max_x and min_y <= position.y <= max_y:
                        text_content = entity.plain_text().strip()
                        if text_content:
                            texts.append(text_content)
                            text_count += 1
                            
            except Exception:
                continue
        
        return texts 