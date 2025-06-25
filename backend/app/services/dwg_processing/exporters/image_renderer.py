#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像渲染器
专门负责DWG图纸的图像渲染
"""

import logging
import tempfile
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ImageRenderer:
    """图像渲染器类"""
    
    def __init__(self):
        """初始化图像渲染器"""
        self.output_format = 'PNG'
        self.default_dpi = 300
        self.default_size = (1920, 1080)
        
    def setup_matplotlib(self):
        """设置matplotlib环境"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # 非交互式后端
            import matplotlib.pyplot as plt
            
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['font.size'] = 10
            
            return plt
            
        except ImportError:
            logger.error("matplotlib库未安装")
            return None
        except Exception as e:
            logger.error(f"matplotlib设置失败: {e}")
            return None
    
    def render_frame_to_image(self, 
                             doc: Any, 
                             frame_bounds: Tuple[float, float, float, float],
                             output_path: str,
                             title: str = "") -> Dict[str, Any]:
        """
        渲染图框为图像
        
        Args:
            doc: DXF文档对象
            frame_bounds: 图框边界 (min_x, min_y, max_x, max_y)
            output_path: 输出路径
            title: 图像标题
            
        Returns:
            渲染结果
        """
        try:
            plt = self.setup_matplotlib()
            if not plt:
                return {'success': False, 'error': 'matplotlib不可用'}
            
            min_x, min_y, max_x, max_y = frame_bounds
            
            # 创建图形
            fig, ax = plt.subplots(1, 1, figsize=(12, 8))
            ax.set_xlim(min_x, max_x)
            ax.set_ylim(min_y, max_y)
            ax.set_aspect('equal')
            
            # 渲染实体
            entity_count = self._render_entities(doc, ax, frame_bounds)
            
            # 设置标题和标签
            if title:
                ax.set_title(title, fontsize=14, fontweight='bold')
            
            ax.set_xlabel('X (mm)', fontsize=10)
            ax.set_ylabel('Y (mm)', fontsize=10)
            ax.grid(True, alpha=0.3)
            
            # 保存图像
            plt.savefig(output_path, dpi=self.default_dpi, bbox_inches='tight')
            plt.close(fig)
            
            # 检查输出文件
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'entity_count': entity_count,
                    'file_size': file_size,
                    'dimensions': f"{max_x-min_x:.1f}×{max_y-min_y:.1f}mm"
                }
            else:
                return {'success': False, 'error': '图像文件生成失败'}
                
        except Exception as e:
            logger.error(f"图像渲染失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _render_entities(self, doc: Any, ax: Any, bounds: Tuple[float, float, float, float]) -> int:
        """
        渲染实体到坐标轴
        
        Args:
            doc: DXF文档
            ax: matplotlib坐标轴
            bounds: 渲染边界
            
        Returns:
            渲染的实体数量
        """
        try:
            count = 0
            min_x, min_y, max_x, max_y = bounds
            
            if not hasattr(doc, 'modelspace'):
                return 0
                
            modelspace = doc.modelspace()
            
            for entity in modelspace:
                try:
                    # 检查实体是否在边界内
                    if self._is_entity_in_bounds(entity, bounds):
                        self._render_single_entity(entity, ax)
                        count += 1
                        
                        # 限制渲染数量，防止过载
                        if count > 1000:
                            break
                            
                except Exception as entity_error:
                    # 单个实体渲染失败不影响整体
                    continue
            
            return count
            
        except Exception as e:
            logger.error(f"实体渲染失败: {e}")
            return 0
    
    def _render_single_entity(self, entity: Any, ax: Any):
        """渲染单个实体"""
        try:
            entity_type = entity.dxftype()
            
            if entity_type == 'LINE':
                self._render_line(entity, ax)
            elif entity_type == 'CIRCLE':
                self._render_circle(entity, ax)
            elif entity_type == 'ARC':
                self._render_arc(entity, ax)
            elif entity_type in ['LWPOLYLINE', 'POLYLINE']:
                self._render_polyline(entity, ax)
            elif entity_type == 'TEXT':
                self._render_text(entity, ax)
                
        except Exception as e:
            # 单个实体类型渲染失败，跳过
            pass
    
    def _render_line(self, entity: Any, ax: Any):
        """渲染直线"""
        try:
            start = entity.dxf.start
            end = entity.dxf.end
            ax.plot([start[0], end[0]], [start[1], end[1]], 'b-', linewidth=0.5)
        except:
            pass
    
    def _render_circle(self, entity: Any, ax: Any):
        """渲染圆"""
        try:
            import matplotlib.patches as patches
            center = entity.dxf.center
            radius = entity.dxf.radius
            circle = patches.Circle((center[0], center[1]), radius, 
                                  fill=False, edgecolor='blue', linewidth=0.5)
            ax.add_patch(circle)
        except:
            pass
    
    def _render_arc(self, entity: Any, ax: Any):
        """渲染圆弧"""
        try:
            import numpy as np
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_angle = np.radians(entity.dxf.start_angle)
            end_angle = np.radians(entity.dxf.end_angle)
            
            angles = np.linspace(start_angle, end_angle, 50)
            x = center[0] + radius * np.cos(angles)
            y = center[1] + radius * np.sin(angles)
            ax.plot(x, y, 'b-', linewidth=0.5)
        except:
            pass
    
    def _render_polyline(self, entity: Any, ax: Any):
        """渲染多段线"""
        try:
            points = list(entity.get_points())
            if len(points) >= 2:
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                ax.plot(x_coords, y_coords, 'b-', linewidth=0.5)
        except:
            pass
    
    def _render_text(self, entity: Any, ax: Any):
        """渲染文本"""
        try:
            insert = entity.dxf.insert
            text = entity.dxf.text
            height = getattr(entity.dxf, 'height', 10)
            ax.text(insert[0], insert[1], text, fontsize=max(6, height/10), 
                   color='red', alpha=0.7)
        except:
            pass
    
    def _is_entity_in_bounds(self, entity: Any, bounds: Tuple[float, float, float, float]) -> bool:
        """检查实体是否在边界内"""
        try:
            min_x, min_y, max_x, max_y = bounds
            
            # 获取实体边界框
            if hasattr(entity, 'get_points'):
                points = list(entity.get_points())
                if points:
                    entity_min_x = min(p[0] for p in points)
                    entity_max_x = max(p[0] for p in points)
                    entity_min_y = min(p[1] for p in points)
                    entity_max_y = max(p[1] for p in points)
                    
                    # 检查是否有重叠
                    return not (entity_max_x < min_x or entity_min_x > max_x or
                              entity_max_y < min_y or entity_min_y > max_y)
            
            return True  # 默认包含
            
        except:
            return True  # 出错时默认包含 

    def export_frame_to_pdf(self, doc: Any, frame_bounds: Tuple[float, float, float, float], output_path: str, title: str = "") -> dict:
        """
        导出图框为PDF
        Args:
            doc: DXF文档对象
            frame_bounds: 图框边界 (min_x, min_y, max_x, max_y)
            output_path: 输出PDF路径
            title: PDF标题
        Returns:
            导出结果
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            min_x, min_y, max_x, max_y = frame_bounds
            fig, ax = plt.subplots(1, 1, figsize=(8.27, 11.69))
            ax.set_xlim(min_x-100, max_x+100)
            ax.set_ylim(min_y-100, max_y+100)
            ax.set_aspect('equal')
            entity_count = 0
            if hasattr(doc, 'modelspace'):
                for entity in doc.modelspace():
                    try:
                        if entity.dxftype() == 'LINE':
                            start = entity.dxf.start
                            end = entity.dxf.end
                            ax.plot([start.x, end.x], [start.y, end.y], 'k-', linewidth=0.5)
                            entity_count += 1
                        if entity_count > 1000:
                            break
                    except Exception:
                        continue
            rect = patches.Rectangle((min_x, min_y), max_x-min_x, max_y-min_y, linewidth=2, edgecolor='red', facecolor='none')
            ax.add_patch(rect)
            if title:
                ax.set_title(title, fontsize=12)
            plt.savefig(output_path, dpi=300, bbox_inches='tight', format='pdf')
            plt.close(fig)
            if Path(output_path).exists():
                return {'success': True, 'output_path': output_path, 'entity_count': entity_count}
            else:
                return {'success': False, 'error': 'PDF文件生成失败'}
        except Exception as e:
            logger.error(f"PDF导出失败: {e}")
            return {'success': False, 'error': str(e)} 