#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图框信息提取器
专门负责从图框区域提取图号、标题、比例等信息
"""

import logging
from typing import Any, Tuple, Dict

logger = logging.getLogger(__name__)

class FrameInfoExtractor:
    """图框信息提取器类"""
    def extract_frame_info(self, doc: Any, bounds: Tuple[float, float, float, float], index: int) -> Dict:
        """
        从图框区域提取图纸信息
        Args:
            doc: ezdxf文档对象
            bounds: 图框边界
            index: 图框索引
        Returns:
            图框信息字典
        """
        try:
            # 在图框附近查找文本，提取图号、标题、比例等信息
            texts_in_frame = self._find_texts_in_area(doc, bounds)
            # 解析文本，提取图纸信息
            drawing_number = self._extract_drawing_number(texts_in_frame, index)
            title = self._extract_drawing_title(texts_in_frame, index)
            scale = self._extract_drawing_scale(texts_in_frame)
            return {
                "index": index,
                "bounds": bounds,
                "drawing_number": drawing_number,
                "title": title,
                "scale": scale,
                "texts": texts_in_frame[:10]  # 保留前10个文本用于调试
            }
        except Exception as e:
            logger.error(f"提取图框信息时发生错误: {e}")
            return self._create_default_frame_info(index, bounds)

    def _find_texts_in_area(self, doc: Any, bounds: Tuple[float, float, float, float]):
        """在图框区域查找文本"""
        try:
            texts = []
            min_x, min_y, max_x, max_y = bounds
            if not hasattr(doc, 'modelspace'):
                return texts
            modelspace = doc.modelspace()
            for entity in modelspace:
                if entity.dxftype() in ['TEXT', 'MTEXT']:
                    try:
                        if entity.dxftype() == 'TEXT':
                            position = entity.dxf.insert
                            text_content = entity.dxf.text
                        else:
                            position = entity.dxf.insert
                            text_content = entity.plain_text()
                        if (min_x <= position.x <= max_x and min_y <= position.y <= max_y and text_content.strip()):
                            texts.append(text_content.strip())
                    except Exception:
                        continue
            return texts
        except Exception as e:
            logger.error(f"查找文本时发生错误: {e}")
            return []

    def _extract_drawing_number(self, texts, index):
        """从文本中提取图号"""
        import re
        for text in texts:
            match = re.search(r'图\s*号[：:]*\s*([A-Za-z0-9\-\/]+)', text)
            if match:
                return match.group(1)
        # 兜底
        return f"图纸-{index+1:02d}"

    def _extract_drawing_title(self, texts, index):
        """从文本中提取标题"""
        import re
        for text in texts:
            match = re.search(r'图\s*名[：:]*\s*([^：:\n]+)', text)
            if match:
                return match.group(1)
        # 兜底
        return f"建筑图纸 {index+1}"

    def _extract_drawing_scale(self, texts):
        """从文本中提取比例"""
        import re
        for text in texts:
            match = re.search(r'1\s*[:：]\s*\d+', text)
            if match:
                return match.group(0)
            match = re.search(r'比例\s*[:：]\s*(.+)', text)
            if match:
                return match.group(1)
            match = re.search(r'Scale\s*[:：]\s*(.+)', text)
            if match:
                return match.group(1)
        return "1:100"

    def _create_default_frame_info(self, index: int, bounds: Tuple[float, float, float, float]) -> Dict:
        """创建默认图框信息"""
        return {
            "index": index,
            "bounds": bounds,
            "drawing_number": f"图纸-{index+1:02d}",
            "title": f"建筑图纸 {index+1}",
            "scale": "1:100"
        } 