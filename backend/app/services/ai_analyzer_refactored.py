#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Analyzer Service (重构版) - 作为新架构的代理接口
保持向后兼容性，将原有大文件重构为小组件
"""
import logging
from typing import Dict, Any, List, Optional

# 导入重构后的AI组件
from .ai import AIAnalyzer as NewAIAnalyzer

logger = logging.getLogger(__name__)

# 创建兼容性代理类
class AIAnalyzerService:
    """
    AI分析器服务（重构版）
    作为原有AIAnalyzerService的代理，调用重构后的组件
    """
    
    def __init__(self):
        """初始化AI分析器服务"""
        # 使用重构后的AI分析器
        self._new_analyzer = NewAIAnalyzer()
        
        # 保持原有属性的兼容性
        self.client = self._new_analyzer.core.client
        self.interaction_logger = self._new_analyzer.interaction_logger
        
        logger.info("✅ AI Analyzer Service (重构版) 初始化完成")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._new_analyzer.is_available()

    def generate_qto_from_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """根据OCR数据生成工程量清单"""
        return self._new_analyzer.generate_qto_from_data(extracted_data)

    def generate_qto_from_local_images(self, 
                                     image_paths: List[str], 
                                     task_id: str = None,
                                     drawing_id: int = None) -> Dict[str, Any]:
        """基于本地图像路径生成工程量清单"""
        context_data = {}
        if task_id:
            context_data['task_id'] = task_id
        if drawing_id:
            context_data['drawing_id'] = drawing_id
            
        return self._new_analyzer.generate_qto_from_local_images(image_paths, context_data)

    def generate_qto_from_encoded_images(self, 
                                       encoded_images: List[Dict],
                                       task_id: str = None,
                                       drawing_id: int = None,
                                       slice_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """基于编码图像数据生成工程量清单"""
        context_data = {}
        if task_id:
            context_data['task_id'] = task_id
        if drawing_id:
            context_data['drawing_id'] = drawing_id
        if slice_metadata:
            context_data['slice_metadata'] = slice_metadata
            
        return self._new_analyzer.generate_qto_from_encoded_images(encoded_images, context_data)

    async def analyze_text_async(self, 
                               prompt: str, 
                               session_id: str = None,
                               context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """异步文本分析"""
        return await self._new_analyzer.analyze_text_async(prompt, session_id, context_data)

    # 兼容性方法：直接代理到核心组件
    def _validate_response_authenticity(self, qto_data: Dict) -> List[str]:
        """验证响应真实性"""
        return self._new_analyzer._validate_response_authenticity(qto_data)

    def _check_for_mock_data_patterns(self, qto_data: Dict) -> bool:
        """检查模拟数据模式"""
        return self._new_analyzer._check_for_mock_data_patterns(qto_data)

    # 提示词构建方法（代理到prompt_builder）
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return self._new_analyzer.prompt_builder.build_system_prompt()

    def _build_enhanced_system_prompt(self) -> str:
        """构建增强系统提示词"""
        return self._new_analyzer.prompt_builder.build_enhanced_system_prompt()

    def _build_user_prompt(self, data: Dict[str, Any]) -> Optional[str]:
        """构建用户提示词"""
        return self._new_analyzer.prompt_builder.build_user_prompt(data)

    # 图像处理方法（代理到image_processor）
    def _prepare_images(self, image_paths: List[str]) -> List[Dict]:
        """准备图像数据"""
        return self._new_analyzer.image_processor._prepare_images(image_paths)

    # 废弃方法的处理
    def _execute_multi_turn_analysis(self, *args, **kwargs):
        """多轮分析方法已废弃"""
        logger.warning("⚠️ 多轮分析方法已废弃，请使用双轨协同分析")
        raise NotImplementedError("多轮分析方法已废弃，请使用双轨协同分析")

    def generate_qto_from_local_images_v2(self, *args, **kwargs):
        """V2方法已废弃"""
        logger.warning("⚠️ V2方法已废弃，请使用标准的generate_qto_from_local_images方法")
        # 重定向到标准方法
        return self.generate_qto_from_local_images(*args, **kwargs)

    def _execute_multi_turn_analysis_with_context(self, *args, **kwargs):
        """上下文多轮分析已废弃"""
        logger.warning("⚠️ 上下文多轮分析已废弃，请使用双轨协同分析")
        raise NotImplementedError("上下文多轮分析已废弃，请使用双轨协同分析")

    # 五步分析方法（已废弃）
    def _step1_extract_drawing_info(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _step2_extract_component_ids(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _step3_count_components(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _step4_extract_positions(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _step5_extract_attributes(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _execute_vision_step(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _execute_contextual_step_1(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _execute_contextual_step_2(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _execute_contextual_step_3(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _execute_contextual_step_4(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _execute_contextual_step_5(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    def _make_contextual_api_call(self, *args, **kwargs):
        raise NotImplementedError("五步分析方法已废弃")

    # 辅助方法
    def _synthesize_qto_data(self, analysis_results: Dict) -> Dict[str, Any]:
        """数据合成（已废弃，融入新架构）"""
        logger.warning("⚠️ _synthesize_qto_data方法已废弃，功能已融入新架构")
        return analysis_results

    def _determine_component_type(self, component_id: str) -> str:
        """构件类型判断"""
        # 简单的构件类型判断逻辑
        if component_id.startswith('KZ'):
            return '框架柱'
        elif component_id.startswith('L'):
            return '框架梁'
        elif component_id.startswith('B'):
            return '现浇板'
        elif component_id.startswith('Q'):
            return '剪力墙'
        else:
            return '其他构件'

    def _generate_quantity_summary(self, components: List[Dict]) -> Dict[str, Any]:
        """生成工程量汇总"""
        summary = {
            "concrete_total": 0,
            "reinforcement_total": 0,
            "formwork_total": 0,
            "component_count": len(components)
        }
        
        for comp in components:
            concrete = comp.get('concrete', {})
            if isinstance(concrete, dict):
                volume = concrete.get('volume', 0)
                if isinstance(volume, (int, float)):
                    summary["concrete_total"] += volume
            
            reinforcement = comp.get('reinforcement', {})
            if isinstance(reinforcement, dict):
                weight = reinforcement.get('total_weight', 0)
                if isinstance(weight, (int, float)):
                    summary["reinforcement_total"] += weight
            
            formwork_area = comp.get('formwork_area', 0)
            if isinstance(formwork_area, (int, float)):
                summary["formwork_total"] += formwork_area
        
        return summary


# 兼容性：创建别名
AIAnalyzer = AIAnalyzerService 