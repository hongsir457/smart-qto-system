#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWG处理模块 - 精细化版本
每个组件单一职责，文件小于200行，优雅架构
"""

# 导入精细化的主控制器
try:
    from .core.dwg_processor import DWGProcessor
except ImportError:
    # 如果导入失败，提供基础实现
    class DWGProcessor:
        def process_multi_sheets(self, file_path):
            return {"error": "精细化DWG处理器不可用"}

# 对外暴露的主要接口
__all__ = ['DWGProcessor']

# 版本信息
__version__ = '2.0.0-精细化'
__author__ = 'Smart QTO System'
__description__ = '精细化模块设计，单一职责原则，优雅架构'
