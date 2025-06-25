"""
自适应切片引擎 - Step 1 优化
实现基于图框检测和内容密度分析的动态切片策略
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image, ImageDraw
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)

@dataclass
class FrameBounds:
    """图框边界"""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    detection_method: str

@dataclass
class ContentDensity:
    """内容密度信息"""
    total_area: int
    content_area: int
    density_ratio: float
    high_density_regions: List[Dict]
    low_density_regions: List[Dict]

@dataclass
class SliceStrategy:
    """切片策略"""
    type: str  # fine_grain, balanced, coarse_grain
    slice_size: int
    overlap: int
    target_count_range: str
    adaptive_factors: Dict[str, Any]

@dataclass
class AdaptiveSliceInfo:
    """自适应切片信息"""
    slice_id: str
    filename: str
    row: int
    col: int
    x_offset: int
    y_offset: int
    width: int
    height: int
    slice_path: str
    content_density: float
    priority: str  # high, medium, low
    base64_data: Optional[str] = None

class AdaptiveSlicingEngine:
    """自适应切片引擎"""
    
    def __init__(self):
        self.min_frame_ratio = 0.7
        self.max_frame_ratio = 0.95
        self.grid_size = 64
        
    def adaptive_slice(self, image_path: str, output_dir: str = "temp_adaptive_slices") -> Dict[str, Any]:
        """基于图框和内容密度的自适应切片"""
        try:
            logger.info(f"🔄 开始自适应切片分析: {image_path}")
            
            # 1. 图框检测与边界提取
            frame_result = self._detect_drawing_frame(image_path)
            if frame_result["success"]:
                content_bounds = frame_result["frame_bounds"]
                logger.info(f"📐 检测到图框边界: {content_bounds['width']}x{content_bounds['height']}")
            else:
                logger.error(f"❌ 图框检测失败: {frame_result.get('error')}")
                return {"success": False, "error": "图框检测失败"}
                
            # 2. 内容密度分析
            density_map = self._analyze_content_density(image_path, content_bounds)
            logger.info(f"📊 内容密度分析完成: {density_map.density_ratio:.3f}")
            
            # 3. 动态切片策略
            slice_strategy = self._determine_slice_strategy(content_bounds, density_map)
            logger.info(f"🎯 切片策略: {slice_strategy.type}, 目标大小: {slice_strategy.slice_size}")
            
            # 4. 生成自适应切片
            slices = self._generate_adaptive_slices(
                image_path, content_bounds, slice_strategy, output_dir
            )
            
            logger.info(f"✅ 自适应切片完成: 生成 {len(slices)} 个切片")
            
            return {
                "success": True,
                "slice_count": len(slices),
                "slice_strategy": asdict(slice_strategy),
                "slices": [asdict(s) for s in slices],
                "frame_detected": frame_result["success"],
                "content_density": asdict(density_map),
                "adaptive_method": "frame_and_density_based"
            }
            
        except Exception as e:
            logger.error(f"❌ 自适应切片失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _detect_drawing_frame(self, image_path: str) -> Dict[str, Any]:
        """检测图纸图框边界"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "error": "无法读取图像"}
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            
            # 边缘检测 + 矩形轮廓查找
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 查找最大的矩形轮廓
            largest_rect = None
            max_area = 0
            
            for contour in contours:
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) == 4:
                    area = cv2.contourArea(contour)
                    total_area = width * height
                    area_ratio = area / total_area
                    
                    if (self.min_frame_ratio <= area_ratio <= self.max_frame_ratio and 
                        area > max_area):
                        max_area = area
                        largest_rect = approx
            
            if largest_rect is not None:
                x, y, w, h = cv2.boundingRect(largest_rect)
                frame_bounds = FrameBounds(
                    x=x, y=y, width=w, height=h,
                    confidence=0.85,
                    detection_method="contour_detection"
                )
                
                return {
                    "success": True,
                    "frame_bounds": asdict(frame_bounds),
                    "detection_method": "contour_detection"
                }
            
            # 降级: 使用全图作为图框
            fallback_bounds = FrameBounds(
                x=0, y=0, width=width, height=height,
                confidence=0.5,
                detection_method="full_image_fallback"
            )
            
            return {
                "success": True,
                "frame_bounds": asdict(fallback_bounds),
                "detection_method": "fallback"
            }
            
        except Exception as e:
            logger.error(f"❌ 图框检测失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_content_density(self, image_path: str, bounds: Dict) -> ContentDensity:
        """分析指定区域的内容密度"""
        try:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            
            x, y, w, h = bounds["x"], bounds["y"], bounds["width"], bounds["height"]
            roi = image[y:y+h, x:x+w]
            
            edges = cv2.Canny(roi, 50, 150)
            total_pixels = w * h
            content_pixels = np.count_nonzero(edges)
            overall_density = content_pixels / total_pixels
            
            # 网格密度分析
            high_density_regions = []
            low_density_regions = []
            
            grid_h = h // self.grid_size
            grid_w = w // self.grid_size
            
            for i in range(0, h, grid_h):
                for j in range(0, w, grid_w):
                    grid_roi = edges[i:i+grid_h, j:j+grid_w]
                    grid_density = np.count_nonzero(grid_roi) / (grid_h * grid_w)
                    
                    region_info = {
                        "x": x + j, "y": y + i,
                        "width": grid_w, "height": grid_h,
                        "density": grid_density
                    }
                    
                    if grid_density > overall_density * 1.5:
                        high_density_regions.append(region_info)
                    elif grid_density < overall_density * 0.5:
                        low_density_regions.append(region_info)
            
            return ContentDensity(
                total_area=total_pixels,
                content_area=content_pixels,
                density_ratio=overall_density,
                high_density_regions=high_density_regions,
                low_density_regions=low_density_regions
            )
            
        except Exception as e:
            logger.error(f"❌ 内容密度分析失败: {e}")
            return ContentDensity(
                total_area=bounds["width"] * bounds["height"],
                content_area=0,
                density_ratio=0.1,
                high_density_regions=[],
                low_density_regions=[]
            )
    
    def _determine_slice_strategy(self, bounds: Dict, density: ContentDensity) -> SliceStrategy:
        """根据图纸特征确定切片策略"""
        
        width = bounds["width"]
        height = bounds["height"]
        total_area = width * height
        density_ratio = density.density_ratio
        
        if total_area < 2048 * 2048:  # 小图纸
            return SliceStrategy(
                type="fine_grain",
                slice_size=512,
                overlap=64,
                target_count_range="6-12",
                adaptive_factors={
                    "area_factor": "small",
                    "density_factor": density_ratio,
                    "overlap_ratio": 0.125
                }
            )
        elif total_area > 8192 * 8192:  # 大图纸
            return SliceStrategy(
                type="coarse_grain", 
                slice_size=2048,
                overlap=256,
                target_count_range="16-32",
                adaptive_factors={
                    "area_factor": "large",
                    "density_factor": density_ratio,
                    "overlap_ratio": 0.125
                }
            )
        else:  # 中等图纸
            if density_ratio > 0.15:  # 高密度内容
                slice_size = 768
                overlap = 96
            else:  # 低密度内容
                slice_size = 1024
                overlap = 128
                
            return SliceStrategy(
                type="balanced",
                slice_size=slice_size,
                overlap=overlap,
                target_count_range="12-24",
                adaptive_factors={
                    "area_factor": "medium",
                    "density_factor": density_ratio,
                    "overlap_ratio": overlap / slice_size
                }
            )
    
    def _generate_adaptive_slices(self, image_path: str, bounds: Dict, strategy: SliceStrategy, 
                                output_dir: str) -> List[AdaptiveSliceInfo]:
        """生成自适应切片"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        image = Image.open(image_path)
        x, y, w, h = bounds["x"], bounds["y"], bounds["width"], bounds["height"]
        roi = image.crop((x, y, x + w, y + h))
        
        slices = []
        slice_size = strategy.slice_size
        overlap = strategy.overlap
        step = slice_size - overlap
        
        rows = max(1, (h - overlap) // step)
        cols = max(1, (w - overlap) // step)
        
        slice_id = 0
        for row in range(rows):
            for col in range(cols):
                slice_x = col * step
                slice_y = row * step
                
                slice_w = min(slice_size, w - slice_x)
                slice_h = min(slice_size, h - slice_y)
                
                if slice_w < slice_size // 2 or slice_h < slice_size // 2:
                    continue
                
                slice_img = roi.crop((slice_x, slice_y, slice_x + slice_w, slice_y + slice_h))
                
                filename = f"adaptive_slice_{row}_{col}.png"
                slice_path = os.path.join(output_dir, filename)
                slice_img.save(slice_path)
                
                # 计算切片内容密度
                slice_array = np.array(slice_img.convert('L'))
                edges = cv2.Canny(slice_array, 50, 150)
                content_density = np.count_nonzero(edges) / (slice_w * slice_h)
                
                # 确定优先级
                if content_density > 0.1:
                    priority = "high"
                elif content_density > 0.05:
                    priority = "medium"
                else:
                    priority = "low"
                
                slice_info = AdaptiveSliceInfo(
                    slice_id=f"adaptive_{slice_id}",
                    filename=filename,
                    row=row,
                    col=col,
                    x_offset=x + slice_x,
                    y_offset=y + slice_y,
                    width=slice_w,
                    height=slice_h,
                    slice_path=slice_path,
                    content_density=content_density,
                    priority=priority
                )
                
                slices.append(slice_info)
                slice_id += 1
        
        # 按优先级排序
        slices.sort(key=lambda s: (s.priority == "low", s.priority == "medium", s.priority == "high"))
        
        return slices 