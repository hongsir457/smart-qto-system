#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Table Extractor Service - 从OCR结果中识别和提取表格数据
"""
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TableExtractorService:
    """
    使用Pandas和正则表达式从OCR结果中提取表格数据。
    """
    def __init__(self, ocr_results: List[Dict[str, Any]]):
        """
        初始化表格提取器。
        
        Args:
            ocr_results (List[Dict[str, Any]]): 经过处理的、包含'text'和'bbox_xyxy'的OCR区域列表。
        """
        self.ocr_results = sorted(ocr_results, key=lambda r: (r['bbox_xyxy']['y_min'], r['bbox_xyxy']['x_min']))
        self.raw_texts = [res['text'] for res in self.ocr_results]
        logger.info(f"TableExtractorService initialized with {len(self.ocr_results)} OCR text regions.")

    def extract_tables(self) -> List[pd.DataFrame]:
        """
        从OCR结果中提取所有可能的表格。
        
        Returns:
            List[pd.DataFrame]: 提取出的表格，每个表格是一个Pandas DataFrame。
        """
        if not self.ocr_results:
            return []
            
        logger.info("Starting table extraction process...")
        
        # 1. 将文本块聚类成行
        lines = self._cluster_text_into_lines()
        if not lines:
            logger.info("No text lines could be clustered. Aborting table extraction.")
            return []
            
        # 2. 识别表格区域（此为简化实现，未来可增强）
        # 简单的假设：连续的多行文本构成一个表格
        potential_tables = self._identify_table_blocks(lines)
        
        # 3. 为每个潜在表格构建DataFrame
        extracted_dataframes = []
        for i, table_block in enumerate(potential_tables):
            logger.info(f"Processing potential table block #{i+1} with {len(table_block)} lines.")
            df = self._build_dataframe_from_block(table_block)

            # 仅在DataFrame非空时进行处理和打印
            if not df.empty:
                extracted_dataframes.append(df)
                logger.info(f"✅ Successfully extracted table #{i+1} with shape {df.shape}.")
                
                # 使用 rich-pandas 或其他方式在日志中漂亮地打印DataFrame
                try:
                    from rich.console import Console
                    from rich.table import Table
                    
                    console = Console()
                    rich_table = Table(show_header=True, header_style="bold magenta", title=f"Extracted Table #{i+1}")
                    
                    # 添加列
                    for col in df.columns:
                        rich_table.add_column(str(col))
                    
                    # 添加行
                    for index, row in df.iterrows():
                        # 将每行的数据转换为字符串
                        rich_table.add_row(*[str(item) for item in row.values])
                        
                    console.print(rich_table)
                    
                except ImportError:
                    logger.info(f"Table #{i+1} content (rich library not found):\n{df.to_string()}")
                except Exception as e:
                    logger.warning(f"Could not print table with rich, falling back. Error: {e}\n{df.to_string()}")
            else:
                logger.warning(f"⚠️ Could not extract a valid DataFrame from table block #{i+1}.")

        logger.info(f"Table extraction complete. Found {len(extracted_dataframes)} valid tables.")
        return extracted_dataframes

    def _cluster_text_into_lines(self, y_tolerance: int = 10) -> List[List[Dict]]:
        """
        将离散的文本块按垂直位置聚类成行。
        
        Args:
            y_tolerance (int): 垂直方向上合并为一行的容差（像素）。
        
        Returns:
            List[List[Dict]]: 文本行的列表，每行是按x坐标排序的文本块列表。
        """
        if not self.ocr_results:
            return []
            
        lines = []
        current_line = [self.ocr_results[0]]
        
        for i in range(1, len(self.ocr_results)):
            prev_bbox = current_line[-1]['bbox_xyxy']
            curr_bbox = self.ocr_results[i]['bbox_xyxy']
            
            # 检查Y坐标是否在容差范围内
            is_same_line = abs(prev_bbox['y_min'] - curr_bbox['y_min']) < y_tolerance
            
            if is_same_line:
                current_line.append(self.ocr_results[i])
            else:
                lines.append(sorted(current_line, key=lambda r: r['bbox_xyxy']['x_min']))
                current_line = [self.ocr_results[i]]
        
        # 添加最后一行
        lines.append(sorted(current_line, key=lambda r: r['bbox_xyxy']['x_min']))
        
        logger.info(f"Clustered {len(self.ocr_results)} text blocks into {len(lines)} lines.")
        return lines
        
    def _identify_table_blocks(self, lines: List[List[Dict]], min_lines_for_table: int = 2) -> List[List[List[Dict]]]:
        """
        (简化实现) 从文本行中识别出可能是表格的块。
        这里简单地将所有行视为一个大表格块。
        """
        if len(lines) >= min_lines_for_table:
            logger.info("Identified one potential table block from all lines.")
            return [lines]
        else:
            logger.warning(f"Not enough lines ({len(lines)}) to form a table (min: {min_lines_for_table}).")
            return []

    def _build_dataframe_from_block(self, block: List[List[Dict]]) -> pd.DataFrame:
        """
        从一个文本块中构建Pandas DataFrame。
        这是一个复杂的任务，核心是确定列的边界。
        """
        if not block:
            return pd.DataFrame()

        # 估算列边界
        # 策略：找到所有文本块的x中点，然后对这些中点进行聚类
        x_centers = []
        for line in block:
            for item in line:
                bbox = item['bbox_xyxy']
                x_centers.append((bbox['x_min'] + bbox['x_max']) / 2)
        
        # 简单的聚类：对x中心点排序并寻找大的间隔来定义列
        sorted_x_centers = sorted(list(set(x_centers)))
        if not sorted_x_centers:
            return pd.DataFrame()
            
        column_boundaries = [sorted_x_centers[0] -1]
        for i in range(1, len(sorted_x_centers)):
            # 如果两个文本中心的距离大于一个典型的字符宽度（估算值），则认为是一个新的列
            if sorted_x_centers[i] - sorted_x_centers[i-1] > 50: # 50像素作为一个阈值
                column_boundaries.append((sorted_x_centers[i] + sorted_x_centers[i-1]) / 2)
        column_boundaries.append(sorted_x_centers[-1] + 50)

        # 构建表格数据
        table_data = []
        for line in block:
            row_data = ["" for _ in range(len(column_boundaries) - 1)]
            for item in line:
                bbox = item['bbox_xyxy']
                center_x = (bbox['x_min'] + bbox['x_max']) / 2
                
                # 找到这个item属于哪一列
                for j in range(len(column_boundaries) - 1):
                    if column_boundaries[j] <= center_x < column_boundaries[j+1]:
                        row_data[j] += f" {item['text']}" # 同一单元格可能有多个文本块
                        break
            table_data.append([cell.strip() for cell in row_data])

        try:
            df = pd.DataFrame(table_data)
            # 可以设置第一行作为表头
            # df.columns = df.iloc[0]
            # df = df[1:]
            return df
        except Exception as e:
            logger.error(f"Failed to create DataFrame: {e}")
            return pd.DataFrame()
            
    def _parse_cell_with_regex(self, cell_content: str) -> Dict[str, Any]:
        """
        (占位符) 使用正则表达式解析单元格内容。
        """
        # 示例：解析 "Φ8@200"
        import re
        pattern = re.compile(r"Φ(\d+)@(\d+)")
        match = pattern.match(cell_content)
        if match:
            return {"type": "rebar", "diameter": int(match.group(1)), "spacing": int(match.group(2))}
        
        return {"raw_text": cell_content} 