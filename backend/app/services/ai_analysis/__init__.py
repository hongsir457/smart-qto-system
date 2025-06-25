#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析模块 - 智能分析服务的模块化实现

本模块将原本的大型ai_analyzer.py文件重构为多个专门的子模块：

- MockDataDetector: 模拟数据检测器
- PromptBuilder: 提示词构建器  
- VisionAnalyzer: 视觉分析器
- ResponseProcessor: 响应处理器
- ContextManager: 上下文管理器
- AIAnalyzerCore: 核心协调器

使用示例:
    from app.services.ai_analysis import AIAnalyzerCore
    
    analyzer = AIAnalyzerCore(openai_client, storage_service, interaction_logger)
    result = analyzer.generate_qto_from_data(data)
"""

from .mock_data_detector import MockDataDetector
from .prompt_builder import PromptBuilder
from .vision_analyzer import VisionAnalyzer
from .response_processor import ResponseProcessor
from .context_manager import ContextManager
from .ai_analyzer_core import AIAnalyzerCore

__all__ = [
    'MockDataDetector',
    'PromptBuilder', 
    'VisionAnalyzer',
    'ResponseProcessor',
    'ContextManager',
    'AIAnalyzerCore'
]

__version__ = "1.0.0"
__author__ = "Smart QTO System"
__description__ = "模块化AI分析服务" 