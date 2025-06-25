#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像处理工具函数，用于OCR预处理。
"""
import cv2
import numpy as np
import logging
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

def correct_skew(image_path: str, threshold: int = 200) -> str:
    """
    对图像进行倾斜校正。
    
    Args:
        image_path (str): 输入图像的路径。
        threshold (int): Canny边缘检测的阈值。

    Returns:
        str: 校正后图像的保存路径。
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            logger.warning(f"无法读取图像文件: {image_path}，跳过倾斜校正。")
            return image_path
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用Canny算子进行边缘检测
        edges = cv2.Canny(gray, threshold, threshold * 2)
        
        # 使用霍夫变换检测直线
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is None:
            logger.info(f"在 {image_path} 中未检测到足够长的直线，跳过倾斜校正。")
            return image_path

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) < 45:  # 只考虑接近水平的线
                angles.append(angle)
        
        if not angles:
            logger.info(f"在 {image_path} 中未检测到合适的角度，跳过倾斜校正。")
            return image_path
            
        # 计算角度的中位数以获得稳健的估计
        median_angle = np.median(angles)
        
        if abs(median_angle) < 0.1: # 如果倾斜角度非常小，则无需校正
            logger.info(f"图像倾斜角度 ({median_angle:.2f}度) 很小，无需校正。")
            return image_path

        logger.info(f"检测到图像倾斜角度: {median_angle:.2f}度。正在进行校正...")
        
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        
        # 获取旋转矩阵并执行旋转
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        # 保存校正后的图像到临时文件
        temp_path = Path(tempfile.gettempdir()) / f"corrected_{Path(image_path).name}"
        cv2.imwrite(str(temp_path), rotated)
        logger.info(f"倾斜校正后的图像已保存到: {temp_path}")
        
        return str(temp_path)

    except Exception as e:
        logger.error(f"处理图像 {image_path} 时发生倾斜校正错误: {e}", exc_info=True)
        return image_path


def enhance_image(image_path: str) -> str:
    """
    增强图像的对比度和亮度，同时保留颜色信息。
    
    Args:
        image_path (str): 输入图像的路径。

    Returns:
        str: 增强后图像的保存路径。
    """
    try:
        # 以彩色模式读取图像
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if image is None:
            logger.warning(f"无法读取图像文件: {image_path}，跳过图像增强。")
            return image_path

        # 将BGR图像转换为LAB色彩空间
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # 分离L, A, B通道
        l, a, b = cv2.split(lab)
        
        # 对L（亮度）通道应用CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        
        # 合并处理后的L通道和原始的A, B通道
        limg = cv2.merge((cl, a, b))
        
        # 将图像从LAB转换回BGR
        enhanced_image = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # 保存增强后的图像
        temp_path = Path(tempfile.gettempdir()) / f"enhanced_color_{Path(image_path).name}"
        cv2.imwrite(str(temp_path), enhanced_image)
        logger.info(f"彩色图像增强完成，已保存到: {temp_path}")
        
        return str(temp_path)
        
    except Exception as e:
        logger.error(f"处理图像 {image_path} 时发生增强错误: {e}", exc_info=True)
        return image_path


def calculate_image_clarity(image_path: str) -> float:
    """
    计算图像的清晰度（使用拉普拉斯算子的方差）。
    
    Args:
        image_path (str): 图像路径。

    Returns:
        float: 清晰度得分，分值越高表示图像越清晰。
    """
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            logger.warning(f"无法读取图像文件: {image_path}，无法计算清晰度。")
            return 0.0
        
        # 计算拉普拉斯算子的方差
        clarity = cv2.Laplacian(image, cv2.CV_64F).var()
        return float(clarity)
        
    except Exception as e:
        logger.error(f"计算图像 {image_path} 清晰度时出错: {e}", exc_info=True)
        return 0.0 