"""
增强版Vision扫描服务
集成精确位置匹配、空间重叠判定、OCR文本联动等功能
"""

import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# 导入增强合并器
from app.services.result_mergers.vision_result_merger_enhanced import (
    EnhancedVisionResultMerger, OCRResultMerger, TextRegion, ComponentMatch
)

# 导入原有组件
from app.services.vision_scanner import VisionScannerService

logger = logging.getLogger(__name__)

@dataclass
class VisionAnalysisMetrics:
    """Vision分析指标"""
    total_slices: int
    successful_slices: int
    components_found: int
    texts_associated: int
    merge_operations: int
    processing_time: float
    enhancement_features_used: List[str]

class EnhancedVisionScannerService(VisionScannerService):
    """增强版Vision扫描服务"""
    
    def __init__(self):
        super().__init__()
        self.enhanced_merger = EnhancedVisionResultMerger()
        self.ocr_merger = OCRResultMerger()
        self.analysis_metrics = None
    
    def scan_images_with_enhanced_merging(self, 
                                        image_paths: List[str],
                                        shared_slice_results: Dict[str, Any], 
                                        drawing_id: int,
                                        task_id: str = None,
                                        ocr_result: Dict[str, Any] = None,
                                        enable_features: List[str] = None) -> Dict[str, Any]:
        """
        使用增强合并的图像扫描
        
        Args:
            image_paths: 图像路径列表
            shared_slice_results: 共享切片结果
            drawing_id: 图纸ID
            task_id: 任务ID
            ocr_result: OCR结果
            enable_features: 启用的增强功能列表
                - "precise_position_matching": 精确位置匹配
                - "spatial_overlap_detection": 空间重叠检测
                - "text_component_association": 文本构件关联
                - "type_similarity_merging": 类型相似性合并
        
        Returns:
            增强分析结果
        """
        start_time = time.time()
        
        if enable_features is None:
            enable_features = [
                "precise_position_matching",
                "spatial_overlap_detection", 
                "text_component_association",
                "type_similarity_merging"
            ]
        
        logger.info(f"🚀 启动增强Vision扫描: {len(image_paths)} 张图片")
        logger.info(f"📋 启用功能: {', '.join(enable_features)}")
        
        try:
            # 步骤1: 执行基础Vision分析
            basic_result = self.scan_images_with_shared_slices(
                image_paths, shared_slice_results, drawing_id, task_id, ocr_result
            )
            
            if not basic_result.get('success', False):
                return basic_result
            
            # 步骤2: 提取Vision结果和坐标映射
            vision_results = self._extract_vision_results_from_basic(basic_result)
            slice_coordinate_map = shared_slice_results.get('slice_coordinate_map', {})
            original_image_info = shared_slice_results.get('original_image_info', {})
            
            # 步骤3: 提取OCR结果（如果可用）
            ocr_results_list = self._extract_ocr_results_from_shared(shared_slice_results, ocr_result)
            
            # 步骤4: 执行增强合并
            if "precise_position_matching" in enable_features:
                enhanced_result = self.enhanced_merger.merge_vision_results_enhanced(
                    vision_results=vision_results,
                    slice_coordinate_map=slice_coordinate_map,
                    original_image_info=original_image_info,
                    ocr_results=ocr_results_list,
                    task_id=task_id or ""
                )
            else:
                # 回退到基础合并
                enhanced_result = basic_result
            
            # 步骤5: 生成分析指标
            self.analysis_metrics = self._generate_analysis_metrics(
                vision_results, enhanced_result, enable_features, start_time
            )
            
            # 步骤6: 增强结果后处理
            final_result = self._post_process_enhanced_result(enhanced_result, basic_result)
            
            logger.info(f"✅ 增强Vision扫描完成: 用时 {time.time() - start_time:.2f}s")
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 增强Vision扫描失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Enhanced vision scanning failed: {str(e)}',
                'fallback_to_basic': True
            }
    
    def _extract_vision_results_from_basic(self, basic_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从基础结果中提取Vision分析结果"""
        vision_results = []
        
        # 从batch_results中提取
        batch_results = basic_result.get('batch_results', [])
        for batch in batch_results:
            if batch.get('success', False):
                vision_results.append(batch)
        
        # 如果没有batch_results，尝试从主结果提取
        if not vision_results and basic_result.get('qto_data'):
            vision_results = [basic_result]
        
        return vision_results
    
    def _extract_ocr_results_from_shared(self, shared_slice_results: Dict, 
                                       ocr_result: Dict = None) -> List[Dict]:
        """从共享结果中提取OCR数据"""
        ocr_results_list = []
        
        # 方法1: 从shared_slice_results中提取
        slice_data = shared_slice_results.get('slice_data', [])
        for slice_info in slice_data:
            if 'ocr_results' in slice_info:
                ocr_item = {
                    'slice_id': slice_info.get('slice_id', ''),
                    'text_regions': slice_info.get('ocr_results', []),
                    'success': True,
                    'offset_x': slice_info.get('offset_x', 0),
                    'offset_y': slice_info.get('offset_y', 0)
                }
                ocr_results_list.append(ocr_item)
        
        # 方法2: 从单独的ocr_result参数提取
        if ocr_result and ocr_result.get('success'):
            ocr_data = ocr_result.get('text_regions', [])
            if ocr_data:
                # 将全局OCR结果转换为切片格式
                ocr_item = {
                    'slice_id': 'global_ocr',
                    'text_regions': ocr_data,
                    'success': True,
                    'offset_x': 0,
                    'offset_y': 0
                }
                ocr_results_list.append(ocr_item)
        
        return ocr_results_list
    
    def _generate_analysis_metrics(self, vision_results: List[Dict], 
                                 enhanced_result: Dict, enable_features: List[str],
                                 start_time: float) -> VisionAnalysisMetrics:
        """生成分析指标"""
        enhanced_data = enhanced_result.get('enhanced_result', {})
        components = enhanced_data.get('components', [])
        
        # 统计文本关联
        texts_associated = sum(1 for comp in components if comp.get('text_tags'))
        
        # 统计合并操作
        merge_operations = sum(1 for comp in components if comp.get('merge_metadata'))
        
        return VisionAnalysisMetrics(
            total_slices=len(vision_results),
            successful_slices=len([r for r in vision_results if r.get('success', False)]),
            components_found=len(components),
            texts_associated=texts_associated,
            merge_operations=merge_operations,
            processing_time=time.time() - start_time,
            enhancement_features_used=enable_features
        )
    
    def _post_process_enhanced_result(self, enhanced_result: Dict, 
                                    basic_result: Dict) -> Dict[str, Any]:
        """增强结果后处理"""
        if not enhanced_result.get('success', False):
            return enhanced_result
        
        # 保持与原有接口的兼容性
        final_result = {
            'success': True,
            'enhanced': True,
            'qto_data': {
                'components': enhanced_result.get('enhanced_result', {}).get('components', []),
                'drawing_info': basic_result.get('qto_data', {}).get('drawing_info', {}),
                'quantity_summary': self._calculate_enhanced_quantity_summary(
                    enhanced_result.get('enhanced_result', {}).get('components', [])
                ),
                'analysis_metadata': {
                    **basic_result.get('qto_data', {}).get('analysis_metadata', {}),
                    'enhancement_applied': True,
                    'enhancement_metrics': self.analysis_metrics.__dict__ if self.analysis_metrics else {}
                }
            },
            'enhanced_result': enhanced_result.get('enhanced_result', {}),
            'analysis_metrics': self.analysis_metrics.__dict__ if self.analysis_metrics else {}
        }
        
        return final_result
    
    def _calculate_enhanced_quantity_summary(self, components: List[Dict]) -> Dict[str, Any]:
        """计算增强版工程量汇总"""
        if not components:
            return {"总计": {}}
        
        # 按类型统计
        type_summary = {}
        total_quantity = 0
        
        for comp in components:
            comp_type = comp.get('component_type', '未知')
            quantity = comp.get('quantity', 0)
            
            if comp_type not in type_summary:
                type_summary[comp_type] = {
                    'count': 0,
                    'total_quantity': 0,
                    'components': []
                }
            
            type_summary[comp_type]['count'] += 1
            type_summary[comp_type]['total_quantity'] += quantity
            type_summary[comp_type]['components'].append(comp.get('component_id', ''))
            
            total_quantity += quantity
        
        # 生成汇总
        summary = {
            "总计": {
                "构件类型数": len(type_summary),
                "构件总数": len(components),
                "总数量": total_quantity
            }
        }
        
        # 添加各类型详情
        for comp_type, data in type_summary.items():
            summary[comp_type] = {
                "数量": data['count'],
                "总计": data['total_quantity'],
                "构件列表": data['components'][:10]  # 限制显示前10个
            }
        
        return summary
    
    def get_analysis_metrics(self) -> Optional[VisionAnalysisMetrics]:
        """获取分析指标"""
        return self.analysis_metrics
    
    def test_ocr_merger_independently(self, ocr_results: List[Dict], 
                                    overlap_strategy: str = "hybrid") -> List[TextRegion]:
        """独立测试OCR合并器"""
        logger.info(f"🧪 独立测试OCR合并器: {len(ocr_results)} 个结果")
        
        return self.ocr_merger.merge_all(ocr_results, overlap_strategy)
    
    def test_position_matching(self, vision_results: List[Dict], 
                             slice_coordinate_map: Dict) -> List[ComponentMatch]:
        """独立测试位置匹配"""
        logger.info(f"🧪 独立测试位置匹配: {len(vision_results)} 个结果")
        
        return self.enhanced_merger._match_components_by_position(vision_results, slice_coordinate_map)
    
    def test_spatial_merging(self, component_matches: List[ComponentMatch]) -> List[Dict]:
        """独立测试空间合并"""
        logger.info(f"🧪 独立测试空间合并: {len(component_matches)} 个构件")
        
        return self.enhanced_merger._merge_by_spatial_and_type_similarity(component_matches)

class VisionAnalysisValidator:
    """Vision分析验证器"""
    
    @staticmethod
    def validate_component_structure(component: Dict) -> Dict[str, Any]:
        """验证构件数据结构"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        required_fields = ['component_id', 'component_type']
        for field in required_fields:
            if field not in component:
                validation_result['errors'].append(f"缺少必需字段: {field}")
                validation_result['valid'] = False
        
        # 检查位置信息
        if 'bbox' not in component and 'position' not in component:
            validation_result['warnings'].append("缺少位置信息")
        
        # 检查数量信息
        if 'quantity' in component:
            try:
                quantity = float(component['quantity'])
                if quantity <= 0:
                    validation_result['warnings'].append("数量应大于0")
            except (ValueError, TypeError):
                validation_result['errors'].append("数量格式无效")
                validation_result['valid'] = False
        
        return validation_result
    
    @staticmethod
    def validate_slice_coordinate_map(slice_map: Dict) -> Dict[str, Any]:
        """验证切片坐标映射"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not slice_map:
            validation_result['errors'].append("切片坐标映射为空")
            validation_result['valid'] = False
            return validation_result
        
        for slice_id, slice_info in slice_map.items():
            required_coords = ['offset_x', 'offset_y']
            for coord in required_coords:
                if coord not in slice_info:
                    validation_result['errors'].append(f"切片 {slice_id} 缺少坐标: {coord}")
                    validation_result['valid'] = False
        
        return validation_result
    
    @staticmethod
    def generate_validation_report(components: List[Dict], 
                                 slice_map: Dict) -> Dict[str, Any]:
        """生成验证报告"""
        report = {
            'timestamp': time.time(),
            'total_components': len(components),
            'slice_count': len(slice_map),
            'component_validations': [],
            'slice_map_validation': {},
            'summary': {}
        }
        
        # 验证每个构件
        valid_components = 0
        for i, component in enumerate(components):
            validation = VisionAnalysisValidator.validate_component_structure(component)
            validation['component_index'] = i
            validation['component_id'] = component.get('component_id', f'unknown_{i}')
            report['component_validations'].append(validation)
            
            if validation['valid']:
                valid_components += 1
        
        # 验证切片映射
        report['slice_map_validation'] = VisionAnalysisValidator.validate_slice_coordinate_map(slice_map)
        
        # 生成汇总
        report['summary'] = {
            'valid_components': valid_components,
            'invalid_components': len(components) - valid_components,
            'validation_rate': valid_components / len(components) if components else 0,
            'slice_map_valid': report['slice_map_validation']['valid']
        }
        
        return report 