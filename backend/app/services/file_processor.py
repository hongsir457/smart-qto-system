#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件处理器 - 按文件类型分流处理
支持 PDF、DWG/DXF、图片等格式
"""

import os
import logging
import tempfile
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

# 导入各种文件处理库
try:
    import pdf2image
    from pdf2image import convert_from_path
except ImportError:
    pdf2image = None

try:
    import ezdxf
except ImportError:
    ezdxf = None

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
except ImportError:
    plt = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None

from PIL import Image

# Disable decompression bomb check to handle large high-resolution images
Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger(__name__)

class FileProcessor:
    """文件处理器 - 根据文件类型进行不同的处理"""
    
    def __init__(self):
        """初始化处理器"""
        self.temp_dir = tempfile.gettempdir()
        self.supported_formats = {
            'pdf': ['.pdf'],
            'cad': ['.dwg', '.dxf'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        }
    
    def process_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        根据文件类型处理文件
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            Dict: 处理结果
        """
        try:
            logger.info(f"🔄 开始处理文件: {file_path}, 类型: {file_type}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 根据文件扩展名确定处理方法
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                return self.process_pdf(file_path)
            elif file_ext in ['.dwg', '.dxf']:
                return self.process_cad(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                return self.process_image(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
                
        except Exception as e:
            logger.error(f"❌ 文件处理失败: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'image_paths': [],
                'text_content': '',
                'processing_method': 'unknown'
            }
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        处理PDF文件 - 转换为图片
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            Dict: 处理结果
        """
        try:
            logger.info(f"📄 开始处理PDF文件: {pdf_path}")
            
            if not pdf2image:
                raise ImportError("pdf2image 库未安装，无法处理PDF文件")
            
            # 检查文件大小和完整性
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError("PDF文件为空")
            
            logger.info(f"📄 PDF文件大小: {file_size} 字节")
            
            # 尝试验证PDF文件头
            try:
                with open(pdf_path, 'rb') as f:
                    header = f.read(8)
                    if not header.startswith(b'%PDF'):
                        raise ValueError("文件头验证失败，不是有效的PDF文件")
            except Exception as header_error:
                logger.warning(f"PDF文件头验证失败: {header_error}")
            
            # 使用300 DPI进行转换
            try:
                images = convert_from_path(
                    pdf_path,
                    dpi=300,  # 使用300 DPI平衡性能和精度
                    output_folder=self.temp_dir,
                    fmt='png',
                    thread_count=4 # 利用多核加速转换
                )
            except Exception as convert_error:
                logger.error(f"PDF在300 DPI下转换失败: {convert_error}", exc_info=True)
                raise Exception(f"PDF转换失败: {convert_error}")
            
            if not images:
                raise ValueError("PDF转换后没有生成任何图片页面")
            
            image_paths = []
            page_uuid = str(uuid.uuid4())
            
            for i, image in enumerate(images):
                # 保存每页图片
                image_path = os.path.join(
                    self.temp_dir, 
                    f"temp_page_{page_uuid}_{i}.png"
                )
                image.save(image_path, 'PNG')
                image_paths.append(image_path)
                
                logger.info(f"📄 PDF第{i+1}页已转换为图片: {image_path}")
            
            logger.info(f"✅ PDF处理完成，共转换 {len(image_paths)} 页图片")
            
            return {
                'status': 'success',
                'image_paths': image_paths,
                'text_content': '',  # PDF文本提取需要另外处理
                'processing_method': 'pdf_to_images',
                'total_pages': len(image_paths)
            }
            
        except Exception as e:
            logger.error(f"❌ PDF处理失败: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'image_paths': [],
                'text_content': '',
                'processing_method': 'pdf_to_images'
            }
    
    def process_cad(self, cad_path: str) -> Dict[str, Any]:
        """
        处理CAD文件 - DWG/DXF
        
        Args:
            cad_path: CAD文件路径
            
        Returns:
            Dict: 处理结果
        """
        try:
            logger.info(f"🏗️ 开始处理CAD文件: {cad_path}")
            
            file_ext = Path(cad_path).suffix.lower()
            
            if file_ext == '.dxf':
                return self._process_dxf(cad_path)
            elif file_ext == '.dwg':
                return self._process_dwg(cad_path)
            else:
                raise ValueError(f"不支持的CAD格式: {file_ext}")
                
        except Exception as e:
            logger.error(f"❌ CAD文件处理失败: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'image_paths': [],
                'text_content': '',
                'processing_method': 'cad_processing'
            }
    
    def _process_dxf(self, dxf_path: str) -> Dict[str, Any]:
        """处理DXF文件"""
        try:
            if not ezdxf:
                raise ImportError("ezdxf 库未安装，无法处理DXF文件")
            
            logger.info(f"📐 读取DXF文件: {dxf_path}")
            
            # 读取DXF文件
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # 尝试提取文字实体
            text_content = self._extract_text_from_dxf(msp)
            
            if text_content.strip():
                logger.info(f"✅ 从DXF提取到文字内容: {len(text_content)} 字符")
                return {
                    'status': 'success',
                    'image_paths': [],
                    'text_content': text_content,
                    'processing_method': 'dxf_text_extraction',
                    'has_text_entities': True
                }
            else:
                # 如果没有文字实体，渲染为图片
                logger.info("📐 DXF文件没有文字实体，渲染为图片...")
                image_path = self._render_dxf_to_image(msp)
                
                return {
                    'status': 'success',
                    'image_paths': [image_path] if image_path else [],
                    'text_content': '',
                    'processing_method': 'dxf_to_image',
                    'has_text_entities': False
                }
                
        except Exception as e:
            logger.error(f"❌ DXF处理失败: {str(e)}")
            raise
    
    def _process_dwg(self, dwg_path: str) -> Dict[str, Any]:
        """处理DWG文件（需要转换为DXF）"""
        try:
            # DWG文件需要专门的库来处理，这里提供一个基础框架
            logger.warning("⚠️ DWG文件支持有限，建议转换为DXF格式")
            
            # 这里可以集成 dwg2dxf 转换工具
            # 或者使用其他DWG处理库
            
            return {
                'status': 'error',
                'error': 'DWG文件暂不支持直接处理，请转换为DXF格式',
                'image_paths': [],
                'text_content': '',
                'processing_method': 'dwg_processing'
            }
            
        except Exception as e:
            logger.error(f"❌ DWG处理失败: {str(e)}")
            raise
    
    def _extract_text_from_dxf(self, msp) -> str:
        """从DXF文件中提取文字实体"""
        text_content = []
        
        try:
            # 提取TEXT实体
            for text_entity in msp.query('TEXT'):
                if hasattr(text_entity, 'dxf') and hasattr(text_entity.dxf, 'text'):
                    text_content.append(text_entity.dxf.text)
            
            # 提取MTEXT实体
            for mtext_entity in msp.query('MTEXT'):
                if hasattr(mtext_entity, 'text'):
                    text_content.append(mtext_entity.text)
            
            return '\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"❌ 提取DXF文字失败: {str(e)}")
            return ''
    
    def _render_dxf_to_image(self, msp) -> Optional[str]:
        """将DXF渲染为图片"""
        try:
            if not plt:
                logger.warning("matplotlib 未安装，无法渲染DXF为图片")
                return None
            
            logger.info("🎨 渲染DXF为图片...")
            
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # 渲染线条实体
            for line in msp.query('LINE'):
                start = line.dxf.start
                end = line.dxf.end
                ax.plot([start.x, end.x], [start.y, end.y], 'k-', linewidth=0.5)
            
            # 渲染圆形实体
            for circle in msp.query('CIRCLE'):
                center = circle.dxf.center
                radius = circle.dxf.radius
                circle_patch = plt.Circle((center.x, center.y), radius, 
                                        fill=False, edgecolor='black', linewidth=0.5)
                ax.add_patch(circle_patch)
            
            # 设置图形属性
            ax.set_aspect('equal')
            ax.axis('off')
            
            # 保存为图片
            cad_uuid = str(uuid.uuid4())
            image_path = os.path.join(self.temp_dir, f"temp_cad_{cad_uuid}.png")
            
            plt.savefig(image_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"✅ DXF渲染完成: {image_path}")
            return image_path
            
        except Exception as e:
            logger.error(f"❌ DXF渲染失败: {str(e)}")
            return None
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        处理图片文件
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            Dict: 处理结果
        """
        try:
            logger.info(f"🖼️ 处理图片文件: {image_path}")
            
            # 验证图片文件
            try:
                with Image.open(image_path) as img:
                    img.verify()
            except Exception as e:
                raise ValueError(f"无效的图片文件: {str(e)}")
            
            # 图片预处理
            processed_image_path = self._preprocess_image(image_path)
            
            return {
                'status': 'success',
                'image_paths': [processed_image_path or image_path],
                'text_content': '',
                'processing_method': 'direct_image_processing',
                'original_path': image_path
            }
            
        except Exception as e:
            logger.error(f"❌ 图片处理失败: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'image_paths': [],
                'text_content': '',
                'processing_method': 'direct_image_processing'
            }
    
    def _preprocess_image(self, image_path: str) -> Optional[str]:
        """
        图像预处理 - OpenCV处理
        
        Args:
            image_path: 原始图片路径
            
        Returns:
            Optional[str]: 处理后的图片路径
        """
        try:
            if not cv2:
                logger.warning("OpenCV 未安装，跳过图像预处理")
                return None
            
            logger.info("🔧 开始图像预处理...")
            
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"无法读取图像: {image_path}")
                return None
            
            # 1. 灰度转换
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 2. 尺寸放大 (1.8x-2.0x)
            scale_factor = 1.9
            height, width = gray.shape
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            resized = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # 3. CLAHE对比度增强
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(resized)
            
            # 4. 双边滤波去噪
            filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)
            
            # 5. 自适应二值化
            binary = cv2.adaptiveThreshold(
                filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 保存预处理后的图像
            image_uuid = str(uuid.uuid4())
            processed_path = os.path.join(
                self.temp_dir, 
                f"preprocessed_{image_uuid}.png"
            )
            
            cv2.imwrite(processed_path, binary)
            
            logger.info(f"✅ 图像预处理完成: {processed_path}")
            return processed_path
            
        except Exception as e:
            logger.error(f"❌ 图像预处理失败: {str(e)}")
            return None
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """清理临时文件"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path) and self.temp_dir in file_path:
                    os.unlink(file_path)
                    logger.info(f"🗑️ 已清理临时文件: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ 清理临时文件失败: {file_path}, 错误: {str(e)}")

# 创建全局文件处理器实例
file_processor = FileProcessor()