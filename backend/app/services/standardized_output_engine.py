"""标准化输出引擎 - Step 6 优化"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class QuantityRule:
    """工程量计算规则"""
    component_type: str
    calculation_method: str
    unit: str
    formula: str
    parameters: Dict[str, Any]
    standard_reference: str

@dataclass
class ComponentQuantity:
    """构件工程量"""
    component_id: str
    component_type: str
    label: str
    dimensions: Dict[str, float]
    quantity: float
    unit: str
    calculation_details: Dict[str, Any]
    standard_compliance: bool
    notes: List[str]

@dataclass
class QuantityList:
    """工程量清单"""
    project_info: Dict[str, str]
    drawing_info: Dict[str, str]
    component_quantities: List[ComponentQuantity]
    summary_by_type: Dict[str, Dict[str, Any]]
    total_summary: Dict[str, Any]
    compliance_report: Dict[str, Any]
    generation_metadata: Dict[str, Any]

class QuantityCalculationRules:
    """工程量计算规则引擎"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> Dict[str, QuantityRule]:
        """初始化计算规则"""
        return {
            "column": QuantityRule(
                component_type="column",
                calculation_method="volume",
                unit="m³",
                formula="length * width * height",
                parameters={"density_factor": 1.0},
                standard_reference="GB50854-2013"
            ),
            "beam": QuantityRule(
                component_type="beam",
                calculation_method="volume",
                unit="m³",
                formula="length * width * height",
                parameters={"density_factor": 1.0},
                standard_reference="GB50854-2013"
            ),
            "slab": QuantityRule(
                component_type="slab",
                calculation_method="area",
                unit="m²",
                formula="length * width",
                parameters={"thickness_default": 0.12},
                standard_reference="GB50854-2013"
            ),
            "wall": QuantityRule(
                component_type="wall",
                calculation_method="area",
                unit="m²",
                formula="length * height",
                parameters={"thickness_default": 0.2},
                standard_reference="GB50854-2013"
            ),
            "foundation": QuantityRule(
                component_type="foundation",
                calculation_method="volume",
                unit="m³",
                formula="length * width * depth",
                parameters={"depth_default": 1.5},
                standard_reference="GB50854-2013"
            ),
            "stair": QuantityRule(
                component_type="stair",
                calculation_method="area",
                unit="m²",
                formula="projected_area * step_factor",
                parameters={"step_factor": 1.3},
                standard_reference="GB50854-2013"
            )
        }
    
    def get_rule(self, component_type: str) -> Optional[QuantityRule]:
        """获取计算规则"""
        return self.rules.get(component_type.lower())
    
    def calculate_quantity(self, component: Dict[str, Any]) -> ComponentQuantity:
        """计算构件工程量"""
        try:
            component_type = component.get("type", "unknown").lower()
            rule = self.get_rule(component_type)
            
            if not rule:
                logger.warning(f"⚠️ 未找到构件类型 {component_type} 的计算规则")
                return self._create_default_quantity(component)
            
            # 提取尺寸信息
            dimensions = component.get("dimensions", {})
            
            # 执行计算
            quantity, calculation_details = self._execute_calculation(rule, dimensions)
            
            # 检查标准合规性
            compliance = self._check_compliance(rule, dimensions, quantity)
            
            # 生成注释
            notes = self._generate_notes(rule, dimensions, quantity, compliance)
            
            return ComponentQuantity(
                component_id=component.get("component_id", "unknown"),
                component_type=component_type,
                label=component.get("label", ""),
                dimensions=dimensions,
                quantity=quantity,
                unit=rule.unit,
                calculation_details=calculation_details,
                standard_compliance=compliance,
                notes=notes
            )
            
        except Exception as e:
            logger.error(f"❌ 工程量计算失败: {e}")
            return self._create_default_quantity(component)
    
    def _execute_calculation(self, rule: QuantityRule, dimensions: Dict[str, float]) -> tuple[float, Dict[str, Any]]:
        """执行计算"""
        try:
            if rule.calculation_method == "volume":
                return self._calculate_volume(rule, dimensions)
            elif rule.calculation_method == "area":
                return self._calculate_area(rule, dimensions)
            else:
                logger.warning(f"⚠️ 未知计算方法: {rule.calculation_method}")
                return 0.0, {"error": "未知计算方法"}
                
        except Exception as e:
            logger.error(f"❌ 计算执行失败: {e}")
            return 0.0, {"error": str(e)}
    
    def _calculate_volume(self, rule: QuantityRule, dimensions: Dict[str, float]) -> tuple[float, Dict[str, Any]]:
        """计算体积"""
        length = dimensions.get("length", dimensions.get("width", 0))
        width = dimensions.get("width", dimensions.get("height", 0))
        height = dimensions.get("height", dimensions.get("depth", 0))
        
        # 处理缺失尺寸
        if length == 0:
            length = rule.parameters.get("length_default", 1.0)
        if width == 0:
            width = rule.parameters.get("width_default", 0.3)
        if height == 0:
            height = rule.parameters.get("height_default", 3.0)
        
        volume = length * width * height
        density_factor = rule.parameters.get("density_factor", 1.0)
        final_volume = volume * density_factor
        
        calculation_details = {
            "method": "volume",
            "formula": rule.formula,
            "input_dimensions": {"length": length, "width": width, "height": height},
            "base_volume": volume,
            "density_factor": density_factor,
            "final_volume": final_volume
        }
        
        return final_volume, calculation_details
    
    def _calculate_area(self, rule: QuantityRule, dimensions: Dict[str, float]) -> tuple[float, Dict[str, Any]]:
        """计算面积"""
        length = dimensions.get("length", dimensions.get("width", 0))
        width = dimensions.get("width", dimensions.get("height", 0))
        
        # 处理缺失尺寸
        if length == 0:
            length = rule.parameters.get("length_default", 1.0)
        if width == 0:
            width = rule.parameters.get("width_default", 1.0)
        
        area = length * width
        
        # 特殊处理楼梯
        if rule.component_type == "stair":
            step_factor = rule.parameters.get("step_factor", 1.3)
            area = area * step_factor
        
        calculation_details = {
            "method": "area",
            "formula": rule.formula,
            "input_dimensions": {"length": length, "width": width},
            "base_area": length * width,
            "final_area": area
        }
        
        return area, calculation_details
    
    def _check_compliance(self, rule: QuantityRule, dimensions: Dict[str, float], quantity: float) -> bool:
        """检查标准合规性"""
        # 简化的合规性检查
        if quantity <= 0:
            return False
        
        # 检查尺寸合理性
        for dim_name, dim_value in dimensions.items():
            if dim_value < 0:
                return False
            
            # 基本尺寸范围检查
            if dim_name in ["length", "width"] and dim_value > 50:  # 超过50米
                return False
            if dim_name == "height" and dim_value > 20:  # 超过20米
                return False
        
        return True
    
    def _generate_notes(self, rule: QuantityRule, dimensions: Dict[str, float], 
                       quantity: float, compliance: bool) -> List[str]:
        """生成注释"""
        notes = []
        
        if not compliance:
            notes.append("⚠️ 该构件可能不符合标准规范，请人工复核")
        
        # 检查是否使用了默认值
        if any(v == 0 for v in dimensions.values()):
            notes.append("📝 部分尺寸使用了默认值，建议核实")
        
        # 添加计算标准引用
        notes.append(f"📋 计算依据: {rule.standard_reference}")
        
        return notes
    
    def _create_default_quantity(self, component: Dict[str, Any]) -> ComponentQuantity:
        """创建默认工程量"""
        return ComponentQuantity(
            component_id=component.get("component_id", "unknown"),
            component_type=component.get("type", "unknown"),
            label=component.get("label", ""),
            dimensions=component.get("dimensions", {}),
            quantity=0.0,
            unit="个",
            calculation_details={"error": "无法计算"},
            standard_compliance=False,
            notes=["❌ 计算失败，请人工处理"]
        )

