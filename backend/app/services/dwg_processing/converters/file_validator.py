#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件验证器
专门负责DWG/DXF文件的验证和检查
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class FileValidator:
    """文件验证器类"""
    
    def __init__(self):
        """初始化文件验证器"""
        self.supported_formats = ['.dwg', '.dxf']
        self.min_file_size = 100  # 最小文件大小（字节）
    
    def validate_input_file(self, file_path: str) -> Dict[str, Any]:
        """
        验证输入文件的有效性
        
        Args:
            file_path: 文件路径
            
        Returns:
            验证结果字典
        """
        try:
            file_path = Path(file_path)
            
            result = {
                'valid': False,
                'file_path': str(file_path),
                'file_size': 0,
                'format': '',
                'errors': []
            }
            
            # 检查文件是否存在
            if not file_path.exists():
                result['errors'].append(f"文件不存在: {file_path}")
                return result
            
            # 检查文件大小
            file_size = file_path.stat().st_size
            result['file_size'] = file_size
            
            if file_size < self.min_file_size:
                result['errors'].append(f"文件太小，可能已损坏: {file_size} bytes")
                return result
            
            # 检查文件格式
            file_ext = file_path.suffix.lower()
            result['format'] = file_ext
            
            if file_ext not in self.supported_formats:
                result['errors'].append(f"不支持的文件格式: {file_ext}")
                return result
            
            # 具体格式验证
            if file_ext == '.dxf':
                if not self._validate_dxf_content(file_path):
                    result['errors'].append("DXF文件内容验证失败")
                    return result
            elif file_ext == '.dwg':
                if not self._validate_dwg_content(file_path):
                    result['errors'].append("DWG文件内容验证失败")
                    return result
            
            result['valid'] = True
            logger.info(f"文件验证通过: {file_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"文件验证异常: {e}")
            return {
                'valid': False,
                'file_path': str(file_path),
                'errors': [f"验证过程异常: {str(e)}"]
            }
    
    def _validate_dxf_content(self, file_path: Path) -> bool:
        """验证DXF文件内容"""
        try:
            # 读取文件前几行检查DXF格式
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline().strip() for _ in range(10)]
                
            # 检查DXF标识
            dxf_indicators = ['0', 'SECTION', 'HEADER', 'ENTITIES', 'EOF']
            found_indicators = sum(1 for line in first_lines if line in dxf_indicators)
            
            if found_indicators < 2:
                logger.warning(f"DXF文件格式可疑: {first_lines[:5]}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"DXF内容验证失败: {e}")
            return False
    
    def _validate_dwg_content(self, file_path: Path) -> bool:
        """验证DWG文件内容"""
        try:
            # 检查DWG文件头
            with open(file_path, 'rb') as f:
                header = f.read(16)
                
            # DWG文件应该以特定字节序列开头
            if len(header) < 6:
                return False
                
            # 检查DWG版本标识
            dwg_signatures = [
                b'AC1015',  # AutoCAD 2000-2002
                b'AC1018',  # AutoCAD 2004-2006  
                b'AC1021',  # AutoCAD 2007-2009
                b'AC1024',  # AutoCAD 2010-2012
                b'AC1027',  # AutoCAD 2013-2017
                b'AC1032'   # AutoCAD 2018+
            ]
            
            for signature in dwg_signatures:
                if signature in header:
                    return True
            
            logger.warning(f"未识别的DWG版本: {header[:10]}")
            return False
            
        except Exception as e:
            logger.error(f"DWG内容验证失败: {e}")
            return False
    
    def quick_validate(self, file_path: str) -> bool:
        """快速验证文件（仅检查基本属性）"""
        try:
            file_path = Path(file_path)
            
            # 基本检查
            if not file_path.exists():
                return False
            
            if file_path.stat().st_size < self.min_file_size:
                return False
            
            if file_path.suffix.lower() not in self.supported_formats:
                return False
                
            return True
            
        except Exception:
            return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件详细信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {'error': '文件不存在'}
            
            stat = file_path.stat()
            
            return {
                'name': file_path.name,
                'size': stat.st_size,
                'format': file_path.suffix.lower(),
                'modified_time': stat.st_mtime,
                'is_readable': os.access(file_path, os.R_OK),
                'absolute_path': str(file_path.absolute())
            }
            
        except Exception as e:
            return {'error': f'获取文件信息失败: {str(e)}'} 