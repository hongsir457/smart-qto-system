#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWG转换器
专门负责DWG到DXF的转换
"""

import os
import logging
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any, List
from pathlib import Path

from .file_validator import FileValidator

logger = logging.getLogger(__name__)

class DWGConverter:
    """DWG转换器类"""
    
    def __init__(self):
        """初始化DWG转换器"""
        self.validator = FileValidator()
        self.temp_dir = None
        self.oda_available = self._check_oda_converter()
    
    def convert_to_dxf(self, dwg_path: str) -> Optional[str]:
        """
        将DWG文件转换为DXF格式
        
        Args:
            dwg_path: DWG文件路径
            
        Returns:
            转换后的DXF文件路径，失败返回None
        """
        try:
            # 验证输入文件
            validation_result = self.validator.validate_input_file(dwg_path)
            if not validation_result['valid']:
                logger.error(f"文件验证失败: {validation_result['errors']}")
                return None
            
            dwg_path = Path(dwg_path)
            
            # 如果已经是DXF文件，直接返回
            if dwg_path.suffix.lower() == '.dxf':
                logger.info(f"文件已是DXF格式: {dwg_path}")
                return str(dwg_path)
            
            # 创建临时目录
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp(prefix='dwg_convert_')
            
            # 尝试不同的转换方法
            dxf_path = None
            
            # 方法1：使用ODA文件转换器
            if self.oda_available:
                logger.info("尝试使用ODA文件转换器...")
                dxf_path = self._convert_with_oda(str(dwg_path))
            
            # 方法2：手动转换（备用方法）
            if not dxf_path:
                logger.info("尝试手动转换方法...")
                dxf_path = self._manual_convert(str(dwg_path))
            
            # 验证转换结果
            if dxf_path and self.validator.validate_input_file(dxf_path)['valid']:
                logger.info(f"DWG转换成功: {dwg_path} -> {dxf_path}")
                return dxf_path
            else:
                logger.error(f"DWG转换失败: {dwg_path}")
                return None
                
        except Exception as e:
            logger.error(f"DWG转换异常: {e}")
            return None
    
    def _convert_with_oda(self, dwg_path: str) -> Optional[str]:
        """使用ODA文件转换器转换DWG"""
        try:
            dwg_path = Path(dwg_path)
            output_dir = Path(self.temp_dir) / 'oda_output'
            output_dir.mkdir(exist_ok=True)
            
            # 构建ODA转换器命令
            cmd = [
                'ODAFileConverter',
                str(dwg_path.parent),
                str(output_dir),
                'ACAD2018',
                'DXF',
                '0',
                '1',
                dwg_path.name
            ]
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                # 查找生成的DXF文件
                dxf_name = dwg_path.stem + '.dxf'
                dxf_path = output_dir / dxf_name
                
                if dxf_path.exists():
                    return str(dxf_path)
            
            logger.warning(f"ODA转换失败: {result.stderr}")
            return None
            
        except subprocess.TimeoutExpired:
            logger.error("ODA转换超时")
            return None
        except Exception as e:
            logger.error(f"ODA转换异常: {e}")
            return None
    
    def _manual_convert(self, dwg_path: str) -> Optional[str]:
        """手动转换方法（简化版）"""
        try:
            # 尝试使用ezdxf库
            try:
                import ezdxf
                from ezdxf import recover
                
                # 尝试恢复损坏的DWG文件并转换
                dwg_path = Path(dwg_path)
                dxf_path = Path(self.temp_dir) / f"{dwg_path.stem}.dxf"
                
                doc, auditor = recover.readfile(str(dwg_path))
                doc.saveas(str(dxf_path))
                
                if dxf_path.exists():
                    logger.info(f"手动转换成功: {dxf_path}")
                    return str(dxf_path)
                    
            except ImportError:
                logger.warning("ezdxf库不可用，无法进行手动转换")
            except Exception as e:
                logger.warning(f"ezdxf转换失败: {e}")
            
            # 如果所有方法都失败，返回None
            return None
            
        except Exception as e:
            logger.error(f"手动转换异常: {e}")
            return None
    
    def _check_oda_converter(self) -> bool:
        """检查ODA文件转换器是否可用"""
        try:
            result = subprocess.run(
                ['ODAFileConverter'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def batch_convert(self, dwg_files: List[str]) -> Dict[str, Optional[str]]:
        """
        批量转换DWG文件
        
        Args:
            dwg_files: DWG文件路径列表
            
        Returns:
            转换结果字典 {原文件路径: 转换后路径}
        """
        results = {}
        
        for dwg_file in dwg_files:
            try:
                dxf_path = self.convert_to_dxf(dwg_file)
                results[dwg_file] = dxf_path
                
                if dxf_path:
                    logger.info(f"批量转换成功: {dwg_file}")
                else:
                    logger.error(f"批量转换失败: {dwg_file}")
                    
            except Exception as e:
                logger.error(f"批量转换异常 {dwg_file}: {e}")
                results[dwg_file] = None
        
        return results
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"清理临时目录: {self.temp_dir}")
                self.temp_dir = None
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    def __del__(self):
        """析构函数，自动清理"""
        self.cleanup() 