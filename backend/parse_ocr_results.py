#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建筑图纸OCR结果解析器
将PaddleOCR识别结果转换为专业的建筑工程文档格式
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Any

class BuildingDrawingParser:
    """建筑图纸OCR结果解析器"""
    
    def __init__(self, ocr_data: Dict[str, Any]):
        """初始化解析器"""
        self.ocr_data = ocr_data
        self.texts = self._extract_texts()
        
    def _extract_texts(self) -> List[str]:
        """提取所有识别的文本"""
        texts = []
        for region in self.ocr_data.get('structured_analysis', {}).get('text_regions', []):
            texts.append(region['text'])
        return texts
    
    def parse_project_info(self) -> Dict[str, str]:
        """解析项目基本信息"""
        project_info = {}
        
        # 查找图纸名称
        for text in self.texts:
            if "平面图" in text:
                project_info["图纸类型"] = text
            elif "1:" in text and text.count(":") == 1:
                project_info["比例"] = text
            elif "楼层标商表" in text:
                if "楼层标商表" not in project_info:
                    project_info["楼层标商表"] = []
                project_info.setdefault("楼层标商表", []).append(text)
        
        # 从元数据获取信息
        meta = self.ocr_data.get('meta', {})
        project_info["OCR处理时间"] = meta.get('ocr_time', '')
        project_info["数据格式"] = meta.get('data_format', '')
        project_info["系统版本"] = meta.get('system_version', '')
        
        return project_info
    
    def parse_design_team(self) -> Dict[str, str]:
        """解析设计团队信息"""
        design_team = {}
        
        # 常见的设计人员关键词
        design_keywords = ["制图", "设计", "校核", "审核", "审查"]
        
        for text in self.texts:
            for keyword in design_keywords:
                if keyword in text:
                    design_team[keyword] = text.replace(keyword, "").strip()
        
        # 查找人名（中文姓名模式）
        name_pattern = r'[\u4e00-\u9fff]{2,4}'
        for text in self.texts:
            if re.match(name_pattern, text) and len(text) in [2, 3]:
                if text not in ["设计阶段", "制图", "合同号"]:
                    design_team.setdefault("相关人员", []).append(text)
        
        return design_team
    
    def parse_components(self) -> Dict[str, List[Dict]]:
        """解析构件信息"""
        components = {
            "框架柱": [],
            "其他构件": []
        }
        
        # 框架柱编号模式
        column_patterns = [
            r'K-JKZ\d+[a-zA-Z]*',
            r'IK-JKZ\d+[a-zA-Z]*',
            r'K-KZT',
            r'K-JK\d+[a-zA-Z]*'
        ]
        
        for text in self.texts:
            for pattern in column_patterns:
                if re.match(pattern, text):
                    # 查找对应的文本区域获取位置和置信度
                    for region in self.ocr_data.get('structured_analysis', {}).get('text_regions', []):
                        if region['text'] == text:
                            component = {
                                "编号": text,
                                "置信度": f"{region['confidence']:.1%}",
                                "位置": f"({region['bbox']['center_x']:.0f}, {region['bbox']['center_y']:.0f})",
                                "尺寸": f"{region['bbox']['width']:.0f}×{region['bbox']['height']:.0f}"
                            }
                            components["框架柱"].append(component)
                            break
        
        return components
    
    def parse_materials(self) -> Dict[str, List[str]]:
        """解析材料信息"""
        materials = {
            "混凝土等级": [],
            "其他材料": []
        }
        
        for text in self.texts:
            # 混凝土等级
            if re.match(r'C\d+', text):
                materials["混凝土等级"].append(text)
        
        return materials
    
    def parse_dimensions(self) -> List[Dict]:
        """解析尺寸信息"""
        dimensions = []
        
        for region in self.ocr_data.get('structured_analysis', {}).get('text_regions', []):
            text = region['text']
            
            # 查找数字（可能的尺寸）
            if region.get('is_number') and len(text) >= 3:
                dimensions.append({
                    "数值": text,
                    "置信度": f"{region['confidence']:.1%}",
                    "位置": f"({region['bbox']['center_x']:.0f}, {region['bbox']['center_y']:.0f})",
                    "可能用途": self._guess_dimension_purpose(text)
                })
        
        return dimensions
    
    def _guess_dimension_purpose(self, text: str) -> str:
        """推测尺寸用途"""
        try:
            value = int(text)
            if 200 <= value <= 800:
                return "可能为截面尺寸"
            elif 1000 <= value <= 10000:
                return "可能为跨度或标高"
            elif value >= 10000:
                return "可能为坐标或大尺寸"
            else:
                return "其他尺寸"
        except:
            return "未知"
    
    def parse_quality_info(self) -> Dict[str, Any]:
        """解析OCR识别质量信息"""
        stats = self.ocr_data.get('structured_analysis', {}).get('statistics', {})
        integrity = self.ocr_data.get('data_integrity', {})
        
        return {
            "识别统计": {
                "文本总数": stats.get('total_count', 0),
                "数字识别": stats.get('numeric_count', 0),
                "构件编号": stats.get('component_code_count', 0),
                "平均置信度": f"{stats.get('avg_confidence', 0):.1%}"
            },
            "数据完整性": {
                "原始数据保留": integrity.get('original_data_preserved', False),
                "边框坐标可用": integrity.get('bbox_coordinates_available', False),
                "置信度可用": integrity.get('confidence_scores_available', False),
                "信息丢失率": integrity.get('information_loss', '未知')
            }
        }
    
    def generate_report(self) -> str:
        """生成完整的分析报告"""
        project_info = self.parse_project_info()
        design_team = self.parse_design_team()
        components = self.parse_components()
        materials = self.parse_materials()
        dimensions = self.parse_dimensions()
        quality_info = self.parse_quality_info()
        
        report_lines = [
            "# 建筑结构图纸OCR识别结果整理",
            "",
            "## 📋 项目信息",
            ""
        ]
        
        for key, value in project_info.items():
            if isinstance(value, list):
                report_lines.append(f"**{key}**: {', '.join(value)}")
            else:
                report_lines.append(f"**{key}**: {value}")
        
        report_lines.extend([
            "",
            "## 👥 设计团队信息",
            ""
        ])
        
        for key, value in design_team.items():
            if isinstance(value, list):
                report_lines.append(f"**{key}**: {', '.join(value)}")
            else:
                report_lines.append(f"**{key}**: {value}")
        
        report_lines.extend([
            "",
            "## 🏗️ 构件信息",
            ""
        ])
        
        for comp_type, comp_list in components.items():
            if comp_list:
                report_lines.append(f"### {comp_type}")
                report_lines.append("")
                for comp in comp_list:
                    report_lines.append(f"**{comp['编号']}**")
                    report_lines.append(f"- 置信度: {comp['置信度']}")
                    report_lines.append(f"- 图纸位置: {comp['位置']}")
                    report_lines.append(f"- 识别框尺寸: {comp['尺寸']}")
                    report_lines.append("")
        
        report_lines.extend([
            "## 🧱 材料信息",
            ""
        ])
        
        for mat_type, mat_list in materials.items():
            if mat_list:
                report_lines.append(f"**{mat_type}**: {', '.join(set(mat_list))}")
        
        report_lines.extend([
            "",
            "## 📏 尺寸数据",
            ""
        ])
        
        # 只显示前10个最重要的尺寸
        top_dimensions = sorted(dimensions, key=lambda x: float(x['置信度'][:-1]), reverse=True)[:10]
        for dim in top_dimensions:
            report_lines.append(f"- **{dim['数值']}** ({dim['置信度']}) - {dim['可能用途']}")
        
        report_lines.extend([
            "",
            "## 📊 OCR识别质量分析",
            ""
        ])
        
        stats = quality_info['识别统计']
        integrity = quality_info['数据完整性']
        
        report_lines.extend([
            "### 识别统计",
            f"- 识别文本总数: {stats['文本总数']}",
            f"- 数字识别: {stats['数字识别']}个",
            f"- 构件编号: {stats['构件编号']}个", 
            f"- 平均置信度: {stats['平均置信度']}",
            "",
            "### 数据完整性",
            f"- 原始数据保留: {'✅' if integrity['原始数据保留'] else '❌'}",
            f"- 边框坐标可用: {'✅' if integrity['边框坐标可用'] else '❌'}",
            f"- 置信度可用: {'✅' if integrity['置信度可用'] else '❌'}",
            f"- 信息丢失率: {integrity['信息丢失率']}",
            "",
            "---",
            f"",
            f"**报告生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            f"**数据来源**: PaddleOCR完整原始数据",
            f"**处理方式**: A→C直接数据流，无信息丢失"
        ])
        
        return "\n".join(report_lines)

def parse_ocr_file(file_path: str) -> str:
    """解析OCR文件并生成报告"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
        
        parser = BuildingDrawingParser(ocr_data)
        return parser.generate_report()
        
    except Exception as e:
        return f"解析文件失败: {str(e)}"

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        report = parse_ocr_file(file_path)
        print(report)
    else:
        print("请提供OCR结果JSON文件路径")
        print("用法: python parse_ocr_results.py <json_file_path>") 