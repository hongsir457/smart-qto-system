# -*- coding: utf-8 -*-
"""
专业图像增强模块 - 针对建筑施工图纸OCR优化
解决模糊、对比度低、倾斜、色彩干扰、干扰线等问题
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional
from pathlib import Path
import math

logger = logging.getLogger(__name__)

class ConstructionDrawingImageEnhancer:
    """建筑施工图纸专用图像增强器"""
    
    def __init__(self):
        """初始化图像增强器"""
        self.kernel_sizes = {
            'small': (3, 3),
            'medium': (5, 5),
            'large': (7, 7)
        }
        
    def enhance_for_ocr(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        完整的OCR图像增强流程
        
        Args:
            image_path: 输入图像路径
            output_path: 输出图像路径，如果为None则覆盖原图
            
        Returns:
            str: 增强后的图像路径
        """
        try:
            logger.info(f"🔧 开始图像增强处理: {image_path}")
            
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"无法读取图像: {image_path}")
            
            original_height, original_width = image.shape[:2]
            logger.info(f"📐 原始图像尺寸: {original_width}×{original_height}")
            
            # 执行增强流程
            enhanced_image = self._enhance_pipeline(image)
            
            # 保存增强后的图像
            if output_path is None:
                output_path = image_path
            
            cv2.imwrite(output_path, enhanced_image)
            
            enhanced_height, enhanced_width = enhanced_image.shape[:2]
            logger.info(f"✅ 图像增强完成: {enhanced_width}×{enhanced_height} -> {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ 图像增强失败: {str(e)}")
            return image_path  # 返回原图路径作为备选
    
    def _enhance_pipeline(self, image: np.ndarray) -> np.ndarray:
        """
        图像增强主流程
        
        Args:
            image: 输入图像
            
        Returns:
            np.ndarray: 增强后的图像
        """
        # 1. 倾斜校正
        image = self._correct_skew(image)
        
        # 2. 噪声去除
        image = self._remove_noise(image)
        
        # 3. 对比度增强
        image = self._enhance_contrast(image)
        
        # 4. 锐化处理
        image = self._sharpen_image(image)
        
        # 5. 干扰线去除
        image = self._remove_interference_lines(image)
        
        # 6. 文字区域优化
        image = self._optimize_text_regions(image)
        
        # 7. 最终优化
        image = self._final_optimization(image)
        
        return image
    
    def _correct_skew(self, image: np.ndarray) -> np.ndarray:
        """
        倾斜校正 - 检测并校正图像倾斜
        """
        try:
            logger.debug("🔄 执行倾斜校正...")
            
            # 检查输入图像
            if image is None or image.size == 0:
                logger.warning("⚠️ 输入图像为空，跳过倾斜校正")
                return image
            
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 边缘检测 - 使用自适应参数
            # 根据图像尺寸调整Canny参数
            height, width = gray.shape
            max_dimension = max(height, width)
            
            if max_dimension > 3000:
                # 高分辨率图像使用更高的阈值
                low_threshold = 80
                high_threshold = 200
                aperture_size = 5
            else:
                # 标准分辨率
                low_threshold = 50
                high_threshold = 150
                aperture_size = 3
                
            edges = cv2.Canny(gray, low_threshold, high_threshold, apertureSize=aperture_size)
            
            # 霍夫直线检测 - 多级检测策略
            lines = None
            thresholds = [150, 100, 80, 60]  # 从严格到宽松的阈值
            
            for threshold in thresholds:
                lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=threshold)
                if lines is not None and len(lines) >= 5:  # 至少需要5条线
                    logger.debug(f"🎯 使用阈值 {threshold} 检测到足够的直线")
                    break
                    
            if lines is None:
                logger.debug("🔍 未检测到足够的直线，尝试降低要求...")
                lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=30)
            
            if lines is not None and len(lines) > 0:
                logger.debug(f"🔍 检测到 {len(lines)} 条直线，格式: {type(lines)}, 形状: {lines.shape if hasattr(lines, 'shape') else 'N/A'}")
                # 计算主要角度
                angles = []
                for line in lines[:20]:  # 只使用前20条线
                    # 兼容不同OpenCV版本的返回格式
                    if isinstance(line, np.ndarray) and line.shape == (1, 2):
                        rho, theta = line[0]
                    elif isinstance(line, (list, tuple)) and len(line) == 2:
                        rho, theta = line
                    elif isinstance(line, np.ndarray) and len(line) == 2:
                        rho, theta = line
                    else:
                        logger.debug(f"⚠️ 跳过格式不匹配的直线数据: {line}")
                        continue
                        
                    angle = theta * 180 / np.pi
                    # 过滤接近水平或垂直的线
                    if abs(angle - 90) < 45:
                        angles.append(angle - 90)
                    elif abs(angle) < 45:
                        angles.append(angle)
                
                if angles:
                    logger.debug(f"📊 收集到 {len(angles)} 个角度值: {angles[:10]}")
                    
                    # 计算平均角度
                    avg_angle = np.median(angles)
                    
                    # 如果倾斜角度超过阈值，进行校正
                    if abs(avg_angle) > 0.5:
                        logger.debug(f"📐 检测到倾斜角度: {avg_angle:.2f}°")
                        
                        # 限制旋转角度，避免过度校正
                        if abs(avg_angle) > 45:
                            logger.warning(f"⚠️ 检测到异常大的倾斜角度 {avg_angle:.2f}°，限制在±45°内")
                            avg_angle = np.clip(avg_angle, -45, 45)
                        
                        # 计算旋转中心
                        height, width = image.shape[:2]
                        center = (width // 2, height // 2)
                        
                        # 创建旋转矩阵
                        rotation_matrix = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
                        
                        # 执行旋转
                        image = cv2.warpAffine(image, rotation_matrix, (width, height), 
                                             flags=cv2.INTER_CUBIC, 
                                             borderMode=cv2.BORDER_REPLICATE)
                        
                        logger.debug(f"✅ 倾斜校正完成，角度: {avg_angle:.2f}°")
                    else:
                        logger.debug(f"📏 倾斜角度 {avg_angle:.2f}° 在正常范围内，无需校正")
                else:
                    logger.debug("📏 未检测到有效的倾斜角度")
            
            return image
            
        except Exception as e:
            logger.warning(f"⚠️ 倾斜校正失败: {str(e)}")
            return image
    
    def _remove_noise(self, image: np.ndarray) -> np.ndarray:
        """
        噪声去除 - 去除椒盐噪声、高斯噪声等
        """
        try:
            logger.debug("🔧 执行噪声去除...")
            
            # 双边滤波 - 保持边缘的同时去噪
            image = cv2.bilateralFilter(image, 9, 75, 75)
            
            # 形态学开运算去除小噪点
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
            
            logger.debug("✅ 噪声去除完成")
            return image
            
        except Exception as e:
            logger.warning(f"⚠️ 噪声去除失败: {str(e)}")
            return image
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        对比度增强 - CLAHE自适应直方图均衡化，针对超高分辨率优化
        """
        try:
            logger.debug("🌟 执行对比度增强...")
            
            # 根据图像分辨率自适应调整CLAHE参数
            height, width = image.shape[:2]
            max_dimension = max(height, width)
            
            # 超高分辨率图像使用更大的tile grid
            if max_dimension > 6000:
                tile_grid_size = (16, 16)  # 超高分辨率
                clip_limit = 3.0
                logger.debug("🔍 检测到超高分辨率图像，使用增强CLAHE参数")
            elif max_dimension > 3000:
                tile_grid_size = (12, 12)  # 高分辨率
                clip_limit = 2.8
                logger.debug("🔍 检测到高分辨率图像，使用优化CLAHE参数")
            else:
                tile_grid_size = (8, 8)    # 标准分辨率
                clip_limit = 2.5
                logger.debug("🔍 标准分辨率图像，使用默认CLAHE参数")
            
            # 转换为LAB颜色空间
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 对L通道进行自适应CLAHE
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
            l = clahe.apply(l)
            
            # 合并通道
            lab = cv2.merge([l, a, b])
            image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # 根据分辨率调整对比度参数
            if max_dimension > 6000:
                alpha = 1.15  # 超高分辨率轻微增强
                beta = 8
            else:
                alpha = 1.2   # 标准增强
                beta = 10
                
            image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
            
            logger.debug("✅ 对比度增强完成")
            return image
            
        except Exception as e:
            logger.warning(f"⚠️ 对比度增强失败: {str(e)}")
            return image
    
    def _sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """
        锐化处理 - 增强文字边缘
        """
        try:
            logger.debug("⚡ 执行锐化处理...")
            
            # 拉普拉斯锐化核
            kernel = np.array([[-1, -1, -1],
                              [-1,  9, -1],
                              [-1, -1, -1]], dtype=np.float32)
            
            # 应用锐化
            sharpened = cv2.filter2D(image, -1, kernel)
            
            # 混合原图和锐化图
            image = cv2.addWeighted(image, 0.7, sharpened, 0.3, 0)
            
            logger.debug("✅ 锐化处理完成")
            return image
            
        except Exception as e:
            logger.warning(f"⚠️ 锐化处理失败: {str(e)}")
            return image
    
    def _remove_interference_lines(self, image: np.ndarray) -> np.ndarray:
        """
        干扰线去除 - 去除建筑图纸中的网格线、辅助线等，针对超高分辨率优化
        """
        try:
            logger.debug("🗂️ 执行干扰线去除...")
            
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 根据图像分辨率自适应调整kernel大小
            height, width = gray.shape
            max_dimension = max(height, width)
            
            if max_dimension > 6000:
                # 超高分辨率图像使用更大的kernel
                h_kernel_size = (60, 1)
                v_kernel_size = (1, 60)
                inpaint_radius = 5
                logger.debug("🔍 超高分辨率图像，使用增强干扰线检测参数")
            elif max_dimension > 3000:
                # 高分辨率图像
                h_kernel_size = (40, 1)
                v_kernel_size = (1, 40)
                inpaint_radius = 4
                logger.debug("🔍 高分辨率图像，使用优化干扰线检测参数")
            else:
                # 标准分辨率
                h_kernel_size = (25, 1)
                v_kernel_size = (1, 25)
                inpaint_radius = 3
                logger.debug("🔍 标准分辨率图像，使用默认干扰线检测参数")
            
            # 检测水平线
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, h_kernel_size)
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
            
            # 检测垂直线
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, v_kernel_size)
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
            
            # 合并线条
            grid_lines = cv2.add(horizontal_lines, vertical_lines)
            
            # 将检测到的线条从原图中减去（只减去细线）
            mask = grid_lines < 50  # 只处理较细的线条
            
            # 在线条位置进行修复
            result = image.copy()
            
            # 创建修复掩码
            inpaint_mask = (~mask).astype(np.uint8)
            
            # 只有当掩码不为空时才进行修复
            if np.any(inpaint_mask):
                # 对整个图像进行修复
                result = cv2.inpaint(result, inpaint_mask, inpaint_radius, cv2.INPAINT_TELEA)
            
            logger.debug("✅ 干扰线去除完成")
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 干扰线去除失败: {str(e)}")
            return image
    
    def _optimize_text_regions(self, image: np.ndarray) -> np.ndarray:
        """
        文字区域优化 - 专门针对文字区域进行优化
        """
        try:
            logger.debug("📝 执行文字区域优化...")
            
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 文字区域检测
            # 使用形态学操作检测文字块
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            
            # 闭运算连接字符
            closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            
            # 自适应阈值处理
            adaptive_thresh = cv2.adaptiveThreshold(
                closed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 将处理结果应用回彩色图像
            # 使用掩码增强文字区域
            text_mask = adaptive_thresh == 0  # 文字区域为黑色
            
            enhanced = image.copy()
            for c in range(3):
                channel = enhanced[:, :, c]
                # 在文字区域增强对比度
                channel[text_mask] = np.clip(channel[text_mask] * 0.8, 0, 255)
                enhanced[:, :, c] = channel
            
            logger.debug("✅ 文字区域优化完成")
            return enhanced
            
        except Exception as e:
            logger.warning(f"⚠️ 文字区域优化失败: {str(e)}")
            return image
    
    def _final_optimization(self, image: np.ndarray) -> np.ndarray:
        """
        最终优化 - 最后的调整和优化
        """
        try:
            logger.debug("🎨 执行最终优化...")
            
            # 伽马校正
            gamma = 1.2
            invGamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            image = cv2.LUT(image, table)
            
            # 轻微的高斯滤波，减少锯齿
            image = cv2.GaussianBlur(image, (1, 1), 0)
            
            logger.debug("✅ 最终优化完成")
            return image
            
        except Exception as e:
            logger.warning(f"⚠️ 最终优化失败: {str(e)}")
            return image
    
    def _detect_resolution_issues(self, image: np.ndarray) -> dict:
        """
        检测图像质量问题
        
        Returns:
            dict: 检测结果
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 检测模糊度
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 检测对比度
            contrast_score = gray.std()
            
            # 检测亮度
            brightness_score = gray.mean()
            
            return {
                'blur_score': blur_score,
                'contrast_score': contrast_score,
                'brightness_score': brightness_score,
                'is_blurry': blur_score < 100,
                'is_low_contrast': contrast_score < 50,
                'is_too_dark': brightness_score < 80,
                'is_too_bright': brightness_score > 200
            }
            
        except Exception as e:
            logger.error(f"图像质量检测失败: {str(e)}")
            return {}

# 创建全局实例
image_enhancer = ConstructionDrawingImageEnhancer() 