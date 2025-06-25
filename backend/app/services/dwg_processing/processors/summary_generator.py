#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汇总生成器
专门负责工程量汇总报告生成
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SummaryGenerator:
    """汇总生成器类"""
    
    def __init__(self):
        """初始化汇总生成器"""
        self.report_version = "2.0.0"
    
    def generate_component_summary(self, grouped_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        生成构件汇总
        
        Args:
            grouped_results: 按类型分组的构件结果
            
        Returns:
            构件汇总
        """
        try:
            summary = {
                'total_types': len(grouped_results),
                'total_components': 0,
                'total_value': 0.0,
                'by_type': {}
            }
            
            for component_type, components in grouped_results.items():
                type_summary = {
                    'count': len(components),
                    'total_quantity': 0,
                    'total_value': 0.0,
                    'unit': components[0].get('unit', '个') if components else '个',
                    'components': []
                }
                
                for comp in components:
                    if 'error' not in comp:
                        type_summary['total_quantity'] += comp.get('quantity', 0)
                        type_summary['total_value'] += comp.get('value', 0)
                        type_summary['components'].append({
                            'code': comp.get('component_code', ''),
                            'quantity': comp.get('quantity', 0),
                            'value': comp.get('value', 0)
                        })
                
                summary['by_type'][component_type] = type_summary
                summary['total_components'] += type_summary['count']
                summary['total_value'] += type_summary['total_value']
            
            return summary
            
        except Exception as e:
            logger.error(f"构件汇总生成失败: {e}")
            return {'error': str(e)}
    
    def generate_drawing_summary(self, drawings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成图纸汇总
        
        Args:
            drawings: 图纸列表
            
        Returns:
            图纸汇总
        """
        try:
            return {
                'total_drawings': len(drawings),
                'processed_drawings': len([d for d in drawings if d.get('success', False)]),
                'failed_drawings': len([d for d in drawings if not d.get('success', False)]),
                'drawing_list': [
                    {
                        'index': d.get('index', 0),
                        'drawing_number': d.get('drawing_number', ''),
                        'title': d.get('title', ''),
                        'component_count': len(d.get('components', [])),
                        'status': 'success' if d.get('success', False) else 'failed'
                    }
                    for d in drawings
                ]
            }
            
        except Exception as e:
            logger.error(f"图纸汇总生成失败: {e}")
            return {'error': str(e)}
    
    def generate_final_report(self, 
                            file_path: str,
                            drawings: List[Dict[str, Any]], 
                            component_summary: Dict[str, Any],
                            processing_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        生成最终报告
        
        Args:
            file_path: 文件路径
            drawings: 图纸列表
            component_summary: 构件汇总
            processing_info: 处理信息
            
        Returns:
            最终报告
        """
        try:
            drawing_summary = self.generate_drawing_summary(drawings)
            
            report = {
                'success': True,
                'file_path': file_path,
                'generated_time': datetime.now().isoformat(),
                'version': self.report_version,
                
                # 图纸信息
                'drawings': drawing_summary,
                
                # 构件信息  
                'components': component_summary,
                
                # 处理信息
                'processing': processing_info or {
                    'method': 'modular_processing',
                    'modules_used': ['component_calculator', 'summary_generator']
                },
                
                # 质量指标
                'quality_metrics': {
                    'success_rate': (drawing_summary.get('processed_drawings', 0) / 
                                   max(drawing_summary.get('total_drawings', 1), 1)),
                    'total_components_found': component_summary.get('total_components', 0),
                    'component_types_found': component_summary.get('total_types', 0)
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"最终报告生成失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def export_to_excel_data(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        导出为Excel数据格式
        
        Args:
            report: 报告数据
            
        Returns:
            Excel格式数据
        """
        try:
            excel_data = {
                'sheets': {
                    '汇总信息': [
                        ['项目', '值'],
                        ['文件路径', report.get('file_path', '')],
                        ['生成时间', report.get('generated_time', '')],
                        ['图纸总数', report.get('drawings', {}).get('total_drawings', 0)],
                        ['构件总数', report.get('components', {}).get('total_components', 0)],
                        ['构件类型数', report.get('components', {}).get('total_types', 0)]
                    ],
                    
                    '构件明细': [
                        ['构件类型', '构件编号', '数量', '计算值', '单位']
                    ],
                    
                    '图纸清单': [
                        ['序号', '图号', '图名', '构件数量', '状态']
                    ]
                }
            }
            
            # 添加构件明细
            components = report.get('components', {}).get('by_type', {})
            for comp_type, type_data in components.items():
                for comp in type_data.get('components', []):
                    excel_data['sheets']['构件明细'].append([
                        comp_type,
                        comp.get('code', ''),
                        comp.get('quantity', 0),
                        comp.get('value', 0),
                        type_data.get('unit', '个')
                    ])
            
            # 添加图纸清单
            drawings = report.get('drawings', {}).get('drawing_list', [])
            for drawing in drawings:
                excel_data['sheets']['图纸清单'].append([
                    drawing.get('index', 0),
                    drawing.get('drawing_number', ''),
                    drawing.get('title', ''),
                    drawing.get('component_count', 0),
                    drawing.get('status', '')
                ])
            
            return excel_data
            
        except Exception as e:
            logger.error(f"Excel数据导出失败: {e}")
            return {'error': str(e)} 