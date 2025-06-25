#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像预处理模块 - 专门为PaddleOCR优化
自动调整图像尺寸、DPI、对比度等，以获得最佳OCR识别效果
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional, Union
from pathlib import Path
import math
from PIL import Image, ImageEnhance, ImageFilter
from ..core.config import settings

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """图像预处理器 - 为PaddleOCR优化图像"""
    
    def __init__(self):
        self.target_dpi = settings.PADDLE_OCR_TARGET_DPI
        self.min_text_height = settings.PADDLE_OCR_MIN_HEIGHT
        self.max_size = settings.PADDLE_OCR_MAX_SIZE
        self.smart_scale = settings.PADDLE_OCR_SMART_SCALE
        self.contrast_enhance = settings.PADDLE_OCR_CONTRAST_ENHANCE
        self.noise_reduction = settings.PADDLE_OCR_NOISE_REDUCTION
        
        logger.info(f"🔧 ImagePreprocessor initialized with DPI={self.target_dpi}, "
                   f"min_height={self.min_text_height}, max_size={self.max_size}")
    
    def auto_resize_for_ocr(self, image_path: Union[str, Path]) -> str:
        """
        自动调整图像尺寸以获得最佳OCR效果
        
        Args:
            image_path: 输入图像路径
            
        Returns:
            str: 处理后图像的路径
        """
        if not settings.PADDLE_OCR_AUTO_RESIZE:
            logger.info("🔧 自动resize已禁用，返回原图")
            return str(image_path)
            
        try:
            image_path = Path(image_path)
            logger.info(f"🔧 开始为OCR优化图像: {image_path.name}")
            
            # 使用PIL加载图像（更好的格式支持）
            pil_image = Image.open(image_path)
            original_size = pil_image.size
            logger.info(f"📏 原始尺寸: {original_size[0]}x{original_size[1]}")
            
            # 转换为OpenCV格式进行处理
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # 步骤1: 计算最佳缩放比例
            optimal_scale = self._calculate_optimal_scale(cv_image)
            logger.info(f"📐 计算得出最佳缩放比例: {optimal_scale:.2f}")
            
            # 步骤2: 应用缩放
            if optimal_scale != 1.0:
                cv_image = self._resize_image(cv_image, optimal_scale)
                logger.info(f"🔄 图像已缩放到: {cv_image.shape[1]}x{cv_image.shape[0]}")
            
            # 步骤3: 图像质量增强
            if self.contrast_enhance or self.noise_reduction:
                cv_image = self._enhance_image_quality(cv_image)
                logger.info("✨ 图像质量增强完成")
            
            # 步骤4: 保存优化后的图像
            output_path = self._save_optimized_image(cv_image, image_path)
            logger.info(f"💾 优化后图像已保存: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ 图像预处理失败: {e}", exc_info=True)
            return str(image_path)  # 失败时返回原图
    
    def _calculate_optimal_scale(self, image: np.ndarray) -> float:
        """计算最佳缩放比例"""
        height, width = image.shape[:2]
        current_max_side = max(width, height)
        
        # 如果启用智能缩放，分析文字大小
        if self.smart_scale:
            estimated_text_height = self._estimate_text_height(image)
            logger.info(f"📝 估计文字高度: {estimated_text_height}px")
            
            if estimated_text_height > 0:
                # 基于文字高度计算缩放比例
                text_scale = self.min_text_height / estimated_text_height
                logger.info(f"📝 基于文字高度的缩放比例: {text_scale:.2f}")
                
                # 确保不超过最大尺寸限制
                size_scale = self.max_size / current_max_side
                
                # 取较小值，但不小于0.5，不大于3.0
                optimal_scale = min(text_scale, size_scale)
                optimal_scale = max(0.5, min(3.0, optimal_scale))
                
                return optimal_scale
        
        # 常规缩放逻辑
        if current_max_side > self.max_size:
            return self.max_size / current_max_side
        elif current_max_side < 1024:  # 图像太小，适当放大
            return min(2.0, 1024 / current_max_side)
        
        return 1.0
    
    def _estimate_text_height(self, image: np.ndarray) -> float:
        """估计图像中文字的平均高度"""
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 边缘检测
            edges = cv2.Canny(gray, 50, 150)
            
            # 形态学操作，连接文字的边缘
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
            dilated = cv2.dilate(edges, kernel, iterations=1)
            
            # 查找轮廓
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 过滤并统计文字区域的高度
            text_heights = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # 过滤条件：宽高比合理，面积适中
                aspect_ratio = w / h if h > 0 else 0
                area = w * h
                
                if (0.1 < aspect_ratio < 20 and 
                    100 < area < image.shape[0] * image.shape[1] * 0.1 and
                    h > 8):  # 高度至少8像素
                    text_heights.append(h)
            
            if text_heights:
                # 使用中位数作为典型文字高度
                text_heights.sort()
                median_height = text_heights[len(text_heights) // 2]
                logger.info(f"📊 检测到{len(text_heights)}个文字区域，中位数高度: {median_height}px")
                return median_height
            
            return 0
            
        except Exception as e:
            logger.warning(f"⚠️ 文字高度估计失败: {e}")
            return 0
    
    def _resize_image(self, image: np.ndarray, scale: float) -> np.ndarray:
        """调整图像尺寸，使用高质量插值"""
        height, width = image.shape[:2]
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # 选择合适的插值方法
        if scale > 1.0:
            # 放大时使用立方插值
            interpolation = cv2.INTER_CUBIC
        else:
            # 缩小时使用区域插值
            interpolation = cv2.INTER_AREA
        
        resized = cv2.resize(image, (new_width, new_height), interpolation=interpolation)
        return resized
    
    def _enhance_image_quality(self, image: np.ndarray) -> np.ndarray:
        """
        增强图像质量以提升OCR效果 - 采用更保守的策略
        使用CLAHE增强对比度，并用小内核开运算去噪。
        """
        try:
            logger.info("✨ 应用更保守的图像增强流程...")

            # 1. 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 2. 使用CLAHE（对比度受限的自适应直方图均衡化）增强低对比度区域
            # clipLimit: 对比度限制，值越小，对比度增强越温和
            # tileGridSize: 网格大小，用于局部直方图均衡化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            clahe_enhanced = clahe.apply(gray)
            logger.info("✨ 步骤1/2: CLAHE 对比度增强完成。")

            # 3. 形态学开运算去噪
            # 使用一个小的 (2,2) 内核来执行开运算（腐蚀后膨胀），以去除小的背景噪声
            # 这种方法比直接腐蚀或激进的二值化更能保留文字的完整性
            kernel = np.ones((2, 2), np.uint8)
            morph_opened = cv2.morphologyEx(clahe_enhanced, cv2.MORPH_OPEN, kernel, iterations=1)
            logger.info("✨ 步骤2/2: 形态学开运算去噪完成。")

            # 将处理后的单通道灰度图转换回BGR三通道格式
            enhanced_image = cv2.cvtColor(morph_opened, cv2.COLOR_GRAY2BGR)
            return enhanced_image

        except Exception as e:
            logger.warning(f"⚠️ 图像质量增强失败: {e}", exc_info=True)
            # 失败时返回原始图像
            return image
    
    def _save_optimized_image(self, image: np.ndarray, original_path: Path) -> str:
        """保存优化后的图像"""
        # 生成输出文件名
        output_dir = original_path.parent / "optimized"
        output_dir.mkdir(exist_ok=True)
        
        stem = original_path.stem
        suffix = original_path.suffix
        output_path = output_dir / f"{stem}_ocr_optimized{suffix}"
        
        # 保存图像，使用高质量设置
        success = cv2.imwrite(str(output_path), image, [
            cv2.IMWRITE_PNG_COMPRESSION, 1,  # 最低压缩
            cv2.IMWRITE_JPEG_QUALITY, 98     # 高质量JPEG
        ])
        
        if success:
            return str(output_path)
        else:
            logger.error(f"❌ 保存优化图像失败: {output_path}")
            return str(original_path)
    
    def get_image_info(self, image_path: Union[str, Path]) -> dict:
        """获取图像信息用于调试"""
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                return {"error": "无法读取图像"}
            
            height, width = image.shape[:2]
            file_size = Path(image_path).stat().st_size
            
            # 估计文字高度
            text_height = self._estimate_text_height(image)
            
            return {
                "width": width,
                "height": height,
                "max_side": max(width, height),
                "file_size_mb": file_size / (1024 * 1024),
                "estimated_text_height": text_height,
                "recommended_scale": self._calculate_optimal_scale(image)
            }
            
        except Exception as e:
            return {"error": str(e)}

# 创建全局实例
image_preprocessor = ImagePreprocessor()
