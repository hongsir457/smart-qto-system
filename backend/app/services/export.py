import pandas as pd
from typing import Dict, Any
from pathlib import Path
import os

class ExportService:
    @staticmethod
    def export_quantities_to_excel(quantities: Dict[str, Any], output_path: str) -> str:
        """
        将工程量计算结果导出为Excel文件
        
        Args:
            quantities: 工程量计算结果
            output_path: 输出文件路径
            
        Returns:
            str: 生成的Excel文件路径
        """
        # 创建输出目录
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建一个Excel写入器
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 导出墙体工程量
            if quantities["walls"]:
                walls_df = pd.DataFrame([
                    {
                        "ID": wall["id"],
                        "类型": wall["type"],
                        "材料": wall["material"],
                        "长度(m)": wall["quantities"]["length"],
                        "面积(m²)": wall["quantities"]["area"],
                        "体积(m³)": wall["quantities"]["volume"]
                    }
                    for wall in quantities["walls"]
                ])
                walls_df.to_excel(writer, sheet_name="墙体工程量", index=False)
            
            # 导出柱子工程量
            if quantities["columns"]:
                columns_df = pd.DataFrame([
                    {
                        "ID": column["id"],
                        "类型": column["type"],
                        "材料": column["material"],
                        "截面面积(m²)": column["quantities"]["area"],
                        "高度(m)": column["quantities"]["height"],
                        "体积(m³)": column["quantities"]["volume"]
                    }
                    for column in quantities["columns"]
                ])
                columns_df.to_excel(writer, sheet_name="柱子工程量", index=False)
            
            # 导出梁工程量
            if quantities["beams"]:
                beams_df = pd.DataFrame([
                    {
                        "ID": beam["id"],
                        "类型": beam["type"],
                        "材料": beam["material"],
                        "长度(m)": beam["quantities"]["length"],
                        "截面面积(m²)": beam["quantities"]["area"],
                        "体积(m³)": beam["quantities"]["volume"]
                    }
                    for beam in quantities["beams"]
                ])
                beams_df.to_excel(writer, sheet_name="梁工程量", index=False)
            
            # 导出板工程量
            if quantities["slabs"]:
                slabs_df = pd.DataFrame([
                    {
                        "ID": slab["id"],
                        "类型": slab["type"],
                        "材料": slab["material"],
                        "面积(m²)": slab["quantities"]["area"],
                        "厚度(m)": slab["quantities"]["thickness"],
                        "体积(m³)": slab["quantities"]["volume"]
                    }
                    for slab in quantities["slabs"]
                ])
                slabs_df.to_excel(writer, sheet_name="板工程量", index=False)
            
            # 导出基础工程量
            if quantities["foundations"]:
                foundations_df = pd.DataFrame([
                    {
                        "ID": foundation["id"],
                        "类型": foundation["type"],
                        "材料": foundation["material"],
                        "底面积(m²)": foundation["quantities"]["area"],
                        "高度(m)": foundation["quantities"]["height"],
                        "体积(m³)": foundation["quantities"]["volume"]
                    }
                    for foundation in quantities["foundations"]
                ])
                foundations_df.to_excel(writer, sheet_name="基础工程量", index=False)
            
            # 导出总工程量
            total_df = pd.DataFrame([
                {
                    "构件类型": "墙体",
                    "体积(m³)": quantities["total"]["wall_volume"]
                },
                {
                    "构件类型": "柱子",
                    "体积(m³)": quantities["total"]["column_volume"]
                },
                {
                    "构件类型": "梁",
                    "体积(m³)": quantities["total"]["beam_volume"]
                },
                {
                    "构件类型": "板",
                    "体积(m³)": quantities["total"]["slab_volume"]
                },
                {
                    "构件类型": "基础",
                    "体积(m³)": quantities["total"]["foundation_volume"]
                },
                {
                    "构件类型": "总计",
                    "体积(m³)": quantities["total"]["total_volume"]
                }
            ])
            total_df.to_excel(writer, sheet_name="总工程量", index=False)
        
        return output_path 