class OutputFormatManager:
    """输出格式管理器"""
    
    def __init__(self):
        self.supported_formats = ["json", "excel", "csv", "pdf"]
    
    def export_quantity_list(self, quantity_list: QuantityList, 
                           output_format: str, output_path: str) -> Dict[str, Any]:
        """导出工程量清单"""
        try:
            logger.info(f"📤 开始导出工程量清单: 格式 {output_format}")
            
            if output_format not in self.supported_formats:
                raise ValueError(f"不支持的输出格式: {output_format}")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if output_format == "json":
                return self._export_json(quantity_list, output_path)
            elif output_format == "excel":
                return self._export_excel(quantity_list, output_path)
            elif output_format == "csv":
                return self._export_csv(quantity_list, output_path)
            elif output_format == "pdf":
                return self._export_pdf(quantity_list, output_path)
            
        except Exception as e:
            logger.error(f"❌ 导出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _export_json(self, quantity_list: QuantityList, output_path: str) -> Dict[str, Any]:
        """导出JSON格式"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(quantity_list), f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "format": "json",
                "file_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"❌ JSON导出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _export_excel(self, quantity_list: QuantityList, output_path: str) -> Dict[str, Any]:
        """导出Excel格式"""
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 工程量明细表
                detail_data = []
                for comp in quantity_list.component_quantities:
                    detail_data.append({
                        "构件编号": comp.component_id,
                        "构件类型": comp.component_type,
                        "构件标签": comp.label,
                        "长度(m)": comp.dimensions.get("length", 0),
                        "宽度(m)": comp.dimensions.get("width", 0),
                        "高度(m)": comp.dimensions.get("height", 0),
                        "工程量": comp.quantity,
                        "单位": comp.unit,
                        "标准合规": "是" if comp.standard_compliance else "否",
                        "备注": "; ".join(comp.notes)
                    })
                
                detail_df = pd.DataFrame(detail_data)
                detail_df.to_excel(writer, sheet_name="工程量明细", index=False)
                
                # 汇总表
                summary_data = []
                for comp_type, summary in quantity_list.summary_by_type.items():
                    summary_data.append({
                        "构件类型": comp_type,
                        "数量": summary.get("count", 0),
                        "总工程量": summary.get("total_quantity", 0),
                        "单位": summary.get("unit", ""),
                        "平均工程量": summary.get("avg_quantity", 0)
                    })
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name="工程量汇总", index=False)
            
            return {
                "success": True,
                "format": "excel",
                "file_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"❌ Excel导出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _export_csv(self, quantity_list: QuantityList, output_path: str) -> Dict[str, Any]:
        """导出CSV格式"""
        try:
            data = []
            for comp in quantity_list.component_quantities:
                data.append({
                    "component_id": comp.component_id,
                    "component_type": comp.component_type,
                    "label": comp.label,
                    "quantity": comp.quantity,
                    "unit": comp.unit,
                    "compliance": comp.standard_compliance
                })
            
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            return {
                "success": True,
                "format": "csv",
                "file_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"❌ CSV导出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _export_pdf(self, quantity_list: QuantityList, output_path: str) -> Dict[str, Any]:
        """导出PDF格式"""
        try:
            # 简化实现：生成HTML然后转PDF（需要安装额外库）
            html_content = self._generate_html_report(quantity_list)
            
            # 这里应该使用PDF生成库，简化为文本文件
            text_path = output_path.replace('.pdf', '.txt')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write("工程量清单报告\n")
                f.write("=" * 50 + "\n\n")
                
                for comp in quantity_list.component_quantities:
                    f.write(f"构件: {comp.label}\n")
                    f.write(f"类型: {comp.component_type}\n")
                    f.write(f"工程量: {comp.quantity} {comp.unit}\n")
                    f.write("-" * 30 + "\n")
            
            return {
                "success": True,
                "format": "pdf",
                "file_path": text_path,
                "file_size": os.path.getsize(text_path),
                "note": "PDF功能暂未完全实现，已生成文本格式"
            }
            
        except Exception as e:
            logger.error(f"❌ PDF导出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_html_report(self, quantity_list: QuantityList) -> str:
        """生成HTML报告"""
        html = """
        <html>
        <head><title>工程量清单</title></head>
        <body>
        <h1>工程量清单</h1>
        <table border="1">
        <tr><th>构件编号</th><th>类型</th><th>工程量</th><th>单位</th></tr>
        """
        
        for comp in quantity_list.component_quantities:
            html += f"<tr><td>{comp.component_id}</td><td>{comp.component_type}</td><td>{comp.quantity}</td><td>{comp.unit}</td></tr>"
        
        html += "</table></body></html>"
        return html

class StandardizedOutputEngine:
    """标准化输出引擎"""
    
    def __init__(self):
        self.calculation_rules = QuantityCalculationRules()
        self.format_manager = OutputFormatManager()
    
    async def generate_quantity_list(self, fused_components: List[Dict], 
                                   project_info: Dict, task_id: str) -> Dict[str, Any]:
        """生成工程量清单"""
        try:
            logger.info(f"🔄 开始生成工程量清单: {len(fused_components)} 个构件")
            start_time = time.time()
            
            # 1. 计算各构件工程量
            component_quantities = []
            for component in fused_components:
                quantity = self.calculation_rules.calculate_quantity(component)
                component_quantities.append(quantity)
            
            logger.info(f"📊 工程量计算完成: {len(component_quantities)} 个构件")
            
            # 2. 生成汇总统计
            summary_by_type = self._generate_summary_by_type(component_quantities)
            total_summary = self._generate_total_summary(component_quantities, summary_by_type)
            
            # 3. 生成合规性报告
            compliance_report = self._generate_compliance_report(component_quantities)
            
            # 4. 创建工程量清单
            quantity_list = QuantityList(
                project_info=project_info,
                drawing_info={
                    "task_id": task_id,
                    "generation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_components": len(component_quantities)
                },
                component_quantities=component_quantities,
                summary_by_type=summary_by_type,
                total_summary=total_summary,
                compliance_report=compliance_report,
                generation_metadata={
                    "processing_time": time.time() - start_time,
                    "calculation_engine": "StandardizedOutputEngine",
                    "version": "1.0"
                }
            )
            
            logger.info(f"✅ 工程量清单生成完成: 用时 {time.time() - start_time:.2f}s")
            
            return {
                "success": True,
                "quantity_list": asdict(quantity_list)
            }
            
        except Exception as e:
            logger.error(f"❌ 工程量清单生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "quantity_list": None
            }
    
    def _generate_summary_by_type(self, quantities: List[ComponentQuantity]) -> Dict[str, Dict[str, Any]]:
        """按类型生成汇总"""
        summary = {}
        
        for quantity in quantities:
            comp_type = quantity.component_type
            
            if comp_type not in summary:
                summary[comp_type] = {
                    "count": 0,
                    "total_quantity": 0.0,
                    "unit": quantity.unit,
                    "avg_quantity": 0.0,
                    "compliant_count": 0
                }
            
            summary[comp_type]["count"] += 1
            summary[comp_type]["total_quantity"] += quantity.quantity
            
            if quantity.standard_compliance:
                summary[comp_type]["compliant_count"] += 1
        
        # 计算平均值
        for comp_type, data in summary.items():
            if data["count"] > 0:
                data["avg_quantity"] = data["total_quantity"] / data["count"]
                data["compliance_rate"] = data["compliant_count"] / data["count"]
        
        return summary
    
    def _generate_total_summary(self, quantities: List[ComponentQuantity], 
                              summary_by_type: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """生成总汇总"""
        total_components = len(quantities)
        compliant_components = len([q for q in quantities if q.standard_compliance])
        
        return {
            "total_components": total_components,
            "compliant_components": compliant_components,
            "compliance_rate": compliant_components / total_components if total_components > 0 else 0.0,
            "component_types": len(summary_by_type),
            "total_quantity_by_unit": self._calculate_total_by_unit(quantities)
        }
    
    def _calculate_total_by_unit(self, quantities: List[ComponentQuantity]) -> Dict[str, float]:
        """按单位计算总量"""
        totals = {}
        
        for quantity in quantities:
            unit = quantity.unit
            if unit not in totals:
                totals[unit] = 0.0
            totals[unit] += quantity.quantity
        
        return totals
    
    def _generate_compliance_report(self, quantities: List[ComponentQuantity]) -> Dict[str, Any]:
        """生成合规性报告"""
        non_compliant = [q for q in quantities if not q.standard_compliance]
        
        issues_by_type = {}
        for quantity in non_compliant:
            comp_type = quantity.component_type
            if comp_type not in issues_by_type:
                issues_by_type[comp_type] = []
            
            issues_by_type[comp_type].append({
                "component_id": quantity.component_id,
                "issues": quantity.notes
            })
        
        return {
            "total_issues": len(non_compliant),
            "issues_by_type": issues_by_type,
            "recommendations": [
                "建议对不合规构件进行人工复核",
                "检查尺寸信息的准确性",
                "确认计算参数的合理性"
            ]
        }
    
    async def export_multiple_formats(self, quantity_list: QuantityList, 
                                    output_dir: str, base_filename: str) -> Dict[str, Any]:
        """多格式导出"""
        try:
            logger.info(f"📤 开始多格式导出: {base_filename}")
            
            export_results = {}
            
            for format_type in self.format_manager.supported_formats:
                output_path = os.path.join(output_dir, f"{base_filename}.{format_type}")
                
                result = self.format_manager.export_quantity_list(
                    quantity_list, format_type, output_path
                )
                
                export_results[format_type] = result
            
            logger.info(f"✅ 多格式导出完成")
            
            return {
                "success": True,
                "export_results": export_results
            }
            
        except Exception as e:
            logger.error(f"❌ 多格式导出失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "export_results": {}
            } 