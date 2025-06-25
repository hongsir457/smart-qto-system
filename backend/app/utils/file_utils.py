"""
文件处理工具模块
"""

import os


def extract_file_type(filename: str) -> str:
    """
    从文件名提取文件类型
    
    Args:
        filename: 文件名
        
    Returns:
        文件类型字符串 (pdf, dwg, dxf, jpg, png, unknown)
    """
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext == '.pdf':
        return 'pdf'
    elif file_ext == '.dwg':
        return 'dwg'
    elif file_ext == '.dxf':
        return 'dxf'
    elif file_ext in ['.jpg', '.jpeg']:
        return 'jpg'
    elif file_ext == '.png':
        return 'png'
    else:
        return 'unknown'


def get_safe_file_type(file_type: str, filename: str = None) -> str:
    """
    获取安全的文件类型，如果file_type为空，则从filename推断
    
    Args:
        file_type: 当前的文件类型
        filename: 文件名（用于推断）
        
    Returns:
        安全的文件类型字符串
    """
    if file_type:
        return file_type.lower()
    
    if filename:
        return extract_file_type(filename)
    
    return 'unknown' 