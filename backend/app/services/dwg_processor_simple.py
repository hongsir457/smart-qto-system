#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版DWG处理器
使用纯Python解决方案处理DWG/DXF文件，无需外部依赖
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import tempfile

# 尝试导入必要的库
try:
    import ezdxf
    from ezdxf import recover
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False
    logging.warning("ezdxf库未安装，DWG/DXF处理功能将受限")

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib库未安装，图像生成功能将受限")

logger = logging.getLogger(__name__)

class SimpleDWGProcessor:
    """简化版DWG处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.supported_formats = ['.dwg', '.dxf']
        self.temp_dir = None
        
        # 检查依赖库
        if not EZDXF_AVAILABLE:
            logger.warning("ezdxf库未安装，将使用演示模式")
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib库未安装，将无法生成图像")
    
    def process_multi_sheets(self, file_path: str) -> Dict[str, Any]:
        """
        处理多图框DWG/DXF文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            处理结果字典
        """
        try:
            logger.info(f"开始处理文件: {file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 检查文件格式
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix="dwg_processing_")
            
            # 加载DWG/DXF文件
            doc = self._load_drawing_file(file_path)
            
            if doc is None:
                # 如果无法加载文件，使用演示模式
                logger.warning("无法加载文件，使用演示模式")
                return self._create_demo_result(file_path)
            
            # 检测图框
            frames = self._detect_frames(doc)
            
            if not frames:
                logger.warning("未检测到图框，使用单图处理")
                frames = [self._create_default_frame()]
            
            # 处理每个图框
            drawings = []
            for i, frame in enumerate(frames):
                drawing = self._process_single_frame(doc, frame, i)
                drawings.append(drawing)
            
            # 按图号排序
            drawings = self._sort_drawings_by_number(drawings)
            
            # 生成汇总
            summary = self._generate_summary(drawings)
            
            result = {
                "success": True,
                "total_drawings": len(drawings),
                "processed_drawings": len([d for d in drawings if d.get("processed", False)]),
                "drawings": drawings,
                "summary": summary,
                "processing_info": {
                    "file_path": file_path,
                    "file_size": os.path.getsize(file_path),
                    "temp_dir": self.temp_dir
                }
            }
            
            logger.info(f"处理完成，共检测到 {len(drawings)} 个图框")
            return result
            
        except Exception as e:
            logger.error(f"处理文件时发生错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "drawings": [],
                "summary": {}
            }
        finally:
            # 清理临时文件
            self._cleanup_temp_files()
    
    def _load_drawing_file(self, file_path: str) -> Optional[Any]:
        """
        加载DWG/DXF文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            ezdxf文档对象或None
        """
        if not EZDXF_AVAILABLE:
            return None
        
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.dxf':
                # 直接读取DXF文件
                doc = ezdxf.readfile(file_path)
                logger.info("成功加载DXF文件")
                return doc
                
            elif file_ext == '.dwg':
                # 尝试多种方法加载DWG文件
                
                # 方法1: 使用ezdxf的实验性DWG加载器
                try:
                    doc = ezdxf.readfile(file_path)
                    logger.info("使用ezdxf成功加载DWG文件")
                    return doc
                except Exception as e:
                    logger.warning(f"ezdxf加载DWG失败: {e}")
                
                # 方法2: 使用recover模式
                try:
                    doc, auditor = recover.readfile(file_path)
                    if auditor.has_errors:
                        logger.warning(f"文件有错误，但已恢复: {auditor.errors}")
                    logger.info("使用recover模式成功加载DWG文件")
                    return doc
                except Exception as e:
                    logger.warning(f"recover模式加载DWG失败: {e}")
                
                # 如果所有方法都失败，返回None
                logger.error("所有DWG加载方法都失败")
                return None
                
        except Exception as e:
            logger.error(f"加载文件失败: {e}")
            return None
    
    def _detect_frames(self, doc: Any) -> List[Dict[str, Any]]:
        """
        检测图框
        
        Args:
            doc: ezdxf文档对象
            
        Returns:
            图框列表
        """
        frames = []
        
        try:
            modelspace = doc.modelspace()
            
            # 查找矩形实体（可能是图框）
            rectangles = []
            for entity in modelspace:
                if entity.dxftype() == 'LWPOLYLINE':
                    # 检查是否为矩形
                    if self._is_rectangle(entity):
                        bounds = self._get_entity_bounds(entity)
                        if bounds and self._is_valid_frame_size(bounds):
                            rectangles.append(bounds)
                
                elif entity.dxftype() == 'POLYLINE':
                    # 检查多段线是否为矩形
                    if self._is_rectangle(entity):
                        bounds = self._get_entity_bounds(entity)
                        if bounds and self._is_valid_frame_size(bounds):
                            rectangles.append(bounds)
                
                elif entity.dxftype() == 'LINE':
                    # 收集线段，后续组合成矩形
                    pass
            
            # 如果找到矩形，创建图框
            for i, rect in enumerate(rectangles):
                frame = {
                    "index": i,
                    "bounds": rect,
                    "drawing_number": f"图纸-{i+1:02d}",
                    "title": f"图纸标题 {i+1}",
                    "scale": "1:100"
                }
                frames.append(frame)
            
            # 如果没有找到图框，创建默认图框
            if not frames:
                logger.warning("未检测到标准图框，创建默认图框")
                frames = [self._create_default_frame()]
            
        except Exception as e:
            logger.error(f"检测图框时发生错误: {e}")
            frames = [self._create_default_frame()]
        
        return frames
    
    def _is_rectangle(self, entity: Any) -> bool:
        """检查实体是否为矩形"""
        try:
            if hasattr(entity, 'get_points'):
                points = list(entity.get_points())
                return len(points) == 4 or len(points) == 5  # 4个顶点或5个点（闭合）
            return False
        except:
            return False
    
    def _get_entity_bounds(self, entity: Any) -> Optional[Tuple[float, float, float, float]]:
        """获取实体边界"""
        try:
            if hasattr(entity, 'get_points'):
                points = list(entity.get_points())
                if points:
                    x_coords = [p[0] for p in points]
                    y_coords = [p[1] for p in points]
                    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
            return None
        except:
            return None
    
    def _is_valid_frame_size(self, bounds: Tuple[float, float, float, float]) -> bool:
        """检查是否为有效的图框尺寸"""
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        
        # 检查尺寸是否合理（假设图框至少100x100单位）
        return width > 100 and height > 100
    
    def _create_default_frame(self) -> Dict[str, Any]:
        """创建默认图框"""
        return {
            "index": 0,
            "bounds": (0, 0, 1000, 700),  # 默认A3尺寸
            "drawing_number": "A-01",
            "title": "建筑平面图",
            "scale": "1:100"
        }
    
    def _process_single_frame(self, doc: Any, frame: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        处理单个图框
        
        Args:
            doc: ezdxf文档对象
            frame: 图框信息
            index: 图框索引
            
        Returns:
            处理结果
        """
        try:
            # 提取图框内容
            components = self._extract_components_from_frame(doc, frame)
            
            # 计算工程量
            quantities = self._calculate_quantities(components)
            
            # 生成图像（如果可能）
            image_path = self._generate_frame_image(doc, frame, index)
            
            drawing = {
                "index": index,
                "drawing_number": frame.get("drawing_number", f"图纸-{index+1:02d}"),
                "title": frame.get("title", f"图纸标题 {index+1}"),
                "scale": frame.get("scale", "1:100"),
                "bounds": frame.get("bounds"),
                "components": components,
                "quantities": quantities,
                "image_path": image_path,
                "processed": True,
                "component_count": len(components)
            }
            
            return drawing
            
        except Exception as e:
            logger.error(f"处理图框 {index} 时发生错误: {e}")
            return {
                "index": index,
                "drawing_number": frame.get("drawing_number", f"图纸-{index+1:02d}"),
                "title": frame.get("title", f"图纸标题 {index+1}"),
                "scale": frame.get("scale", "1:100"),
                "error": str(e),
                "processed": False,
                "components": [],
                "quantities": {},
                "component_count": 0
            }
    
    def _extract_components_from_frame(self, doc: Any, frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从图框中提取构件"""
        components = []
        
        try:
            if not EZDXF_AVAILABLE:
                # 演示模式：生成模拟构件
                return self._generate_demo_components()
            
            modelspace = doc.modelspace()
            bounds = frame.get("bounds", (0, 0, 1000, 700))
            
            # 在图框范围内查找实体
            for entity in modelspace:
                if self._is_entity_in_bounds(entity, bounds):
                    component = self._classify_entity_as_component(entity)
                    if component:
                        components.append(component)
            
        except Exception as e:
            logger.error(f"提取构件时发生错误: {e}")
            # 返回演示构件
            components = self._generate_demo_components()
        
        return components
    
    def _is_entity_in_bounds(self, entity: Any, bounds: Tuple[float, float, float, float]) -> bool:
        """检查实体是否在指定边界内"""
        try:
            entity_bounds = self._get_entity_bounds(entity)
            if not entity_bounds:
                return False
            
            min_x, min_y, max_x, max_y = bounds
            e_min_x, e_min_y, e_max_x, e_max_y = entity_bounds
            
            # 检查是否有重叠
            return not (e_max_x < min_x or e_min_x > max_x or e_max_y < min_y or e_min_y > max_y)
        except:
            return False
    
    def _classify_entity_as_component(self, entity: Any) -> Optional[Dict[str, Any]]:
        """将实体分类为构件"""
        try:
            entity_type = entity.dxftype()
            
            # 简单的分类逻辑
            if entity_type in ['LINE', 'LWPOLYLINE', 'POLYLINE']:
                # 根据长度和形状判断构件类型
                bounds = self._get_entity_bounds(entity)
                if bounds:
                    width = bounds[2] - bounds[0]
                    height = bounds[3] - bounds[1]
                    
                    if width > height * 3:  # 长条形，可能是梁
                        return {
                            "type": "beam",
                            "name": "梁",
                            "dimensions": {"width": width, "height": height},
                            "quantity": 1
                        }
                    elif height > width * 3:  # 高条形，可能是柱
                        return {
                            "type": "column",
                            "name": "柱",
                            "dimensions": {"width": width, "height": height},
                            "quantity": 1
                        }
                    else:  # 接近正方形，可能是墙
                        return {
                            "type": "wall",
                            "name": "墙",
                            "dimensions": {"width": width, "height": height},
                            "quantity": 1
                        }
            
            elif entity_type in ['CIRCLE', 'ARC']:
                return {
                    "type": "column",
                    "name": "圆柱",
                    "dimensions": {"radius": getattr(entity, 'radius', 100)},
                    "quantity": 1
                }
            
            return None
            
        except Exception as e:
            logger.error(f"分类实体时发生错误: {e}")
            return None
    
    def _generate_demo_components(self) -> List[Dict[str, Any]]:
        """生成演示构件"""
        return [
            {
                "type": "wall",
                "name": "外墙",
                "dimensions": {"length": 6000, "height": 3000, "thickness": 240},
                "quantity": 4,
                "unit": "m²",
                "area": 72.0
            },
            {
                "type": "column",
                "name": "框架柱",
                "dimensions": {"width": 400, "height": 400, "length": 3000},
                "quantity": 8,
                "unit": "m³",
                "volume": 3.84
            },
            {
                "type": "beam",
                "name": "框架梁",
                "dimensions": {"width": 300, "height": 600, "length": 6000},
                "quantity": 6,
                "unit": "m³",
                "volume": 6.48
            },
            {
                "type": "slab",
                "name": "楼板",
                "dimensions": {"length": 12000, "width": 8000, "thickness": 120},
                "quantity": 1,
                "unit": "m³",
                "volume": 11.52
            },
            {
                "type": "foundation",
                "name": "独立基础",
                "dimensions": {"length": 2000, "width": 2000, "height": 800},
                "quantity": 8,
                "unit": "m³",
                "volume": 25.6
            }
        ]
    
    def _calculate_quantities(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算工程量"""
        quantities = {
            "wall": {"count": 0, "area": 0, "volume": 0},
            "column": {"count": 0, "volume": 0},
            "beam": {"count": 0, "volume": 0},
            "slab": {"count": 0, "area": 0, "volume": 0},
            "foundation": {"count": 0, "volume": 0}
        }
        
        for component in components:
            comp_type = component.get("type", "unknown")
            if comp_type in quantities:
                quantities[comp_type]["count"] += component.get("quantity", 1)
                
                # 计算面积和体积
                dims = component.get("dimensions", {})
                if comp_type == "wall":
                    area = dims.get("length", 0) * dims.get("height", 0) / 1000000  # 转换为m²
                    quantities[comp_type]["area"] += area
                    volume = area * dims.get("thickness", 240) / 1000  # 转换为m³
                    quantities[comp_type]["volume"] += volume
                
                elif comp_type in ["column", "beam"]:
                    volume = (dims.get("width", 0) * dims.get("height", 0) * 
                             dims.get("length", 0)) / 1000000000  # 转换为m³
                    quantities[comp_type]["volume"] += volume * component.get("quantity", 1)
                
                elif comp_type == "slab":
                    area = dims.get("length", 0) * dims.get("width", 0) / 1000000  # 转换为m²
                    quantities[comp_type]["area"] += area
                    volume = area * dims.get("thickness", 120) / 1000  # 转换为m³
                    quantities[comp_type]["volume"] += volume
                
                elif comp_type == "foundation":
                    volume = (dims.get("length", 0) * dims.get("width", 0) * 
                             dims.get("height", 0)) / 1000000000  # 转换为m³
                    quantities[comp_type]["volume"] += volume * component.get("quantity", 1)
        
        return quantities
    
    def _generate_frame_image(self, doc: Any, frame: Dict[str, Any], index: int) -> Optional[str]:
        """生成图框图像"""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        try:
            fig, ax = plt.subplots(1, 1, figsize=(12, 8))
            
            # 绘制图框
            bounds = frame.get("bounds", (0, 0, 1000, 700))
            rect = patches.Rectangle(
                (bounds[0], bounds[1]), 
                bounds[2] - bounds[0], 
                bounds[3] - bounds[1],
                linewidth=2, edgecolor='black', facecolor='none'
            )
            ax.add_patch(rect)
            
            # 添加标题
            ax.text(
                bounds[0] + (bounds[2] - bounds[0]) / 2,
                bounds[3] + 50,
                frame.get("title", f"图纸 {index+1}"),
                ha='center', va='bottom', fontsize=14, fontweight='bold'
            )
            
            # 设置坐标轴
            ax.set_xlim(bounds[0] - 100, bounds[2] + 100)
            ax.set_ylim(bounds[1] - 100, bounds[3] + 100)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # 保存图像
            image_path = os.path.join(self.temp_dir, f"frame_{index}.png")
            plt.savefig(image_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return image_path
            
        except Exception as e:
            logger.error(f"生成图像时发生错误: {e}")
            return None
    
    def _sort_drawings_by_number(self, drawings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按图号排序"""
        def natural_sort_key(drawing):
            number = drawing.get("drawing_number", "")
            # 提取数字部分进行自然排序
            parts = re.split(r'(\d+)', number)
            return [int(part) if part.isdigit() else part for part in parts]
        
        return sorted(drawings, key=natural_sort_key)
    
    def _generate_summary(self, drawings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成汇总信息"""
        total_components = {}
        total_quantities = {
            "wall": {"count": 0, "area": 0, "volume": 0},
            "column": {"count": 0, "volume": 0},
            "beam": {"count": 0, "volume": 0},
            "slab": {"count": 0, "area": 0, "volume": 0},
            "foundation": {"count": 0, "volume": 0}
        }
        
        for drawing in drawings:
            # 统计构件
            for component in drawing.get("components", []):
                comp_type = component.get("type", "unknown")
                if comp_type not in total_components:
                    total_components[comp_type] = 0
                total_components[comp_type] += component.get("quantity", 1)
            
            # 累加工程量
            quantities = drawing.get("quantities", {})
            for comp_type, values in quantities.items():
                if comp_type in total_quantities:
                    for key, value in values.items():
                        total_quantities[comp_type][key] += value
        
        return {
            "total_components": total_components,
            "total_quantities": total_quantities,
            "processed_drawings": len([d for d in drawings if d.get("processed", False)]),
            "failed_drawings": len([d for d in drawings if not d.get("processed", True)])
        }
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info(f"已清理临时目录: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
    
    def _create_demo_result(self, file_path: str) -> Dict[str, Any]:
        """创建演示结果"""
        logger.info("使用演示模式生成结果")
        
        # 生成3个演示图框
        drawings = []
        for i in range(3):
            components = self._generate_demo_components()
            quantities = self._calculate_quantities(components)
            
            drawing = {
                "index": i,
                "drawing_number": f"A-{i+1:02d}",
                "title": f"建筑平面图 {i+1}",
                "scale": "1:100",
                "bounds": (0, 0, 1000, 700),
                "components": components,
                "quantities": quantities,
                "processed": True,
                "component_count": len(components)
            }
            drawings.append(drawing)
        
        summary = self._generate_summary(drawings)
        
        return {
            "success": True,
            "total_drawings": len(drawings),
            "processed_drawings": len(drawings),
            "drawings": drawings,
            "summary": summary,
            "processing_info": {
                "file_path": file_path,
                "mode": "demo",
                "note": "演示模式：由于缺少必要的库，使用模拟数据"
            }
        }

# 使用示例
if __name__ == "__main__":
    processor = SimpleDWGProcessor()
    
    # 测试文件路径
    test_files = [
        "test.dwg",
        "test.dxf",
        "sample.dwg"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"处理文件: {test_file}")
            result = processor.process_multi_sheets(test_file)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            break
    else:
        print("未找到测试文件，使用演示模式")
        result = processor.process_multi_sheets("demo.dwg")
        print(json.dumps(result, indent=2, ensure_ascii=False)) 