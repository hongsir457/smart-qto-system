import json
import logging
from app.database import SafeDBSession
from app.models.drawing import Drawing
# from app.models.quantity_result import QuantityResult  # 暂时注释，该模型不存在
# from app.models.component import Component  # 暂时注释，该模型不存在
from sqlalchemy import desc

logger = logging.getLogger(__name__)

class CalculationDebugger:
    """计算模块调试工具"""
    
    def __init__(self):
        self.logger = logger
    
    def check_calculation_pipeline(self, drawing_id: int):
        """检查计算流水线的状态"""
        results = {
            'drawing_status': None,
            'recognition_results': None,
            'component_count': 0,
            'quantity_results': None,
            'calculation_errors': [],
            'recommendations': []
        }
        
        try:
            with SafeDBSession() as db:
                # 检查图纸状态
                drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
                if not drawing:
                    results['calculation_errors'].append(f"未找到图纸ID: {drawing_id}")
                    return results
                
                results['drawing_status'] = {
                    'id': drawing.id,
                    'filename': drawing.filename,
                    'status': drawing.status,
                    'error_message': drawing.error_message,
                    'has_recognition_results': bool(drawing.recognition_results),
                    'file_type': drawing.file_type,
                    'created_at': str(drawing.created_at)
                }
                
                # 检查识别结果
                if drawing.recognition_results:
                    try:
                        recognition_data = json.loads(drawing.recognition_results)
                        results['recognition_results'] = {
                            'has_data': True,
                            'keys': list(recognition_data.keys()),
                            'total_components': self._count_components_in_recognition(recognition_data)
                        }
                        
                        # 分析识别结果格式
                        if 'quantity_list' in recognition_data:
                            results['recognition_results']['format'] = 'chatgpt_format'
                            results['recognition_results']['chatgpt_components'] = len(recognition_data.get('quantity_list', []))
                        elif any(key in recognition_data for key in ['beams', 'columns', 'slabs', 'walls']):
                            results['recognition_results']['format'] = 'standard_format'
                        else:
                            results['recognition_results']['format'] = 'unknown_format'
                            results['calculation_errors'].append("识别结果格式不符合预期")
                            
                    except Exception as e:
                        results['calculation_errors'].append(f"解析识别结果失败: {str(e)}")
                        results['recognition_results'] = {'has_data': False, 'error': str(e)}
                else:
                    results['calculation_errors'].append("没有识别结果")
                
                # 检查构件表（暂时注释，Component模型不存在）
                # components = db.query(Component).filter(Component.drawing_id == drawing_id).all()
                # results['component_count'] = len(components)
                results['component_count'] = 0  # 临时设置
                
                # if components:
                #     component_summary = {}
                #     for comp in components:
                #         comp_type = comp.component_type
                #         if comp_type not in component_summary:
                #             component_summary[comp_type] = 0
                #         component_summary[comp_type] += 1
                #     results['component_summary'] = component_summary
                # else:
                #     results['calculation_errors'].append("构件表中没有数据")
                results['calculation_errors'].append("构件表功能暂未实现（Component模型不存在）")
                
                # 检查工程量计算结果（暂时注释，QuantityResult模型不存在）
                # quantity_results = db.query(QuantityResult).filter(
                #     QuantityResult.drawing_id == drawing_id
                # ).order_by(desc(QuantityResult.created_at)).all()
                
                # if quantity_results:
                #     results['quantity_results'] = {
                #         'count': len(quantity_results),
                #         'latest_result': {
                #             'id': quantity_results[0].id,
                #             'created_at': str(quantity_results[0].created_at),
                #             'has_data': bool(quantity_results[0].calculation_results)
                #         }
                #     }
                #     
                #     # 分析最新的计算结果
                #     if quantity_results[0].calculation_results:
                #         try:
                #             calc_data = json.loads(quantity_results[0].calculation_results)
                #             results['quantity_results']['result_keys'] = list(calc_data.keys())
                #             results['quantity_results']['total_calculated'] = self._count_calculated_items(calc_data)
                #         except Exception as e:
                #             results['calculation_errors'].append(f"解析计算结果失败: {str(e)}")
                # else:
                #     results['calculation_errors'].append("没有工程量计算结果")
                results['calculation_errors'].append("工程量计算功能暂未实现（QuantityResult模型不存在）")
                
                # 生成建议
                self._generate_recommendations(results)
                
        except Exception as e:
            results['calculation_errors'].append(f"调试过程出错: {str(e)}")
            logger.error(f"调试计算管道失败: {str(e)}", exc_info=True)
        
        return results
    
    def _count_components_in_recognition(self, recognition_data):
        """计算识别结果中的构件数量"""
        total = 0
        
        if 'quantity_list' in recognition_data:
            # ChatGPT格式
            total = len(recognition_data.get('quantity_list', []))
        else:
            # 标准格式
            for key in ['beams', 'columns', 'slabs', 'walls', 'foundations']:
                if key in recognition_data:
                    if isinstance(recognition_data[key], list):
                        total += len(recognition_data[key])
                    elif isinstance(recognition_data[key], dict):
                        total += len(recognition_data[key])
        
        return total
    
    def _count_calculated_items(self, calc_data):
        """计算计算结果中的项目数量"""
        total = 0
        
        for category in calc_data.values():
            if isinstance(category, dict) and 'items' in category:
                total += len(category['items'])
            elif isinstance(category, list):
                total += len(category)
        
        return total
    
    def _generate_recommendations(self, results):
        """生成调试建议"""
        recommendations = []
        
        if not results['recognition_results'] or not results['recognition_results'].get('has_data'):
            recommendations.append("需要重新进行构件识别")
        
        if results['component_count'] == 0:
            recommendations.append("构件表为空，检查识别结果到构件转换过程")
        
        if not results['quantity_results']:
            recommendations.append("没有工程量计算结果，检查计算模块是否正常运行")
        
        if results['calculation_errors']:
            recommendations.append("存在错误，需要修复后重新计算")
        
        if results['recognition_results'] and results['recognition_results'].get('format') == 'chatgpt_format':
            recommendations.append("检查ChatGPT结果适配器是否正常工作")
        
        results['recommendations'] = recommendations
    
    def get_latest_task_logs(self, drawing_id: int, limit: int = 50):
        """获取最新的任务日志"""
        try:
            with SafeDBSession() as db:
                drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
                if drawing and drawing.task_id:
                    # 这里可以添加从Celery或日志文件中获取任务日志的逻辑
                    return {
                        'task_id': drawing.task_id,
                        'status': drawing.status,
                        'message': "日志功能需要进一步实现"
                    }
                else:
                    return {'error': '没有找到任务ID'}
        except Exception as e:
            logger.error(f"获取任务日志失败: {str(e)}")
            return {'error': str(e)} 