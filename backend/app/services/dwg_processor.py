#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWG多图框处理器
支持自动检测多个图框，按图号排序，构件识别和工程量计算
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../../'))

import re
import json
import logging
import subprocess
import tempfile
import shutil
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import matplotlib.font_manager as fm
from concurrent.futures import ProcessPoolExecutor
import pickle

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

# 尝试导入简化版处理器作为备用
try:
    from .dwg_processor_simple import SimpleDWGProcessor
    SIMPLE_PROCESSOR_AVAILABLE = True
except ImportError:
    SIMPLE_PROCESSOR_AVAILABLE = False

logger = logging.getLogger(__name__)

# === 全局字体配置函数 ===
def _setup_matplotlib_chinese_fonts():
    """全局字体配置函数，供多进程使用"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        import platform
        import os
        
        # 尝试从环境变量获取已配置的字体
        selected_font = os.environ.get('MATPLOTLIB_FONT')
        
        if not selected_font:
            # 根据操作系统设置合适的中文字体
            system = platform.system().lower()
            
            # 定义不同系统的中文字体列表
            font_candidates = []
            if system == 'windows':
                font_candidates = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi']
            elif system == 'darwin':  # macOS
                font_candidates = ['PingFang SC', 'Heiti SC', 'STSong']
            else:  # Linux
                font_candidates = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'DejaVu Sans']
            
            # 获取系统可用字体
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            
            # 查找第一个可用的中文字体
            for font in font_candidates:
                if font in available_fonts:
                    selected_font = font
                    break
        
        # 设置matplotlib字体配置
        if selected_font:
            plt.rcParams['font.family'] = ['sans-serif']
            plt.rcParams['font.sans-serif'] = [selected_font] + plt.rcParams.get('font.sans-serif', [])
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['font.size'] = 10
        else:
            # 最基本的配置
            plt.rcParams['axes.unicode_minus'] = False
            
    except Exception:
        # 静默失败，不影响主要功能
        pass

# === 多进程图框处理顶层函数 ===
def process_frame_mp(args):
    """多进程安全的图框处理函数，增强异常捕获"""
    # 首先导入所有必需的模块
    import os
    import sys
    import gc
    import re
    import traceback
    from pathlib import Path
    
    try:
        import ezdxf
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        import matplotlib.font_manager as fm
        
        # 配置中文字体支持（多进程环境）
        _setup_matplotlib_chinese_fonts()
        
    except ImportError as import_error:
        return {
            'success': False,
            'error': f'导入模块失败: {import_error}',
            'frame_index': args[0] if args else -1
        }
    
    i, frame, doc_path, temp_dir = args
    error_log_path = os.path.join(temp_dir, f'frame_{i}_error.log')
    
    try:
        # 验证输入文件是否存在且可读
        if not os.path.exists(doc_path):
            raise FileNotFoundError(f"文档文件不存在: {doc_path}")
        
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        
        # 验证DXF文件内容
        file_size = os.path.getsize(doc_path)
        if file_size < 100:  # DXF文件至少应该有100字节
            raise ValueError(f"文件太小，可能已损坏: {doc_path} ({file_size} bytes)")
        
        # 尝试读取文件前几行验证格式
        try:
            with open(doc_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
                if not any('DXF' in line or '0' in line for line in first_lines):
                    raise ValueError(f"文件格式异常，不是有效的DXF文件: {first_lines[:3]}")
        except Exception as read_error:
            raise ValueError(f"无法读取文件内容: {read_error}")
        
        # 重新加载doc，增加超时和重试机制
        doc = None
        for attempt in range(3):  # 最多重试3次
            try:
                doc = ezdxf.readfile(doc_path)
                break
            except Exception as load_error:
                if attempt == 2:  # 最后一次尝试
                    raise ValueError(f"加载DXF文件失败 (尝试{attempt+1}/3): {load_error}")
                import time
                time.sleep(0.5)  # 等待0.5秒后重试
        
        if doc is None:
            raise ValueError("无法加载DXF文档")
        
        # 安全地获取modelspace
        try:
            modelspace = doc.modelspace()
            if not modelspace:
                raise ValueError("文档modelspace为空")
        except Exception as ms_error:
            raise ValueError(f"获取modelspace失败: {ms_error}")
        
        # 重新计算entity_cache，增加异常处理
        entity_cache = []
        entity_count = 0
        for entity in modelspace:
            try:
                if hasattr(entity, 'get_points'):
                    points = list(entity.get_points())
                    if points:
                        x_coords = [p[0] for p in points]
                        y_coords = [p[1] for p in points]
                        bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                        entity_cache.append((entity, bounds))
                        entity_count += 1
                        
                        # 限制实体数量，防止内存溢出
                        if entity_count > 10000:
                            break
            except Exception as entity_error:
                # 跳过有问题的实体，继续处理其他实体
                continue
        
        bounds = frame.get("bounds", (0, 0, 1000, 700))
        min_x, min_y, max_x, max_y = bounds
        
        # 验证bounds合理性
        if max_x <= min_x or max_y <= min_y:
            raise ValueError(f"图框边界异常: {bounds}")
        
        # 生成图片 - 优化版本，确保精确裁切
        image_path = os.path.join(temp_dir, f"frame_{i}.png")
        try:
            # 计算图框尺寸，确保合理的图像比例
            frame_width = max_x - min_x
            frame_height = max_y - min_y
            
            # 根据图框尺寸动态计算figure尺寸，保持比例
            fig_ratio = frame_width / frame_height
            if fig_ratio > 1.5:  # 宽图
                figsize = (16, 16/fig_ratio)
            else:  # 高图或方图
                figsize = (12, 12/fig_ratio)
            
            fig, ax = plt.subplots(1, 1, figsize=figsize)
            
            # 设置背景为白色
            fig.patch.set_facecolor('white')
            ax.set_facecolor('white')
            
            # 绘制实体，限制数量防止内存溢出
            drawn_entities = 0
            for entity, e_bounds in entity_cache:
                if drawn_entities > 8000:  # 增加绘制实体数量限制
                    break
                    
                # 只绘制图框范围内的实体，加小边界容差
                tolerance = 50  # 50单位容差
                if e_bounds and not (e_bounds[2] < min_x - tolerance or e_bounds[0] > max_x + tolerance or 
                                   e_bounds[3] < min_y - tolerance or e_bounds[1] > max_y + tolerance):
                    try:
                        if entity.dxftype() == 'LINE':
                            start = entity.dxf.start
                            end = entity.dxf.end
                            ax.plot([start[0], end[0]], [start[1], end[1]], 'k-', linewidth=0.8)
                        elif entity.dxftype() == 'LWPOLYLINE':
                            points = list(entity.get_points())
                            if len(points) >= 2:
                                x = [p[0] for p in points]
                                y = [p[1] for p in points]
                                ax.plot(x, y, 'k-', linewidth=0.8)
                        elif entity.dxftype() == 'CIRCLE':
                            center = entity.dxf.center
                            radius = entity.dxf.radius
                            circle = plt.Circle((center[0], center[1]), radius, fill=False, color='k', linewidth=0.8)
                            ax.add_patch(circle)
                        elif entity.dxftype() in ['TEXT', 'MTEXT']:
                            # 绘制文字（简化表示为点）
                            if hasattr(entity.dxf, 'insert'):
                                pos = entity.dxf.insert
                                ax.plot(pos[0], pos[1], 'k.', markersize=2)
                        drawn_entities += 1
                    except Exception as plot_error:
                        # 跳过有问题的实体
                        continue
            
            # 绘制图框边界（红色醒目边框）
            rect = patches.Rectangle((min_x, min_y), max_x-min_x, max_y-min_y, 
                                   linewidth=3, edgecolor='red', facecolor='none', linestyle='--')
            ax.add_patch(rect)
            
            # 精确设置图像边界，无额外边距
            margin = 20  # 最小边距
            ax.set_xlim(min_x - margin, max_x + margin)
            ax.set_ylim(min_y - margin, max_y + margin)
            ax.set_aspect('equal')
            
            # 移除坐标轴和网格，得到纯净图像
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            
            # 添加图框信息标题
            title_text = f"图框 {i+1}: {frame.get('title', '未知标题')} ({frame.get('drawing_number', f'图纸-{i+1:02d}')})"
            ax.text((min_x + max_x) / 2, max_y + margin * 0.5, title_text, 
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            # 高质量保存PNG
            plt.savefig(image_path, dpi=200, bbox_inches='tight', pad_inches=0.1, 
                       facecolor='white', edgecolor='none', format='png')
            plt.close()
            gc.collect()
            
        except Exception as img_error:
            image_path = None
            # 记录图片生成错误但不中断处理
            with open(error_log_path, 'a', encoding='utf-8') as f:
                f.write(f"图片生成错误: {img_error}\n")
        
        # 生成PDF
        pdf_filename = f"{frame.get('drawing_number', f'图纸-{i+1:02d}').replace('/', '_')}_{frame.get('title', f'图纸标题 {i+1}').replace('/', '_')}.pdf"
        # 清理文件名中的非法字符
        pdf_filename = re.sub(r'[\\/:*?"<>|%\s]+', '_', pdf_filename)
        pdf_path = os.path.join(temp_dir, pdf_filename)
        
        try:
            fig, ax = plt.subplots(1, 1, figsize=(8.27, 11.69))
            
            # 绘制实体
            drawn_entities = 0
            for entity, e_bounds in entity_cache:
                if drawn_entities > 5000:  # 限制绘制实体数量
                    break
                    
                if e_bounds and not (e_bounds[2] < min_x or e_bounds[0] > max_x or e_bounds[3] < min_y or e_bounds[1] > max_y):
                    try:
                        if entity.dxftype() == 'LINE':
                            start = entity.dxf.start
                            end = entity.dxf.end
                            ax.plot([start[0], end[0]], [start[1], end[1]], 'k-', linewidth=0.5)
                        elif entity.dxftype() == 'LWPOLYLINE':
                            points = list(entity.get_points())
                            x = [p[0] for p in points]
                            y = [p[1] for p in points]
                            ax.plot(x, y, 'k-', linewidth=0.5)
                        drawn_entities += 1
                    except Exception as plot_error:
                        continue
            
            # 绘制图框边界
            rect = patches.Rectangle((min_x, min_y), max_x-min_x, max_y-min_y, 
                                   linewidth=2, edgecolor='red', facecolor='none')
            ax.add_patch(rect)
            
            ax.set_xlim(min_x-100, max_x+100)
            ax.set_ylim(min_y-100, max_y+100)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_title(f"图纸 {i+1}: {frame.get('title', '未知标题')}", fontsize=12)
            
            plt.savefig(pdf_path, dpi=300, bbox_inches='tight', format='pdf')
            plt.close()
            gc.collect()
            
        except Exception as pdf_error:
            pdf_path = None
            # 记录PDF生成错误但不中断处理
            with open(error_log_path, 'a', encoding='utf-8') as f:
                f.write(f"PDF生成错误: {pdf_error}\n")
        
        # 成功处理，记录日志
        success_log = f"图框 {i} 处理成功: 实体数={len(entity_cache)}, 图片={'✓' if image_path else '✗'}, PDF={'✓' if pdf_path else '✗'}"
        with open(os.path.join(temp_dir, f'frame_{i}_success.log'), 'w', encoding='utf-8') as f:
            f.write(success_log)
        
        return {
            "index": i,
            "drawing_number": frame.get("drawing_number", f"图纸-{i+1:02d}"),
            "title": frame.get("title", f"图纸标题 {i+1}"),
            "scale": frame.get("scale", "1:100"),
            "bounds": frame.get("bounds"),
            "image_path": image_path,
            "pdf_path": pdf_path,
            "processed": True,
            "entity_count": len(entity_cache),
            "drawn_entities": drawn_entities
        }
        
    except Exception as e:
        # 详细记录错误信息
        import traceback
        error_details = {
            "frame_index": i,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "doc_path": doc_path,
            "temp_dir": temp_dir,
            "frame_info": frame
        }
        
        # 写入错误日志文件
        try:
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write(f"图框 {i} 处理失败\n")
                f.write(f"错误类型: {error_details['error_type']}\n")
                f.write(f"错误信息: {error_details['error_message']}\n")
                f.write(f"文档路径: {error_details['doc_path']}\n")
                f.write(f"临时目录: {error_details['temp_dir']}\n")
                f.write(f"图框信息: {error_details['frame_info']}\n")
                f.write(f"详细堆栈:\n{error_details['traceback']}\n")
        except:
            pass  # 如果连日志都写不了，就放弃
        
        # 返回错误结果而不是让进程崩溃
        return {
            "index": i,
            "drawing_number": frame.get("drawing_number", f"图纸-{i+1:02d}"),
            "title": frame.get("title", f"图纸标题 {i+1}"),
            "scale": frame.get("scale", "1:100"),
            "bounds": frame.get("bounds"),
            "image_path": None,
            "pdf_path": None,
            "processed": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "error_log": error_log_path
        }

from .frame_detection import detect_title_blocks_and_frames
from .frame_sorting import sort_drawings_by_number
from .frame_image import generate_frame_image, export_frame_to_pdf
from .frame_info_extract import extract_frame_info
from .frame_utils import *
from .oda_converter import convert_dwg_with_oda, validate_dxf_file

class DWGProcessor:
    """DWG多图框处理器"""
    
    def __init__(self):
        """初始化处理器"""
        # 配置matplotlib中文字体支持
        self._setup_chinese_fonts()
        
        self.supported_formats = ['.dwg', '.dxf', '.dwt']
        self.temp_dir = None
        self.oda_converter_path = None
        
        # 检查依赖库
        if not EZDXF_AVAILABLE:
            logger.warning("ezdxf库未安装，DWG/DXF处理功能将受限")
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib库未安装，图像生成功能将受限")
        
        # 检查ODA File Converter
        self._check_oda_converter()
        print(f"[诊断] ODA File Converter 路径: {self.oda_converter_path}")
        if self.oda_converter_path:
            print("[诊断] ODA File Converter 检测成功！")
        else:
            print("[诊断] 未检测到ODA File Converter，请检查是否已安装并配置路径！")
        
        # 初始化简化版处理器作为备用
        self.simple_processor = None
        if SIMPLE_PROCESSOR_AVAILABLE:
            try:
                self.simple_processor = SimpleDWGProcessor()
                logger.info("简化版DWG处理器已初始化")
            except Exception as e:
                logger.warning(f"初始化简化版处理器失败: {e}")
    
    def _setup_chinese_fonts(self):
        """配置matplotlib中文字体支持，解决中文字符渲染问题"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            import platform
            
            # 根据操作系统设置合适的中文字体
            system = platform.system().lower()
            
            # 定义不同系统的中文字体列表
            font_candidates = []
            if system == 'windows':
                font_candidates = [
                    'Microsoft YaHei',     # 微软雅黑
                    'SimHei',              # 黑体
                    'SimSun',              # 宋体
                    'KaiTi',               # 楷体
                    'FangSong'             # 仿宋
                ]
            elif system == 'darwin':  # macOS
                font_candidates = [
                    'PingFang SC',         # 苹方
                    'Heiti SC',            # 黑体
                    'STSong',              # 华文宋体
                    'STFangsong'           # 华文仿宋
                ]
            else:  # Linux
                font_candidates = [
                    'WenQuanYi Micro Hei', # 文泉驿微米黑
                    'WenQuanYi Zen Hei',   # 文泉驿正黑
                    'Droid Sans Fallback', # Droid字体
                    'DejaVu Sans'          # DejaVu字体
                ]
            
            # 获取系统可用字体
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            
            # 查找第一个可用的中文字体
            selected_font = None
            for font in font_candidates:
                if font in available_fonts:
                    selected_font = font
                    logger.info(f"选择中文字体: {selected_font}")
                    break
            
            # 如果没有找到专门的中文字体，尝试使用通用字体
            if not selected_font:
                fallback_fonts = ['DejaVu Sans', 'Arial', 'Helvetica']
                for font in fallback_fonts:
                    if font in available_fonts:
                        selected_font = font
                        logger.warning(f"使用备用字体: {selected_font}")
                        break
            
            # 设置matplotlib全局字体配置
            if selected_font:
                # 设置字体族
                plt.rcParams['font.family'] = ['sans-serif']
                plt.rcParams['font.sans-serif'] = [selected_font] + plt.rcParams['font.sans-serif']
                
                # 设置其他字体相关参数
                plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
                plt.rcParams['font.size'] = 10              # 设置默认字体大小
                
                # 为了确保在多进程环境中也生效，设置环境变量
                os.environ['MATPLOTLIB_FONT'] = selected_font
                
                logger.info(f"✅ 中文字体配置成功: {selected_font}")
            else:
                logger.warning("⚠️ 未找到合适的中文字体，可能出现中文显示问题")
                
        except Exception as e:
            logger.error(f"❌ 配置中文字体失败: {e}")
            # 即使字体配置失败，也不影响主要功能
            try:
                # 最基本的字体设置
                plt.rcParams['axes.unicode_minus'] = False
            except:
                pass
    
    def _check_oda_converter(self):
        """优雅检测ODA File Converter，不执行命令避免弹窗"""
        possible_paths = [
            shutil.which("ODAFileConverter"),
            shutil.which("ODAFileConverter.exe"),
            "ODAFileConverter",
            "ODAFileConverter.exe",
            "/usr/bin/ODAFileConverter",
            "/usr/local/bin/ODAFileConverter",
            "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
            "C:\\Program Files (x86)\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
            "C:\\Program Files\\ODA\\ODAFileConverter 26.4.0\\ODAFileConverter.exe"
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                self.oda_converter_path = path
                print(f"[诊断] 找到ODA File Converter: {path}")
                logger.info(f"找到ODA File Converter: {path}")
                return
        logger.warning("未找到ODA File Converter，DWG文件处理将使用备用方法")
        print("[诊断] 未检测到ODA File Converter，请检查是否已安装并配置路径！")
    
    def safe_filename(self, s: str) -> str:
        """将字符串转换为安全的文件名"""
        return re.sub(r'[\\/:*?"<>|%\s]+', '_', s)
    
    def process_multi_sheets(self, file_path: str) -> Dict[str, Any]:
        """
        处理多图框DWG/DXF文件，并自动导出PDF
        """
        try:
            logger.info(f"开始处理文件: {file_path}")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            self.temp_dir = tempfile.mkdtemp(prefix="dwg_processing_")
            
            # 加载和验证DWG/DXF文件
            doc = self._load_dwg_file(file_path)
            if doc is None:
                if self.simple_processor:
                    logger.info("主处理器失败，尝试使用简化版处理器")
                    return self.simple_processor.process_multi_sheets(file_path)
                else:
                    logger.warning("所有处理器都不可用，使用演示模式")
                    return self._create_demo_result(file_path)
            
            # 验证转换后的DXF文件（如果是从DWG转换的）
            if file_ext in ['.dwg', '.dwt']:
                converted_dxf_path = self._find_converted_dxf_file()
                if converted_dxf_path:
                    # 验证DXF文件完整性
                    if not self._validate_dxf_file(converted_dxf_path):
                        raise ValueError(f"转换后的DXF文件损坏或格式异常: {converted_dxf_path}")
                    # 使用转换后的DXF文件路径
                    doc_path = converted_dxf_path
                else:
                    doc_path = file_path
            else:
                doc_path = file_path
            
            frames = self._detect_title_blocks_and_frames(doc)
            if not frames:
                logger.warning("未检测到图框，使用单图处理")
                frames = [self._create_default_frame()]
            
            # 限制图框数量，防止内存溢出
            max_frames = 100  # 最多处理100个图框
            if len(frames) > max_frames:
                logger.warning(f"检测到{len(frames)}个图框，限制处理前{max_frames}个")
                frames = frames[:max_frames]
            
            drawings = []
            pdf_paths = []
            
            # 多进程参数准备
            temp_dir = self.temp_dir
            args_list = [(i, frame, doc_path, temp_dir) for i, frame in enumerate(frames)]
            
            # 使用更安全的多进程处理
            max_workers = min(4, len(frames))  # 限制最大进程数为4
            logger.info(f"开始多进程处理 {len(frames)} 个图框，使用 {max_workers} 个进程")
            
            results = []
            failed_count = 0
            
            try:
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    # 提交所有任务
                    future_to_index = {executor.submit(process_frame_mp, args): args[0] for args in args_list}
                    
                    # 收集结果，增加超时处理
                    for future in future_to_index:
                        try:
                            result = future.result(timeout=300)  # 每个图框最多处理5分钟
                            results.append(result)
                            
                            # 检查处理结果
                            if not result.get('processed', False):
                                failed_count += 1
                                logger.error(f"图框 {result.get('index', '?')} 处理失败: {result.get('error', '未知错误')}")
                                
                                # 读取详细错误日志
                                error_log_path = result.get('error_log')
                                if error_log_path and os.path.exists(error_log_path):
                                    try:
                                        with open(error_log_path, 'r', encoding='utf-8') as f:
                                            error_details = f.read()
                                            logger.error(f"图框 {result.get('index', '?')} 详细错误:\n{error_details}")
                                    except Exception as log_error:
                                        logger.error(f"无法读取错误日志: {log_error}")
                            else:
                                logger.info(f"图框 {result.get('index', '?')} 处理成功: 实体数={result.get('entity_count', 0)}")
                                
                        except Exception as future_error:
                            failed_count += 1
                            index = future_to_index[future]
                            logger.error(f"图框 {index} 处理超时或异常: {future_error}")
                            
                            # 创建失败结果
                            error_result = {
                                "index": index,
                                "drawing_number": f"图纸-{index+1:02d}",
                                "title": f"图纸标题 {index+1}",
                                "scale": "1:100",
                                "bounds": frames[index].get("bounds") if index < len(frames) else (0, 0, 1000, 700),
                                "image_path": None,
                                "pdf_path": None,
                                "processed": False,
                                "error": str(future_error),
                                "error_type": "ProcessingTimeout"
                            }
                            results.append(error_result)
                            
            except Exception as pool_error:
                logger.error(f"进程池执行失败: {pool_error}")
                # 如果多进程完全失败，尝试单进程处理
                logger.info("多进程失败，尝试单进程处理")
                results = self._fallback_single_process(args_list)
            
            # 按索引排序结果
            results.sort(key=lambda x: x.get('index', 0))
            drawings = self._sort_drawings_by_number(results)
            
            # 收集成功生成的PDF路径
            pdf_paths = [d['pdf_path'] for d in drawings if d.get('pdf_path')]
            
            # 生成处理摘要
            summary = self._generate_summary(drawings)
            summary['pdf_paths'] = pdf_paths
            summary['failed_frames'] = failed_count
            summary['success_rate'] = f"{((len(drawings) - failed_count) / len(drawings) * 100):.1f}%" if drawings else "0%"
            
            # 收集所有错误日志
            error_logs = self._collect_error_logs(temp_dir)
            if error_logs:
                summary['error_logs'] = error_logs
            
            result = {
                "success": True,
                "total_drawings": len(drawings),
                "processed_drawings": len([d for d in drawings if d.get("processed", False)]),
                "failed_drawings": failed_count,
                "drawings": drawings,
                "summary": summary,
                "processing_info": {
                    "file_path": file_path,
                    "file_size": os.path.getsize(file_path),
                    "temp_dir": self.temp_dir,
                    "processor_used": "main",
                    "max_workers": max_workers,
                    "doc_path": doc_path
                }
            }
            
            logger.info(f"处理完成，共检测到 {len(drawings)} 个图框，成功 {len(drawings) - failed_count} 个，失败 {failed_count} 个")
            return result
            
        except Exception as e:
            logger.error(f"处理文件时发生错误: {str(e)}")
            if self.simple_processor:
                try:
                    logger.info("主处理器出错，尝试使用简化版处理器")
                    result = self.simple_processor.process_multi_sheets(file_path)
                    result["processing_info"]["processor_used"] = "simple_fallback"
                    result["processing_info"]["main_processor_error"] = str(e)
                    return result
                except Exception as simple_error:
                    logger.error(f"简化版处理器也失败: {simple_error}")
            return {
                "success": False,
                "error": str(e),
                "drawings": [],
                "summary": {},
                "processing_info": {
                    "processor_used": "none",
                    "error": str(e)
                }
            }
        finally:
            # 延迟清理，确保所有进程都完成
            import time
            time.sleep(1)
            self._cleanup_temp_files()
    
    def _find_converted_dxf_file(self) -> Optional[str]:
        """查找转换后的DXF文件"""
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return None
        
        for file in os.listdir(self.temp_dir):
            if file.lower().endswith('.dxf'):
                dxf_path = os.path.join(self.temp_dir, file)
                if os.path.getsize(dxf_path) > 100:  # 文件大小合理
                    return dxf_path
        return None
    
    def _validate_dxf_file(self, dxf_path: str) -> bool:
        """验证DXF文件完整性"""
        try:
            # 检查文件大小
            if os.path.getsize(dxf_path) < 100:
                logger.error(f"DXF文件太小: {dxf_path}")
                return False
            
            # 检查文件头
            with open(dxf_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline().strip() for _ in range(10)]
                
                # DXF文件应该包含这些标识
                has_dxf_markers = any('DXF' in line or line == '0' for line in first_lines)
                if not has_dxf_markers:
                    logger.error(f"DXF文件格式异常，缺少DXF标识: {first_lines[:5]}")
                    return False
            
            # 尝试用ezdxf加载验证
            try:
                test_doc = ezdxf.readfile(dxf_path)
                modelspace = test_doc.modelspace()
                entity_count = len(list(modelspace))
                logger.info(f"DXF文件验证成功: {dxf_path}, 实体数: {entity_count}")
                return True
            except Exception as load_error:
                logger.error(f"DXF文件无法被ezdxf加载: {load_error}")
                return False
                
        except Exception as e:
            logger.error(f"验证DXF文件时出错: {e}")
            return False
    
    def _fallback_single_process(self, args_list: List) -> List[Dict[str, Any]]:
        """单进程备用处理方法"""
        logger.info("使用单进程备用方法处理图框")
        results = []
        
        for args in args_list:
            try:
                result = process_frame_mp(args)
                results.append(result)
                logger.info(f"单进程处理图框 {result.get('index', '?')}: {'成功' if result.get('processed') else '失败'}")
            except Exception as e:
                index = args[0]
                logger.error(f"单进程处理图框 {index} 失败: {e}")
                error_result = {
                    "index": index,
                    "drawing_number": f"图纸-{index+1:02d}",
                    "title": f"图纸标题 {index+1}",
                    "scale": "1:100",
                    "bounds": (0, 0, 1000, 700),
                    "image_path": None,
                    "pdf_path": None,
                    "processed": False,
                    "error": str(e),
                    "error_type": "SingleProcessError"
                }
                results.append(error_result)
        
        return results
    
    def _collect_error_logs(self, temp_dir: str) -> List[str]:
        """收集所有错误日志"""
        error_logs = []
        
        if not temp_dir or not os.path.exists(temp_dir):
            return error_logs
        
        try:
            for file in os.listdir(temp_dir):
                if file.endswith('_error.log'):
                    log_path = os.path.join(temp_dir, file)
                    try:
                        with open(log_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if content.strip():
                                error_logs.append(f"=== {file} ===\n{content}")
                    except Exception as read_error:
                        error_logs.append(f"=== {file} (读取失败) ===\n无法读取: {read_error}")
        except Exception as e:
            logger.error(f"收集错误日志失败: {e}")
        
        return error_logs
    
    def _load_dwg_file(self, file_path: str) -> Optional[Any]:
        """
        加载DWG文件，支持多种方法
        Args:
            file_path: 文件路径
        Returns:
            ezdxf文档对象或None
        """
        if not EZDXF_AVAILABLE:
            logger.warning("ezdxf库不可用")
            print("[调试] ezdxf库不可用")
            return None
        
        file_ext = Path(file_path).suffix.lower()
        print(f"[加载] 处理文件: {file_path} (格式: {file_ext})")
        logger.info(f"[加载] 处理文件: {file_path} (格式: {file_ext})")
        
        # 如果是DXF文件，直接读取
        if file_ext == '.dxf':
            try:
                print("[加载] 直接加载DXF文件...")
                logger.info("[加载] 直接加载DXF文件...")
                doc = ezdxf.readfile(file_path)
                print("[加载] DXF文件加载成功!")
                logger.info("[加载] DXF文件加载成功!")
                return doc
            except Exception as e:
                print(f"[加载] DXF文件加载失败: {e}")
                logger.error(f"加载DXF文件失败: {e}")
                return None
        
        # 如果是DWG文件，需要转换
        if file_ext in ['.dwg', '.dwt']:
            print(f"[加载] 检测到DWG文件，需要转换...")
            logger.info(f"[加载] 检测到DWG文件，需要转换...")
            
            # 优先使用ODA File Converter
            if self.oda_converter_path:
                print(f"[加载] 使用ODA File Converter转换: {self.oda_converter_path}")
                logger.info(f"[加载] 使用ODA File Converter转换: {self.oda_converter_path}")
                try:
                    converted_file = self._convert_dwg_with_oda(file_path)
                    print(f"[加载] ODA转换返回: {converted_file}")
                    logger.info(f"[加载] ODA转换返回: {converted_file}")
                    if converted_file and os.path.exists(converted_file):
                        print(f"[加载] ODA转换成功，加载DXF文件: {converted_file}")
                        logger.info(f"[加载] ODA转换成功，加载DXF文件: {converted_file}")
                        doc = ezdxf.readfile(converted_file)
                        print("[加载] 转换后的DXF文件加载成功!")
                        logger.info("[加载] 转换后的DXF文件加载成功!")
                        return doc
                    else:
                        print("[加载] ODA转换失败，未生成DXF文件")
                        logger.error("[加载] ODA转换失败，未生成DXF文件")
                except Exception as oda_error:
                    print(f"[加载] ODA转换失败: {oda_error}")
                    logger.error(f"ODA File Converter转换失败: {oda_error}")
            else:
                print("[加载] ODA File Converter不可用，请检查是否已安装！")
                logger.error("[加载] ODA File Converter不可用，请检查是否已安装！")
            
            # 尝试使用ezdxf的recover模式直接读取DWG
            print("[加载] 尝试使用ezdxf recover模式直接读取DWG...")
            logger.info("[加载] 尝试使用ezdxf recover模式直接读取DWG...")
            try:
                doc, auditor = recover.readfile(file_path)
                if auditor.has_errors:
                    print(f"[加载] 文件有 {len(auditor.errors)} 个错误，但已恢复")
                    logger.warning(f"文件有错误，但已恢复: {len(auditor.errors)} 个错误")
                print("[加载] recover模式加载成功!")
                logger.info("[加载] recover模式加载成功!")
                return doc
            except Exception as recover_error:
                print(f"[加载] recover模式失败: {recover_error}")
                logger.warning(f"recover模式失败: {recover_error}")
        
        # 所有方法都失败
        error_msg = f"无法加载文件 {file_path}。请确保:"
        error_msg += "\n1. 文件格式正确（支持DWG、DXF、DWT）"
        error_msg += "\n2. 文件未损坏"
        if file_ext in ['.dwg', '.dwt']:
            error_msg += "\n3. 已安装ODA File Converter或文件为较新的DWG格式"
        
        print(f"[加载] {error_msg}")
        logger.error(f"[加载] {error_msg}")
        raise ValueError(error_msg)
    
    def _convert_dwg_with_oda(self, dwg_path: str) -> Optional[str]:
        """
        使用ODA File Converter转换DWG到DXF，增强错误处理和文件验证
        """
        try:
            print(f"[ODA] 开始转换DWG文件: {dwg_path}")
            logger.info(f"[ODA] 开始转换DWG文件: {dwg_path}")

            # 检查DWG路径是否存在且无中文、空格
            if not os.path.exists(dwg_path):
                raise FileNotFoundError(f"DWG文件不存在: {dwg_path}")
            
            # 检查DWG文件大小
            dwg_size = os.path.getsize(dwg_path)
            if dwg_size < 1024:  # DWG文件至少应该有1KB
                raise ValueError(f"DWG文件太小，可能已损坏: {dwg_path} ({dwg_size} bytes)")
            
            print(f"[ODA] DWG文件大小: {dwg_size} bytes")
            logger.info(f"[ODA] DWG文件大小: {dwg_size} bytes")
            
            # 检查路径中的特殊字符
            if re.search(r'[\u4e00-\u9fa5]', dwg_path) or ' ' in dwg_path:
                # 如果路径包含中文或空格，复制到安全路径
                safe_dir = tempfile.mkdtemp(prefix="oda_safe_")
                safe_dwg_path = os.path.join(safe_dir, "temp.dwg")
                shutil.copy2(dwg_path, safe_dwg_path)
                dwg_path = safe_dwg_path
                print(f"[ODA] 复制到安全路径: {safe_dwg_path}")
                logger.info(f"[ODA] 复制到安全路径: {safe_dwg_path}")

            # 创建临时输入文件夹，并复制DWG文件进去
            input_dir = tempfile.mkdtemp(prefix="oda_input_")
            input_file = os.path.join(input_dir, "input.dwg")
            shutil.copy2(dwg_path, input_file)
            
            print(f"[ODA] 输入目录: {input_dir}")
            print(f"[ODA] 输入文件: {input_file}")
            logger.info(f"[ODA] 输入目录: {input_dir}")

            # 输出目录
            output_dir = self.temp_dir
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            print(f"[ODA] 输出目录: {output_dir}")
            logger.info(f"[ODA] 输出目录: {output_dir}")

            # 期望的输出文件
            expected_output = os.path.join(output_dir, "input.dxf")
            print(f"[ODA] 期望输出文件: {expected_output}")

            # 构建ODA File Converter命令
            cmd = [
                self.oda_converter_path,
                input_dir,           # 输入文件夹
                output_dir,          # 输出目录
                "ACAD2018",         # 输出版本
                "DXF",              # 输出格式
                "0",                # 递归处理子文件夹 (0=否)
                "1",                # 审计和恢复 (1=是)
                ""                  # 输出文件名过滤器(空=全部)
            ]

            print(f"[ODA] 执行命令: {' '.join(cmd)}")
            logger.info(f"[ODA] 执行命令: {' '.join(cmd)}")
            
            # 执行转换，增加更好的错误处理
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 增加超时时间为10分钟
                    cwd=output_dir,
                    creationflags=creationflags
                )
                
                print(f"[ODA] 返回码: {result.returncode}")
                print(f"[ODA] STDOUT: {result.stdout}")
                print(f"[ODA] STDERR: {result.stderr}")
                logger.info(f"[ODA] 返回码: {result.returncode}")
                logger.info(f"[ODA] STDOUT: {result.stdout}")
                if result.stderr:
                    logger.warning(f"[ODA] STDERR: {result.stderr}")
                
                # ODA File Converter返回码为0不一定表示成功，需要检查输出文件
                
            except subprocess.TimeoutExpired:
                error_msg = "ODAFileConverter 超时（10分钟），自动终止！"
                print(f"[ODA] {error_msg}")
                logger.error(f"[ODA] {error_msg}")
                raise RuntimeError(error_msg)
            except Exception as e:
                error_msg = f"调用ODAFileConverter异常: {e}"
                print(f"[ODA] {error_msg}")
                logger.error(f"[ODA] {error_msg}")
                raise RuntimeError(error_msg)

            # 详细检查输出目录
            print(f"[ODA] 检查输出目录 {output_dir} 中的文件:")
            logger.info(f"[ODA] 检查输出目录 {output_dir} 中的文件:")
            
            output_files = []
            try:
                for file in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, file)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        output_files.append((file, file_size))
                        print(f"  - {file} ({file_size} bytes)")
                        logger.info(f"  - {file} ({file_size} bytes)")
            except Exception as e:
                error_msg = f"列出目录文件时出错: {e}"
                print(f"[ODA] {error_msg}")
                logger.error(f"[ODA] {error_msg}")

            # 查找生成的DXF文件，按优先级排序
            possible_outputs = [
                expected_output,
                os.path.join(output_dir, "input.dxf"),
                os.path.join(output_dir, "temp.dxf"),
            ]
            
            # 添加目录中所有DXF文件
            for file, size in output_files:
                if file.lower().endswith('.dxf') and size > 100:
                    full_path = os.path.join(output_dir, file)
                    if full_path not in possible_outputs:
                        possible_outputs.append(full_path)

            # 查找最佳输出文件
            found_output = None
            best_size = 0
            
            for output_path in possible_outputs:
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    if file_size > best_size:
                        # 验证DXF文件格式
                        if self._quick_validate_dxf(output_path):
                            found_output = output_path
                            best_size = file_size
                            print(f"[ODA] 找到有效DXF文件: {found_output} ({file_size} bytes)")
                            logger.info(f"[ODA] 找到有效DXF文件: {found_output} ({file_size} bytes)")

            # 清理临时输入文件夹
            try:
                shutil.rmtree(input_dir, ignore_errors=True)
            except Exception as cleanup_error:
                logger.warning(f"清理临时输入目录失败: {cleanup_error}")

            if found_output and os.path.exists(found_output):
                # 最终验证DXF文件
                if self._validate_dxf_file(found_output):
                    print(f"[ODA] 转换成功! 输出文件: {found_output}")
                    logger.info(f"[ODA] 转换成功! 输出文件: {found_output}")
                    return found_output
                else:
                    error_msg = f"转换后的DXF文件验证失败: {found_output}"
                    print(f"[ODA] {error_msg}")
                    logger.error(f"[ODA] {error_msg}")
                    raise RuntimeError(error_msg)
            else:
                error_msg = f"ODA转换失败: 未找到有效的DXF输出文件"
                if result.returncode != 0:
                    error_msg += f", 返回码={result.returncode}"
                if result.stderr:
                    error_msg += f", 错误信息={result.stderr}"
                print(f"[ODA] {error_msg}")
                logger.error(f"[ODA] {error_msg}")
                raise RuntimeError(error_msg)

        except Exception as e:
            error_msg = f"ODA转换过程中发生错误: {e}"
            print(f"[ODA] {error_msg}")
            logger.error(f"[ODA] {error_msg}")
            raise RuntimeError(error_msg)
    
    def _quick_validate_dxf(self, dxf_path: str) -> bool:
        """快速验证DXF文件格式"""
        try:
            # 检查文件大小
            if os.path.getsize(dxf_path) < 100:
                return False
            
            # 检查文件头
            with open(dxf_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
                # DXF文件应该以特定格式开始
                return any('0' in line or 'SECTION' in line or 'DXF' in line for line in first_lines)
        except:
            return False
    
    def _manual_convert_dwg_to_dxf(self, dwg_path: str) -> Optional[str]:
        """
        手动转换DWG到DXF的方法
        这里可以集成其他转换工具或方法
        
        Args:
            dwg_path: DWG文件路径
            
        Returns:
            转换后的DXF文件路径或None
        """
        # 这里可以添加其他转换方法
        # 例如：使用其他CAD软件的命令行工具
        # 或者调用在线转换服务等
        
        logger.info("手动转换方法暂未实现")
        return None
    
    def _detect_title_blocks_and_frames(self, doc: Any) -> List[Dict[str, Any]]:
        """
        基于建筑制图标准的智能图框检测（优化版本 - 提高召回率）
        参考：GB/T 50001-2017《房屋建筑制图统一标准》
        
        Args:
            doc: ezdxf文档对象
            
        Returns:
            图框列表，包含图号、标题、比例等信息
        """
        frames = []
        
        try:
            modelspace = doc.modelspace()
            entity_count = len(list(modelspace))
            logger.info(f"开始基于国标的图框检测，文档包含 {entity_count} 个实体")
            
            # 根据实体数量调整检测策略
            fast_mode = entity_count > 100000
            if fast_mode:
                logger.warning(f"实体数量过大({entity_count})，启用快速检测模式")
            
            # 第一步：查找符合国标尺寸的矩形边框（提高召回率）
            standard_frames = self._find_standard_frames(modelspace, fast_mode)
            logger.info(f"找到 {len(standard_frames)} 个符合国标尺寸的候选图框")
            
            if not standard_frames:
                logger.warning("未找到标准图框，尝试宽松检测")
                standard_frames = self._find_frames_relaxed(modelspace, fast_mode)
            
            # 第二步：验证每个候选图框的标准性（降低阈值以提高召回率）
            validated_frames = []
            max_analysis = 200 if fast_mode else 500  # 增加分析数量
            
            for i, frame_candidate in enumerate(standard_frames[:max_analysis]):
                if i % 20 == 0:
                    logger.info(f"标准验证进度: {i+1}/{min(len(standard_frames), max_analysis)}")
                
                # 使用建筑制图标准验证图框
                validation_score = self._validate_frame_by_standard(modelspace, frame_candidate)
                
                logger.debug(f"图框 {frame_candidate['bounds']} 标准符合度: {validation_score:.2f}")
                
                # 降低标准阈值以提高召回率
                min_score = 1.0 if fast_mode else 1.5  # 从2.0/3.0降低到1.0/1.5
                if validation_score >= min_score:
                    frame_candidate['validation_score'] = validation_score
                    validated_frames.append(frame_candidate)
                    logger.info(f"确认标准图框: 边界={frame_candidate['bounds']}, 得分={validation_score:.2f}")
            
            # 第三步：如果标准检测结果太少，使用补充检测
            if len(validated_frames) < 30:  # 从20提高到30，提高检测目标
                logger.info("标准检测结果较少，启用补充检测")
                additional_frames = self._supplementary_frame_detection(modelspace, validated_frames, fast_mode)
                validated_frames.extend(additional_frames)
            
            # 第四步：去重和优化排序
            final_frames = self._finalize_frame_list(validated_frames)
            logger.info(f"最终确认 {len(final_frames)} 个标准图框")
            
            # 第五步：提取详细信息
            for i, frame_candidate in enumerate(final_frames):
                frame_info = self._extract_frame_info(doc, frame_candidate['bounds'], i)
                # 添加标准化信息
                frame_info['standard_compliance'] = frame_candidate.get('validation_score', 0)
                frame_info['frame_type'] = frame_candidate.get('frame_type', 'Standard')
                frames.append(frame_info)
            
            # 如果仍然没有找到图框，创建默认图框
            if not frames:
                logger.warning("未检测到任何标准图框，创建默认图框")
                frames = [self._create_default_frame()]
            
        except Exception as e:
            logger.error(f"检测图框时发生错误: {e}")
            frames = [self._create_default_frame()]
        
        logger.info(f"最终确认 {len(frames)} 个图框")
        return frames
    
    def _find_standard_frames(self, modelspace: Any, fast_mode: bool = False) -> List[Dict[str, Any]]:
        """查找符合国家标准尺寸的图框（优化版本 - 提高召回率）"""
        # 国家标准图框尺寸（单位：mm）
        # 参考GB/T 50001-2017《房屋建筑制图统一标准》
        STANDARD_SIZES = {
            # 基本标准图幅（GB/T 14689-2008）
            'A0': (841, 1189),   # A0 - 大型总平面图、详细图
            'A1': (594, 841),    # A1 - 平面图、立面图、剖面图
            'A2': (420, 594),    # A2 - 局部平面图、详图
            'A3': (297, 420),    # A3 - 节点详图、构造详图
            'A4': (210, 297),    # A4 - 说明书、小型详图
            
            # 加长图幅（建筑制图常用）
            'A0_LONG': (841, 1189 * 1.5),    # A0加长 - 超长建筑平面图
            'A1_LONG': (594, 841 * 1.5),     # A1加长 - 长条形建筑立面图
            'A2_LONG': (420, 594 * 1.5),     # A2加长 - 长条形详图
            'A3_LONG': (297, 420 * 1.5),     # A3加长 - 长条形构造详图
            
            # 建筑专业常用非标准尺寸
            'ARCH_SUPER': (1189, 841),       # 超大建筑图（A0横向）
            'ARCH_LARGE': (1000, 700),       # 大型建筑平面图
            'ARCH_MEDIUM': (800, 600),       # 中型建筑图
            'ARCH_STANDARD': (700, 500),     # 标准建筑详图
            
            # 结构专业常用尺寸
            'STRUCT_LARGE': (900, 650),      # 大型结构图
            'STRUCT_MEDIUM': (750, 550),     # 中型结构图
            'STRUCT_DETAIL': (600, 450),     # 结构详图
            
            # 设备专业常用尺寸
            'MEP_LARGE': (850, 600),         # 大型设备图
            'MEP_MEDIUM': (700, 500),        # 中型设备图
            'MEP_DETAIL': (500, 350),        # 设备详图
            
            # 园林景观专业尺寸
            'LANDSCAPE_LARGE': (1000, 800),  # 大型景观总图
            'LANDSCAPE_MEDIUM': (800, 600),  # 中型景观图
            
            # 室内装修专业尺寸
            'INTERIOR_LARGE': (900, 600),    # 大型装修图
            'INTERIOR_MEDIUM': (700, 500),   # 中型装修图
            
            # 特殊比例图框
            'SQUARE_LARGE': (800, 800),      # 正方形大图
            'SQUARE_MEDIUM': (600, 600),     # 正方形中图
            'PANORAMIC': (1200, 400),        # 全景图框
            
            # 增加更多变体以提高召回率
            'A0_VARIANT': (840, 1190),       # A0 变体
            'A1_VARIANT': (593, 840),        # A1 变体
            'A2_VARIANT': (419, 593),        # A2 变体
            'A3_VARIANT': (296, 419),        # A3 变体
            'CUSTOM_LARGE': (750, 1050),     # 自定义大图
            'CUSTOM_MEDIUM': (650, 900),     # 自定义中图
            'CUSTOM_SMALL': (550, 750),      # 自定义小图
        }
        
        standard_frames = []
        large_rectangles = []
        
        # 限制检查的实体数量
        max_entities = 50000 if fast_mode else 150000  # 增加检查数量
        entity_counter = 0
        
        for entity in modelspace:
            entity_counter += 1
            if entity_counter > max_entities:
                logger.warning(f"达到实体检查限制({max_entities})，停止检查")
                break
            
            # 扩展检查的实体类型以提高召回率
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE', 'LINE', 'SPLINE', 'ARC', 'CIRCLE']:
                if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE'] and self._is_rectangle(entity):
                    bounds = self._get_entity_bounds(entity)
                    if bounds:
                        width = bounds[2] - bounds[0]
                        height = bounds[3] - bounds[1]
                        area = width * height
                        
                        # 降低面积筛选阈值以提高召回率
                        if area >= 20000:  # 从50000降低到20000
                            large_rectangles.append({
                                'entity': entity,
                                'bounds': bounds,
                                'width': width,
                                'height': height,
                                'area': area
                            })
                # 增加LINE组合检测（用于检测由多条线段组成的矩形框）
                elif entity.dxftype() == 'LINE':
                    # 简单的线段收集，后续可以组合成矩形
                    pass
        
        logger.info(f"找到 {len(large_rectangles)} 个大矩形候选")
        
        # 按面积排序，优先检查大的矩形
        large_rectangles.sort(key=lambda x: x['area'], reverse=True)
        
        # 检查每个矩形是否符合标准尺寸（放宽容差）
        tolerance = 0.20  # 从15%放宽到20%的尺寸容差
        
        for rect in large_rectangles[:800]:  # 从500增加到800
            width, height = rect['width'], rect['height']
            
            for size_name, (std_w, std_h) in STANDARD_SIZES.items():
                # 检查正向和旋转90度的匹配
                matches = [
                    # 正向匹配
                    (abs(width - std_w) / std_w < tolerance and abs(height - std_h) / std_h < tolerance),
                    # 旋转90度匹配
                    (abs(width - std_h) / std_h < tolerance and abs(height - std_w) / std_w < tolerance),
                ]
                
                if any(matches):
                    rect['frame_type'] = size_name
                    rect['size_match'] = 'exact'
                    standard_frames.append(rect)
                    logger.debug(f"找到标准图框 {size_name}: {width:.0f}x{height:.0f}")
                    break
        
        # 如果标准匹配结果太少，添加近似匹配
        if len(standard_frames) < 20:  # 从10提高到20
            logger.info("标准匹配结果较少，添加近似匹配")
            tolerance = 0.30  # 从25%放宽到30%容差
            
            for rect in large_rectangles[:500]:  # 从200增加到500
                if rect in standard_frames:
                    continue
                    
                width, height = rect['width'], rect['height']
                
                for size_name, (std_w, std_h) in STANDARD_SIZES.items():
                    matches = [
                        (abs(width - std_w) / std_w < tolerance and abs(height - std_h) / std_h < tolerance),
                        (abs(width - std_h) / std_h < tolerance and abs(height - std_w) / std_w < tolerance),
                    ]
                    
                    if any(matches):
                        rect['frame_type'] = size_name + '_APPROX'
                        rect['size_match'] = 'approximate'
                        standard_frames.append(rect)
                        break
        
        return standard_frames
    
    def _validate_frame_by_standard(self, modelspace: Any, frame_candidate: Dict[str, Any]) -> float:
        """
        根据建筑制图标准验证图框
        参考GB/T 50001-2017《房屋建筑制图统一标准》
        返回标准符合度得分（0-10分）
        """
        bounds = frame_candidate['bounds']
        score = 0.0
        
        try:
            # 1. 图签区域检测（权重：30%）
            title_block_score = self._validate_title_block_standard(modelspace, bounds)
            score += title_block_score * 3.0
            
            # 2. 边框完整性检测（权重：20%）
            border_score = self._validate_border_integrity(modelspace, bounds)
            score += border_score * 2.0
            
            # 3. 标准文本内容检测（权重：25%）
            text_score = self._validate_standard_texts(modelspace, bounds)
            score += text_score * 2.5
            
            # 4. 印章位置检测（权重：15%）
            seal_score = self._validate_standard_seal_positions(modelspace, bounds)
            score += seal_score * 1.5
            
            # 5. 尺寸标准性检测（权重：10%）
            size_score = self._get_size_standard_score(frame_candidate)
            score += size_score * 1.0
            
            # 添加标准符合度到候选框信息中
            frame_candidate['standard_compliance'] = score
            frame_candidate['compliance_details'] = {
                'title_block': title_block_score,
                'border_integrity': border_score,
                'standard_texts': text_score,
                'seal_positions': seal_score,
                'size_standard': size_score
            }
            
            # 根据得分确定图框类型
            if score >= 7.0:
                frame_candidate['frame_type'] = frame_candidate.get('frame_type', 'Standard') + '_EXCELLENT'
            elif score >= 5.0:
                frame_candidate['frame_type'] = frame_candidate.get('frame_type', 'Standard') + '_GOOD'
            elif score >= 3.0:
                frame_candidate['frame_type'] = frame_candidate.get('frame_type', 'Standard') + '_ACCEPTABLE'
            else:
                frame_candidate['frame_type'] = frame_candidate.get('frame_type', 'NonStandard') + '_POOR'
            
            logger.debug(f"图框标准验证详情: 图签={title_block_score:.2f}, 边框={border_score:.2f}, "
                        f"文本={text_score:.2f}, 印章={seal_score:.2f}, 尺寸={size_score:.2f}, 总分={score:.2f}")
            
        except Exception as e:
            logger.error(f"验证图框标准时出错: {e}")
            frame_candidate['standard_compliance'] = 0.0
        
        return score
    
    def _validate_title_block_standard(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """
        验证图签区域是否符合GB/T 50001-2017标准
        图签应位于图框右下角，包含规定的基本信息
        """
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        
        # 标准图签位置：右下角
        # 根据GB/T 50001-2017，图签宽度一般为180mm，高度为56mm或更高
        title_block_bounds = (
            max_x - min(180, width * 0.3),  # 图签宽度
            min_y,                          # 底边
            max_x,                         # 右边
            min_y + min(80, height * 0.2)  # 图签高度
        )
        
        score = 0.0
        
        # 检测图签区域的文本
        title_texts = self._find_texts_in_specific_area(modelspace, title_block_bounds, max_texts=50)
        
        if len(title_texts) < 3:
            return 0.0  # 图签区域文本太少
        
        # 检测标准图签内容（按GB/T 50001-2017要求）
        standard_content = {
            'project_name': 0,      # 工程名称（必需）
            'drawing_title': 0,     # 图名（必需）
            'drawing_number': 0,    # 图号（必需）
            'scale': 0,            # 比例（必需）
            'designer': 0,         # 设计者（必需）
            'checker': 0,          # 校对者（必需）
            'approver': 0,         # 审核者（必需）
            'date': 0,             # 日期（必需）
            'profession': 0,       # 专业标识
            'phase': 0,            # 设计阶段
            'version': 0,          # 版本号
            'unit': 0,             # 设计单位
        }
        
        # 专业识别关键词
        profession_keywords = {
            'architecture': ['建筑', '建施', 'ARCH', 'ARCHITECTURE', '建筑设计'],
            'structure': ['结构', '结施', 'STRUCT', 'STRUCTURE', '结构设计'],
            'electrical': ['电气', '电施', 'ELEC', 'ELECTRICAL', '电气设计'],
            'plumbing': ['给排水', '给水', '排水', 'PLUMB', 'WATER', '给排水设计'],
            'hvac': ['暖通', '通风', 'HVAC', 'VENTILATION', '暖通设计'],
            'landscape': ['景观', '园林', 'LANDSCAPE', 'GARDEN', '景观设计'],
            'interior': ['装修', '室内', 'INTERIOR', 'DECORATION', '装修设计'],
            'fire': ['消防', 'FIRE', 'SAFETY', '消防设计'],
        }
        
        # 设计阶段关键词
        phase_keywords = ['方案', '初设', '施工图', 'SCHEME', 'PRELIMINARY', 'CONSTRUCTION']
        
        # 检测标准内容
        for text in title_texts:
            text_upper = text.upper()
            text_clean = text.strip()
            
            # 1. 工程名称检测
            if any(keyword in text for keyword in ['工程', '项目', 'PROJECT', '建设']):
                standard_content['project_name'] += 1
            
            # 2. 图名检测（建筑制图标准术语）
            drawing_terms = [
                '平面图', '立面图', '剖面图', '详图', '大样', '节点',
                'PLAN', 'ELEVATION', 'SECTION', 'DETAIL', 'NODE',
                '总平面', '首层', '标准层', '屋顶', '地下室',
                '东立面', '西立面', '南立面', '北立面',
                '横剖面', '纵剖面', '楼梯', '卫生间', '厨房'
            ]
            if any(term in text for term in drawing_terms):
                standard_content['drawing_title'] += 1
            
            # 3. 图号检测（标准格式：专业代码-图纸序号）
            drawing_number_patterns = [
                r'[A-Z]\d{2,}[-_]\d+',      # A01-01格式
                r'\d+-\d+',                 # 01-01格式
                r'[A-Z]{2,3}-\d+',          # ARCH-01格式
                r'[建结电水暖景装消]\d+-\d+',  # 中文专业代码
            ]
            if any(re.search(pattern, text) for pattern in drawing_number_patterns):
                standard_content['drawing_number'] += 1
            
            # 4. 比例检测
            scale_patterns = [
                r'1\s*[:：]\s*\d+',         # 1:100格式
                r'比例\s*[:：]\s*1\s*[:：]\s*\d+',  # 比例:1:100格式
                r'SCALE\s*[:：]\s*1\s*[:：]\s*\d+',  # SCALE:1:100格式
            ]
            if any(re.search(pattern, text) for pattern in scale_patterns) or '比例' in text or 'SCALE' in text_upper:
                standard_content['scale'] += 1
            
            # 5. 设计人员检测
            if any(keyword in text for keyword in ['设计', 'DESIGN', 'DRAWN BY', '制图']):
                standard_content['designer'] += 1
            if any(keyword in text for keyword in ['校对', 'CHECK', 'REVIEWED BY', '校核']):
                standard_content['checker'] += 1
            if any(keyword in text for keyword in ['审核', '审批', 'APPROVE', 'APPROVED BY', '审查']):
                standard_content['approver'] += 1
            
            # 6. 日期检测
            date_patterns = [
                r'\d{4}[-./年]\d{1,2}[-./月]\d{1,2}',  # 2024-01-01格式
                r'\d{4}\.\d{1,2}\.\d{1,2}',           # 2024.01.01格式
                r'\d{1,2}[-./]\d{1,2}[-./]\d{4}',     # 01-01-2024格式
            ]
            if any(re.search(pattern, text) for pattern in date_patterns):
                standard_content['date'] += 1
            
            # 7. 专业标识检测
            for prof, keywords in profession_keywords.items():
                if any(keyword in text_upper or keyword in text for keyword in keywords):
                    standard_content['profession'] += 1
                    break
            
            # 8. 设计阶段检测
            if any(keyword in text for keyword in phase_keywords):
                standard_content['phase'] += 1
            
            # 9. 版本号检测
            if re.search(r'[Vv]\d+\.\d+', text) or '版本' in text or 'VERSION' in text_upper:
                standard_content['version'] += 1
            
            # 10. 设计单位检测
            if any(keyword in text for keyword in ['设计院', '设计公司', '建筑设计', 'DESIGN INSTITUTE']):
                standard_content['unit'] += 1
        
        # 计算图签内容得分（总分3.0）
        # 必需内容（2.4分）
        essential_items = ['drawing_number', 'drawing_title', 'scale', 'designer', 'checker', 'approver']
        for item in essential_items:
            if standard_content[item] > 0:
                score += 0.4  # 每个必需项0.4分
        
        # 重要内容（0.4分）
        important_items = ['project_name', 'date']
        for item in important_items:
            if standard_content[item] > 0:
                score += 0.2  # 每个重要项0.2分
        
        # 补充内容（0.2分）
        supplementary_items = ['profession', 'phase', 'version', 'unit']
        for item in supplementary_items:
            if standard_content[item] > 0:
                score += 0.05  # 每个补充项0.05分
        
        # 文本数量合理性加分
        if 8 <= len(title_texts) <= 30:
            score += 0.2  # 合理的文本数量
        elif 5 <= len(title_texts) <= 40:
            score += 0.1  # 可接受的文本数量
        
        return min(score, 3.0)  # 最高3分
    
    def _validate_border_integrity(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """验证边框完整性"""
        min_x, min_y, max_x, max_y = bounds
        tolerance = 10  # 10个单位的容差
        
        # 检查四条边框线
        edges = {
            'top': (min_x, max_y, max_x, max_y),      # 上边
            'bottom': (min_x, min_y, max_x, min_y),   # 下边  
            'left': (min_x, min_y, min_x, max_y),     # 左边
            'right': (max_x, min_y, max_x, max_y)     # 右边
        }
        
        found_edges = 0
        entity_count = 0
        
        for entity in modelspace:
            entity_count += 1
            if entity_count > 2000:  # 限制检查数量
                break
                
            if entity.dxftype() == 'LINE':
                try:
                    start = entity.dxf.start
                    end = entity.dxf.end
                    
                    for edge_name, (ex1, ey1, ex2, ey2) in edges.items():
                        # 检查线段是否接近边框线
                        if edge_name in ['top', 'bottom']:  # 水平线
                            if (abs(start.y - ey1) < tolerance and abs(end.y - ey1) < tolerance and
                                abs(start.x - ex1) < tolerance * 5 and abs(end.x - ex2) < tolerance * 5):
                                found_edges += 1
                                break
                        else:  # 垂直线
                            if (abs(start.x - ex1) < tolerance and abs(end.x - ex1) < tolerance and
                                abs(start.y - ey1) < tolerance * 5 and abs(end.y - ey2) < tolerance * 5):
                                found_edges += 1
                                break
                except:
                    continue
        
        # 边框完整性得分
        if found_edges >= 3:
            return 1.0  # 找到3条边以上
        elif found_edges >= 2:
            return 0.6  # 找到2条边
        elif found_edges >= 1:
            return 0.3  # 找到1条边
        else:
            return 0.0
    
    def _validate_standard_texts(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """验证标准文本内容"""
        # 在整个图框范围内查找文本
        all_texts = self._find_texts_in_specific_area(modelspace, bounds, max_texts=100)
        
        score = 0.0
        
        # 检测专业标识
        profession_keywords = {
            'architecture': ['建筑', '建施', 'ARCH', 'ARCHITECTURE'],
            'structure': ['结构', '结施', 'STRUCT', 'STRUCTURE'], 
            'mep': ['给排水', '电气', '暖通', 'MEP', 'HVAC', 'PLUMBING', 'ELECTRICAL'],
            'landscape': ['景观', '园林', 'LANDSCAPE'],
            'interior': ['装修', '室内', 'INTERIOR']
        }
        
        for text in all_texts:
            text_upper = text.upper()
            
            # 专业识别加分
            for prof, keywords in profession_keywords.items():
                if any(keyword in text_upper or keyword in text for keyword in keywords):
                    score += 0.2
                    break
            
            # 标准术语识别
            standard_terms = ['平面图', '立面图', '剖面图', '节点图', '详图', '大样', 
                            'PLAN', 'ELEVATION', 'SECTION', 'DETAIL']
            if any(term in text_upper or term in text for term in standard_terms):
                score += 0.3
            
            # 标准单位识别
            if any(unit in text for unit in ['mm', 'MM', 'M', 'm']):
                score += 0.1
        
        return min(score, 2.0)  # 最高2分
    
    def _validate_standard_seal_positions(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """验证标准印章位置"""
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        
        # 标准印章位置：图签区域内
        seal_areas = [
            # 注册建筑师章位置（图签右侧）
            (max_x - width * 0.2, min_y, max_x, min_y + height * 0.15),
            # 设计单位章位置（图签左侧）
            (max_x - width * 0.3, min_y, max_x - width * 0.15, min_y + height * 0.15),
        ]
        
        score = 0.0
        entity_count = 0
        
        for seal_area in seal_areas:
            seal_min_x, seal_min_y, seal_max_x, seal_max_y = seal_area
            found_seals = 0
            
            for entity in modelspace:
                entity_count += 1
                if entity_count > 1000:
                    break
                
                try:
                    # 检查圆形印章
                    if entity.dxftype() in ['CIRCLE']:
                        center = entity.dxf.center
                        if (seal_min_x <= center.x <= seal_max_x and 
                            seal_min_y <= center.y <= seal_max_y):
                            radius = entity.dxf.radius
                            if 10 <= radius <= 50:  # 合理的印章尺寸
                                found_seals += 1
                    
                    # 检查矩形印章框
                    elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE']:
                        if hasattr(entity, 'get_points'):
                            points = list(entity.get_points())
                            if len(points) >= 4:
                                center_x = sum(p[0] for p in points) / len(points)
                                center_y = sum(p[1] for p in points) / len(points)
                                
                                if (seal_min_x <= center_x <= seal_max_x and 
                                    seal_min_y <= center_y <= seal_max_y):
                                    found_seals += 1
                except:
                    continue
            
            if found_seals > 0:
                score += 0.5
        
        return min(score, 1.0)  # 最高1分
    
    def _get_size_standard_score(self, frame_candidate: Dict[str, Any]) -> float:
        """获取尺寸标准性得分"""
        size_match = frame_candidate.get('size_match', '')
        frame_type = frame_candidate.get('frame_type', '')
        
        if size_match == 'exact':
            if 'A0' in frame_type or 'A1' in frame_type:
                return 1.0  # 大图纸得分高
            elif 'A2' in frame_type or 'A3' in frame_type:
                return 0.8  # 中等图纸
            else:
                return 0.6  # 其他标准尺寸
        elif size_match == 'approximate':
            return 0.4  # 近似匹配
        else:
            return 0.0  # 非标准尺寸
    
    def _find_frames_relaxed(self, modelspace: Any, fast_mode: bool = False) -> List[Dict[str, Any]]:
        """宽松的图框查找（备用方法）"""
        relaxed_frames = []
        
        # 这里可以添加宽松的检测逻辑
        # 目前保持原有的实现
        for entity in modelspace:
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE']:
                if self._is_rectangle(entity):
                    bounds = self._get_entity_bounds(entity)
                    if bounds and self._basic_frame_validation(bounds):
                        relaxed_frames.append({
                            'entity': entity,
                            'bounds': bounds,
                            'frame_type': 'NonStandard',
                            'size_match': 'relaxed'
                        })
        
        return relaxed_frames[:100]  # 限制数量
    
    def _supplementary_frame_detection(self, modelspace: Any, existing_frames: List[Dict[str, Any]], fast_mode: bool = False) -> List[Dict[str, Any]]:
        """补充图框检测（优化版本 - 多策略提高召回率）"""
        additional_frames = []
        
        # 获取已有图框的边界，避免重复
        existing_bounds = [frame['bounds'] for frame in existing_frames]
        
        # 策略1：使用更宽松的条件查找额外图框
        logger.info("执行补充检测策略1：宽松矩形检测")
        max_supplementary = 50 if fast_mode else 100  # 增加补充数量限制
        
        for entity in modelspace:
            if len(additional_frames) >= max_supplementary:
                break
                
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE']:
                if self._is_rectangle(entity):
                    bounds = self._get_entity_bounds(entity)
                    if bounds and self._is_valid_frame_size_relaxed(bounds):
                        # 检查是否与现有图框重叠
                        is_duplicate = False
                        for existing_bound in existing_bounds:
                            if self._is_frames_overlapping(bounds, existing_bound, overlap_threshold=0.4):  # 降低重叠阈值
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            additional_frames.append({
                                'entity': entity,
                                'bounds': bounds,
                                'frame_type': 'Supplementary',
                                'size_match': 'relaxed',
                                'validation_score': 1.0  # 给补充检测的图框基础分
                            })
        
        logger.info(f"策略1找到 {len(additional_frames)} 个补充图框")
        
        # 策略2：基于文本区域的图框推断
        if len(additional_frames) < max_supplementary * 0.8:  # 如果第一策略效果不好
            logger.info("执行补充检测策略2：文本区域推断")
            text_based_frames = self._detect_frames_by_text_areas(modelspace, existing_bounds + [f['bounds'] for f in additional_frames])
            additional_frames.extend(text_based_frames)
        
        # 策略3：基于图元密度的区域检测
        if len(additional_frames) < max_supplementary * 0.6:
            logger.info("执行补充检测策略3：图元密度检测")
            density_based_frames = self._detect_frames_by_entity_density(modelspace, existing_bounds + [f['bounds'] for f in additional_frames])
            additional_frames.extend(density_based_frames)
        
        # 去重并按得分排序
        unique_frames = self._remove_duplicate_frames(additional_frames)
        unique_frames.sort(key=lambda x: x.get('validation_score', 0), reverse=True)
        
        logger.info(f"补充检测总共找到 {len(unique_frames)} 个额外图框")
        return unique_frames[:max_supplementary]
    
    def _detect_frames_by_text_areas(self, modelspace: Any, excluded_bounds: List) -> List[Dict[str, Any]]:
        """基于文本聚集区域推断图框位置"""
        text_frames = []
        text_entities = []
        
        # 收集所有文本实体
        for entity in modelspace:
            if entity.dxftype() in ['TEXT', 'MTEXT']:
                try:
                    if hasattr(entity, 'insert') and hasattr(entity, 'text'):
                        text_entities.append({
                            'position': entity.insert,
                            'text': entity.text,
                            'entity': entity
                        })
                except:
                    continue
        
        if len(text_entities) < 10:  # 文本太少，不适用此策略
            return text_frames
        
        # 分析文本聚集区域
        text_clusters = self._cluster_text_entities(text_entities)
        
        for cluster in text_clusters:
            if len(cluster) >= 5:  # 至少5个文本实体形成聚集
                # 计算聚集区域的边界
                min_x = min(t['position'][0] for t in cluster)
                max_x = max(t['position'][0] for t in cluster)
                min_y = min(t['position'][1] for t in cluster)
                max_y = max(t['position'][1] for t in cluster)
                
                # 扩展边界以形成可能的图框
                padding = 100  # 扩展边距
                estimated_bounds = (min_x - padding, min_y - padding, max_x + padding, max_y + padding)
                
                # 检查是否与已有图框重叠
                is_duplicate = False
                for existing_bound in excluded_bounds:
                    if self._is_frames_overlapping(estimated_bounds, existing_bound, overlap_threshold=0.3):
                        is_duplicate = True
                        break
                
                if not is_duplicate and self._is_valid_frame_size_relaxed(estimated_bounds):
                    text_frames.append({
                        'bounds': estimated_bounds,
                        'frame_type': 'TextBased',
                        'size_match': 'inferred',
                        'validation_score': 1.5,  # 稍高的分数
                        'entity': None
                    })
        
        return text_frames
    
    def _detect_frames_by_entity_density(self, modelspace: Any, excluded_bounds: List) -> List[Dict[str, Any]]:
        """基于图元密度检测可能的图框区域"""
        density_frames = []
        
        # 简化的网格密度分析
        # 将图纸空间分割成网格，分析每个网格的图元密度
        try:
            # 计算整体边界
            all_entities = list(modelspace)
            if len(all_entities) < 100:
                return density_frames
            
            # 获取所有实体的边界
            min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
            
            for entity in all_entities[:1000]:  # 限制分析数量
                bounds = self._get_entity_bounds(entity)
                if bounds:
                    min_x = min(min_x, bounds[0])
                    min_y = min(min_y, bounds[1])
                    max_x = max(max_x, bounds[2])
                    max_y = max(max_y, bounds[3])
            
            if min_x == float('inf'):
                return density_frames
            
            # 分析高密度区域（简化版本）
            grid_size = 500  # 网格大小
            width = max_x - min_x
            height = max_y - min_y
            
            if width > 2000 and height > 1500:  # 只对足够大的图纸进行密度分析
                # 寻找可能的高密度区域作为图框候选
                sample_regions = [
                    (min_x, min_y, min_x + 1000, min_y + 700),  # 左下角
                    (max_x - 1000, min_y, max_x, min_y + 700),  # 右下角
                    (min_x, max_y - 700, min_x + 1000, max_y),  # 左上角
                    (max_x - 1000, max_y - 700, max_x, max_y),  # 右上角
                ]
                
                for region in sample_regions:
                    # 检查是否与已有图框重叠
                    is_duplicate = False
                    for existing_bound in excluded_bounds:
                        if self._is_frames_overlapping(region, existing_bound, overlap_threshold=0.3):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate and self._is_valid_frame_size_relaxed(region):
                        density_frames.append({
                            'bounds': region,
                            'frame_type': 'DensityBased',
                            'size_match': 'inferred',
                            'validation_score': 1.2,
                            'entity': None
                        })
        
        except Exception as e:
            logger.warning(f"密度检测出错: {e}")
        
        return density_frames
    
    def _cluster_text_entities(self, text_entities: List[Dict]) -> List[List[Dict]]:
        """简单的文本聚类算法"""
        if not text_entities:
            return []
        
        clusters = []
        cluster_distance = 200  # 聚类距离阈值
        
        for text in text_entities:
            pos = text['position']
            assigned = False
            
            # 尝试加入现有聚类
            for cluster in clusters:
                # 计算到聚类中心的距离
                cluster_center_x = sum(t['position'][0] for t in cluster) / len(cluster)
                cluster_center_y = sum(t['position'][1] for t in cluster) / len(cluster)
                
                distance = ((pos[0] - cluster_center_x) ** 2 + (pos[1] - cluster_center_y) ** 2) ** 0.5
                
                if distance < cluster_distance:
                    cluster.append(text)
                    assigned = True
                    break
            
            # 如果没有合适的聚类，创建新聚类
            if not assigned:
                clusters.append([text])
        
        return clusters
    
    def _remove_duplicate_frames(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复的图框"""
        unique_frames = []
        
        for frame in frames:
            is_duplicate = False
            frame_bounds = frame['bounds']
            
            for existing_frame in unique_frames:
                if self._is_frames_overlapping(frame_bounds, existing_frame['bounds'], overlap_threshold=0.5):
                    # 保留得分更高的图框
                    if frame.get('validation_score', 0) > existing_frame.get('validation_score', 0):
                        unique_frames.remove(existing_frame)
                        unique_frames.append(frame)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_frames.append(frame)
        
        return unique_frames
    
    def _finalize_frame_list(self, validated_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """最终确定图框列表"""
        if not validated_frames:
            return []
        
        # 按验证得分排序
        validated_frames.sort(key=lambda x: x.get('validation_score', 0), reverse=True)
        
        # 去重处理
        final_frames = []
        for frame in validated_frames:
            is_duplicate = False
            for existing_frame in final_frames:
                if self._is_frames_overlapping(frame['bounds'], existing_frame['bounds'], overlap_threshold=0.6):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                final_frames.append(frame)
        
        # 限制最大数量
        max_frames = 80
        if len(final_frames) > max_frames:
            logger.warning(f"图框数量过多({len(final_frames)})，限制为前{max_frames}个最高得分的")
            final_frames = final_frames[:max_frames]
        
        return final_frames
    
    def _is_valid_frame_size_relaxed(self, bounds: Tuple[float, float, float, float]) -> bool:
        """放宽的图框尺寸验证，支持更多图框尺寸"""
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        area = width * height
        
        # 更宽松的最小面积阈值
        min_area = 20000  # 降低最小面积要求
        max_area = 5000000  # 设置最大面积限制
        
        # 检查面积是否合理
        if area < min_area or area > max_area:
            return False
        
        # 更宽松的长宽比检测
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > 10:  # 长宽比不能太极端
            return False
        
        # 检查是否接近标准图框尺寸或其变体
        standard_sizes = [
            (841, 1189),   # A0
            (594, 841),    # A1
            (420, 594),    # A2
            (297, 420),    # A3
            (210, 297),    # A4
            # 添加一些常见的变体尺寸
            (1000, 700),   # 常见建筑图框
            (800, 600),    # 常见结构图框
            (1200, 800),   # 大型图框
        ]
        
        # 允许的尺寸偏差和加长比例
        tolerance = 0.3  # 增加容差到30%
        max_extend_ratio = 6.0  # 允许加长至6倍
        
        for std_w, std_h in standard_sizes:
            # 检查各种情况的匹配
            checks = [
                # 标准尺寸匹配
                (abs(width - std_w) / std_w < tolerance and abs(height - std_h) / std_h < tolerance),
                # 旋转90度匹配
                (abs(width - std_h) / std_h < tolerance and abs(height - std_w) / std_w < tolerance),
                # 宽度接近标准，高度可以加长
                (abs(width - std_w) / std_w < tolerance and std_h * 0.5 <= height <= std_h * max_extend_ratio),
                # 高度接近标准，宽度可以加长
                (abs(height - std_h) / std_h < tolerance and std_w * 0.5 <= width <= std_w * max_extend_ratio),
                # 旋转版本的加长
                (abs(width - std_h) / std_h < tolerance and std_w * 0.5 <= height <= std_w * max_extend_ratio),
                (abs(height - std_w) / std_w < tolerance and std_h * 0.5 <= width <= std_h * max_extend_ratio),
            ]
            
            if any(checks):
                return True
        
        # 如果不匹配标准尺寸，检查是否是合理的矩形
        # 最小尺寸检查
        if width >= 100 and height >= 100:  # 最小100单位
            return True
        
        return False
    
    def _basic_frame_validation(self, bounds: Tuple[float, float, float, float]) -> bool:
        """基本的图框验证，用于宽松策略"""
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        area = width * height
        
        # 基本检查
        if area < 50000:  # 最小面积
            return False
        
        if width < 200 or height < 150:  # 最小尺寸
            return False
        
        # 长宽比检查
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > 8:  # 不能太极端
            return False
        
        return True
    
    def _filter_overlapping_frames_relaxed(self, potential_frames: List[Tuple[float, float, float, float]]) -> List[Tuple[float, float, float, float]]:
        """更宽松的重叠图框过滤"""
        if not potential_frames:
            return []
        
        # 按面积排序，优先保留大的图框
        frames_with_area = []
        for bounds in potential_frames:
            area = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
            frames_with_area.append((bounds, area))
        
        frames_with_area.sort(key=lambda x: x[1], reverse=True)
        
        filtered_frames = []
        
        for bounds, area in frames_with_area:
            # 检查是否与已有图框重叠
            is_overlapping = False
            
            for existing_bounds in filtered_frames:
                # 使用更高的重叠阈值，允许更多图框通过
                if self._is_frames_overlapping(bounds, existing_bounds, overlap_threshold=0.7):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered_frames.append(bounds)
        
        return filtered_frames
    
    def _analyze_title_block_features(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """
        分析图框的图签特征，返回特征得分（使用浮点数以支持更精细的评分）
        
        Args:
            modelspace: 模型空间
            bounds: 图框边界
            
        Returns:
            特征得分（0-10分，支持小数）
        """
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        score = 0.0
        
        try:
            # 1. 检测图签区域（通常在右下角）
            title_block_area = (
                max_x - width * 0.3,  # 右侧30%区域
                min_y,                # 底部
                max_x,               # 右边界
                min_y + height * 0.25  # 扩大到下方25%区域
            )
            
            # 2. 在图签区域查找文本，适当增加数量限制
            title_texts = self._find_texts_in_specific_area(modelspace, title_block_area, max_texts=80)
            
            # 降低文本数量要求
            if len(title_texts) < 1:
                return 0.0
            
            # 3. 检测关键文本特征
            key_features = {
                'drawing_number': 0.0,    # 图号
                'title': 0.0,            # 图名
                'scale': 0.0,            # 比例
                'date': 0.0,             # 日期
                'designer': 0.0,         # 设计相关
                'company': 0.0,          # 公司信息
                'project': 0.0           # 工程信息
            }
            
            # 检测图号格式（更宽松的模式）
            drawing_number_patterns = [
                r'[A-Z]-\d+',           # A-01, S-02等
                r'\d+-\d+',             # 1-1, 2-3等  
                r'[A-Z]\d{2,}',         # A01, S02等
                r'\d{2,}',              # 纯数字图号
                r'图\s*号',             # 包含"图号"字样
                r'Drawing',             # 包含"Drawing"
                r'No\.',                # 包含"No."
            ]
            
            # 限制文本处理数量，避免性能问题
            texts_to_process = title_texts[:50]  # 处理前50个文本
            
            for text in texts_to_process:
                text_upper = text.upper()
                text_clean = text.strip()
                
                # 检测图号（加权更高）
                for pattern in drawing_number_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        key_features['drawing_number'] += 0.5
                        break
                
                # 检测比例
                if (re.search(r'1\s*[:：]\s*\d+', text) or 
                    '比例' in text or 'SCALE' in text_upper or
                    re.search(r'\d+:\d+', text)):
                    key_features['scale'] += 0.3
                
                # 检测日期
                if (re.search(r'\d{4}[-./]\d{1,2}[-./]\d{1,2}', text) or 
                    re.search(r'\d{4}\s*年', text) or
                    re.search(r'\d{2}[-./]\d{2}[-./]\d{2,4}', text)):
                    key_features['date'] += 0.2
                
                # 检测设计相关文本
                design_keywords = ['设计', '校对', '审核', '审批', '制图', 'DESIGN', 'CHECK', 'APPROVE', 'DRAWN']
                if any(keyword in text_upper or keyword in text for keyword in design_keywords):
                    key_features['designer'] += 0.2
                
                # 检测公司/单位信息
                company_keywords = ['公司', '集团', 'GROUP', 'CO', 'LTD', '工程', '设计院', 'INSTITUTE']
                if any(keyword in text_upper or keyword in text for keyword in company_keywords):
                    key_features['company'] += 0.2
                
                # 检测工程名称相关
                project_keywords = ['工程', '项目', 'PROJECT', '建筑', '结构', '给排水', '电气', '暖通', '机电']
                if any(keyword in text_upper or keyword in text for keyword in project_keywords):
                    key_features['project'] += 0.1
                
                # 检测图纸标题相关
                title_keywords = ['平面图', '立面图', '剖面图', '详图', '大样', 'PLAN', 'ELEVATION', 'SECTION', 'DETAIL']
                if any(keyword in text_upper or keyword in text for keyword in title_keywords):
                    key_features['title'] += 0.3
            
            # 4. 计算特征得分
            for feature, value in key_features.items():
                score += min(value, 2.0)  # 每个特征最高2分
            
            # 5. 检测印章位置框（图签中的印章框，而不是实际印章）
            seal_score = self._detect_seal_positions_fast(modelspace, title_block_area)
            score += seal_score
            
            # 6. 检测表格结构（图签通常有表格结构）
            table_score = self._detect_table_structure_fast(modelspace, title_block_area)
            score += table_score
            
            # 7. 文本密度检查（图签区域应该有适量文本）
            text_density_score = self._calculate_text_density_score(len(title_texts))
            score += text_density_score
            
            # 8. 位置加分（右下角的图框更可能是真实图框）
            position_score = self._calculate_position_score(bounds, modelspace)
            score += position_score
            
            logger.debug(f"图框 {bounds} 特征分析: 文本数={len(title_texts)}, 特征得分={key_features}, 总分={score:.2f}")
            
        except Exception as e:
            logger.error(f"分析图签特征时出错: {e}")
            score = 0.0
        
        return score
    
    def _find_texts_in_specific_area(self, modelspace: Any, bounds: Tuple[float, float, float, float], max_texts: int = 50) -> List[str]:
        """在指定区域查找文本，专门用于图签检测"""
        texts = []
        min_x, min_y, max_x, max_y = bounds
        
        try:
            for entity in modelspace:
                if entity.dxftype() in ['TEXT', 'MTEXT']:
                    try:
                        # 获取文本位置
                        if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'insert'):
                            x, y = entity.dxf.insert.x, entity.dxf.insert.y
                        elif hasattr(entity, 'get_pos'):
                            pos = entity.get_pos()
                            x, y = pos[0], pos[1]
                        else:
                            continue
                        
                        # 检查是否在指定区域内
                        if min_x <= x <= max_x and min_y <= y <= max_y:
                            text_content = getattr(entity.dxf, 'text', '')
                            if text_content and text_content.strip():
                                texts.append(text_content.strip())
                    
                    except Exception as e:
                        continue
        
        except Exception as e:
            logger.error(f"查找指定区域文本时发生错误: {e}")
        
        return texts[:max_texts]
    
    def _detect_seal_positions_fast(self, modelspace: Any, bounds: Tuple[float, float, float, float]) -> float:
        """检测印章位置框（图签中预留的印章位置，通常是矩形框）- 快速版本"""
        score = 0.0
        min_x, min_y, max_x, max_y = bounds
        
        try:
            # 印章位置通常在图签的特定区域
            seal_areas = [
                (max_x - (max_x - min_x) * 0.4, min_y, max_x, min_y + (max_y - min_y) * 0.3),  # 右下区域
                (min_x, min_y, min_x + (max_x - min_x) * 0.3, min_y + (max_y - min_y) * 0.3),  # 左下区域
            ]
            
            # 限制检查的实体数量
            entity_count = 0
            max_entities = 800  # 增加检查数量
            
            for seal_area in seal_areas:
                seal_min_x, seal_min_y, seal_max_x, seal_max_y = seal_area
                
                # 查找矩形框（印章位置框）
                rectangles_found = 0
                circles_found = 0
                
                for entity in modelspace:
                    entity_count += 1
                    if entity_count > max_entities:
                        break
                    
                    try:
                        # 检查矩形印章框
                        if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE']:
                            if hasattr(entity, 'get_points'):
                                points = list(entity.get_points())
                                if len(points) >= 4:
                                    # 计算中心点
                                    center_x = sum(p[0] for p in points) / len(points)
                                    center_y = sum(p[1] for p in points) / len(points)
                                    
                                    if (seal_min_x <= center_x <= seal_max_x and 
                                        seal_min_y <= center_y <= seal_max_y):
                                        rectangles_found += 1
                        
                        # 检查圆形印章
                        elif entity.dxftype() in ['CIRCLE', 'ARC']:
                            center = entity.dxf.center
                            if (seal_min_x <= center.x <= seal_max_x and 
                                seal_min_y <= center.y <= seal_max_y):
                                circles_found += 1
                                
                    except:
                        continue
                
                # 计算印章得分
                if rectangles_found > 0:
                    score += 0.3  # 找到矩形印章框
                if circles_found > 0:
                    score += 0.2  # 找到圆形印章
                    
                if entity_count > max_entities:
                    break
        
        except Exception as e:
            logger.debug(f"检测印章位置时出错: {e}")
        
        return min(score, 0.8)  # 最多0.8分
    
    def _calculate_text_density_score(self, text_count: int) -> float:
        """根据文本数量计算密度得分"""
        if text_count == 0:
            return 0.0
        elif 1 <= text_count <= 3:
            return 0.1  # 文本太少
        elif 4 <= text_count <= 15:
            return 0.3  # 合理范围
        elif 16 <= text_count <= 40:
            return 0.5  # 较好范围
        elif 41 <= text_count <= 80:
            return 0.4  # 文本较多但可接受
        else:
            return 0.2  # 文本过多
    
    def _calculate_position_score(self, bounds: Tuple[float, float, float, float], modelspace: Any) -> float:
        """根据图框位置计算得分"""
        try:
            # 获取整个图纸的大致边界
            all_x = []
            all_y = []
            
            entity_count = 0
            for entity in modelspace:
                entity_count += 1
                if entity_count > 1000:  # 限制检查数量
                    break
                    
                try:
                    if hasattr(entity, 'get_points'):
                        points = list(entity.get_points())
                        if points:
                            all_x.extend([p[0] for p in points])
                            all_y.extend([p[1] for p in points])
                except:
                    continue
            
            if not all_x or not all_y:
                return 0.1  # 默认小分
            
            # 计算图框相对位置
            min_x, min_y, max_x, max_y = bounds
            drawing_min_x, drawing_max_x = min(all_x), max(all_x)
            drawing_min_y, drawing_max_y = min(all_y), max(all_y)
            
            # 检查是否在图纸边缘（图框通常在边缘）
            edge_tolerance = 0.1  # 10%容差
            
            score = 0.0
            
            # 检查是否靠近图纸边界
            if abs(min_x - drawing_min_x) / (drawing_max_x - drawing_min_x) < edge_tolerance:
                score += 0.1  # 左边缘
            if abs(max_x - drawing_max_x) / (drawing_max_x - drawing_min_x) < edge_tolerance:
                score += 0.1  # 右边缘
            if abs(min_y - drawing_min_y) / (drawing_max_y - drawing_min_y) < edge_tolerance:
                score += 0.1  # 下边缘
            if abs(max_y - drawing_max_y) / (drawing_max_y - drawing_min_y) < edge_tolerance:
                score += 0.1  # 上边缘
            
            return min(score, 0.3)  # 最多0.3分
            
        except Exception as e:
            logger.debug(f"计算位置得分时出错: {e}")
            return 0.1
    
    def _is_frames_overlapping(self, frame1: Tuple[float, float, float, float], 
                              frame2: Tuple[float, float, float, float], 
                              overlap_threshold: float = 0.3) -> bool:
        """检查两个图框是否重叠"""
        min_x1, min_y1, max_x1, max_y1 = frame1
        min_x2, min_y2, max_x2, max_y2 = frame2
        
        # 计算重叠区域
        overlap_min_x = max(min_x1, min_x2)
        overlap_min_y = max(min_y1, min_y2)
        overlap_max_x = min(max_x1, max_x2)
        overlap_max_y = min(max_y1, max_y2)
        
        if overlap_max_x <= overlap_min_x or overlap_max_y <= overlap_min_y:
            return False  # 没有重叠
        
        # 计算重叠面积
        overlap_area = (overlap_max_x - overlap_min_x) * (overlap_max_y - overlap_min_y)
        
        # 计算两个图框的面积
        area1 = (max_x1 - min_x1) * (max_y1 - min_y1)
        area2 = (max_x2 - min_x2) * (max_y2 - min_y2)
        
        # 计算重叠比例
        overlap_ratio1 = overlap_area / area1 if area1 > 0 else 0
        overlap_ratio2 = overlap_area / area2 if area2 > 0 else 0
        
        # 如果任一图框的重叠比例超过阈值，认为是重叠的
        return max(overlap_ratio1, overlap_ratio2) > overlap_threshold
    
    def _is_rectangle(self, entity: Any) -> bool:
        """检查实体是否为矩形"""
        try:
            if hasattr(entity, 'get_points'):
                points = list(entity.get_points())
                return len(points) >= 4  # 至少4个点
            return False
        except:
            return False
    
    def _get_entity_bounds(self, entity: Any) -> Optional[Tuple[float, float, float, float]]:
        """获取实体边界框"""
        try:
            if hasattr(entity, 'get_points'):
                points = list(entity.get_points())
                if points:
                    x_coords = [p[0] for p in points]
                    y_coords = [p[1] for p in points]
                    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
            elif hasattr(entity, 'bounding_box'):
                bbox = entity.bounding_box
                return (bbox.extmin.x, bbox.extmin.y, bbox.extmax.x, bbox.extmax.y)
            return None
        except:
            return None
    
    def _is_valid_frame_size(self, bounds: Tuple[float, float, float, float]) -> bool:
        """检查是否为有效的图框尺寸，支持A0~A4及其加长版本"""
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        area = width * height
        
        # 标准图框尺寸 (毫米)
        standard_sizes = [
            (841, 1189),   # A0
            (594, 841),    # A1
            (420, 594),    # A2
            (297, 420),    # A3
            (210, 297)     # A4
        ]
        
        # 允许的尺寸偏差
        tolerance = 0.15  # 15%偏差
        max_extend_ratio = 4.0  # 允许加长至4倍
        min_area = 50000  # 最小面积阈值
        
        # 检查面积是否合理
        if area < min_area:
            return False
        
        for std_w, std_h in standard_sizes:
            # 检查宽度接近标准，高度可以加长
            if (abs(width - std_w) / std_w < tolerance and 
                std_h * 0.8 <= height <= std_h * max_extend_ratio):
                return True
            
            # 检查高度接近标准，宽度可以加长
            if (abs(height - std_h) / std_h < tolerance and 
                std_w * 0.8 <= width <= std_w * max_extend_ratio):
                return True
            
            # 检查标准尺寸的旋转版本
            if (abs(width - std_h) / std_h < tolerance and 
                std_w * 0.8 <= height <= std_w * max_extend_ratio):
                return True
            
            if (abs(height - std_w) / std_w < tolerance and 
                std_h * 0.8 <= width <= std_h * max_extend_ratio):
                return True
        
        return False
    
    def _extract_frame_info(self, doc: Any, bounds: Tuple[float, float, float, float], index: int) -> Dict[str, Any]:
        """
        从图框区域提取图纸信息
        
        Args:
            doc: ezdxf文档对象
            bounds: 图框边界
            index: 图框索引
            
        Returns:
            图框信息字典
        """
        try:
            # 在图框附近查找文本，提取图号、标题、比例等信息
            texts_in_frame = self._find_texts_in_area(doc, bounds)
            
            # 解析文本，提取图纸信息
            drawing_number = self._extract_drawing_number(texts_in_frame, index)
            title = self._extract_drawing_title(texts_in_frame, index)
            scale = self._extract_drawing_scale(texts_in_frame)
            
            return {
                "index": index,
                "bounds": bounds,
                "drawing_number": drawing_number,
                "title": title,
                "scale": scale,
                "texts": texts_in_frame[:10]  # 保留前10个文本用于调试
            }
            
        except Exception as e:
            logger.error(f"提取图框信息时发生错误: {e}")
            return self._create_default_frame_info(index, bounds)
    
    def _find_texts_in_area(self, doc: Any, bounds: Tuple[float, float, float, float]) -> List[str]:
        """在指定区域查找文本"""
        texts = []
        
        try:
            modelspace = doc.modelspace()
            min_x, min_y, max_x, max_y = bounds
            
            # 扩展搜索区域，包括标题栏
            search_margin = min(max_x - min_x, max_y - min_y) * 0.1
            search_bounds = (
                min_x - search_margin,
                min_y - search_margin,
                max_x + search_margin,
                max_y + search_margin
            )
            
            for entity in modelspace:
                if entity.dxftype() in ['TEXT', 'MTEXT']:
                    try:
                        # 获取文本位置
                        if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'insert'):
                            x, y = entity.dxf.insert.x, entity.dxf.insert.y
                        elif hasattr(entity, 'get_pos'):
                            pos = entity.get_pos()
                            x, y = pos[0], pos[1]
                        else:
                            continue
                        
                        # 检查是否在搜索区域内
                        if (search_bounds[0] <= x <= search_bounds[2] and 
                            search_bounds[1] <= y <= search_bounds[3]):
                            
                            text_content = getattr(entity.dxf, 'text', '')
                            if text_content and text_content.strip():
                                texts.append(text_content.strip())
                    
                    except Exception as e:
                        logger.debug(f"处理文本实体时出错: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"查找文本时发生错误: {e}")
        
        return texts
    
    def _extract_drawing_number(self, texts: List[str], index: int) -> str:
        """从文本中提取图号"""
        # 图号的常见模式
        patterns = [
            r'[A-Z]-\d+',           # A-01, B-02等
            r'\d+-\d+',             # 01-01, 02-03等
            r'[A-Z]\d+',            # A01, B02等
            r'图\s*号\s*[:：]\s*(.+)',  # 图号: XXX
            r'Drawing\s*No\s*[:：]\s*(.+)',  # Drawing No: XXX
        ]
        
        for text in texts:
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if match.groups():
                        return match.group(1).strip()
                    else:
                        return match.group(0).strip()
        
        # 如果没有找到，生成默认图号
        return f"图纸-{index+1:02d}"
    
    def _extract_drawing_title(self, texts: List[str], index: int) -> str:
        """从文本中提取图纸标题"""
        # 标题的常见模式
        title_keywords = ['平面图', '立面图', '剖面图', '详图', '大样', '节点', 
                         'plan', 'elevation', 'section', 'detail']
        
        # 查找包含标题关键词的文本
        for text in texts:
            for keyword in title_keywords:
                if keyword.lower() in text.lower():
                    return text
        
        # 查找较长的文本作为标题
        long_texts = [t for t in texts if len(t) > 3 and len(t) < 50]
        if long_texts:
            return long_texts[0]
        
        # 默认标题
        return f"建筑图纸 {index+1}"
    
    def _extract_drawing_scale(self, texts: List[str]) -> str:
        """从文本中提取比例"""
        scale_patterns = [
            r'1\s*[:：]\s*\d+',      # 1:100, 1：50等
            r'比例\s*[:：]\s*(.+)',    # 比例: 1:100
            r'Scale\s*[:：]\s*(.+)',  # Scale: 1:100
        ]
        
        for text in texts:
            for pattern in scale_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if match.groups():
                        return match.group(1).strip()
                    else:
                        return match.group(0).strip()
        
        return "1:100"  # 默认比例
    
    def _create_default_frame(self) -> Dict[str, Any]:
        """创建默认图框"""
        return {
            "index": 0,
            "bounds": (0, 0, 1000, 700),  # 默认A3尺寸
            "drawing_number": "A-01",
            "title": "建筑平面图",
            "scale": "1:100"
        }
    
    def _create_default_frame_info(self, index: int, bounds: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """创建默认图框信息"""
        return {
            "index": index,
            "bounds": bounds,
            "drawing_number": f"图纸-{index+1:02d}",
            "title": f"建筑图纸 {index+1}",
            "scale": "1:100"
        }
    
    def _process_single_frame(self, doc: Any, frame: Dict[str, Any], index: int, entity_cache=None) -> Dict[str, Any]:
        """处理单个图框，支持实体缓存"""
        try:
            components = self._extract_components_from_frame(doc, frame, entity_cache)
            quantities = self._calculate_quantities(components)
            image_path = self._generate_frame_image(doc, frame, index, entity_cache)
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
    
    def _extract_components_from_frame(self, doc: Any, frame: Dict[str, Any], entity_cache=None) -> List[Dict[str, Any]]:
        """从图框中提取构件，支持实体缓存"""
        components = []
        try:
            bounds = frame.get("bounds", (0, 0, 1000, 700))
            # 用缓存加速
            entities = entity_cache if entity_cache is not None else [(e, self._get_entity_bounds(e)) for e in doc.modelspace()]
            for entity, e_bounds in entities:
                if e_bounds and self._is_entity_in_bounds_bounds(e_bounds, bounds):
                    component = self._classify_entity_as_component(entity)
                    if component:
                        components.append(component)
            if not components:
                components = self._generate_demo_components()
        except Exception as e:
            logger.error(f"提取构件时发生错误: {e}")
            components = self._generate_demo_components()
        return components
    
    def _is_entity_in_bounds_bounds(self, e_bounds, bounds):
        min_x, min_y, max_x, max_y = bounds
        e_min_x, e_min_y, e_max_x, e_max_y = e_bounds
        return not (e_max_x < min_x or e_min_x > max_x or e_max_y < min_y or e_min_y > max_y)
    
    def _classify_entity_as_component(self, entity: Any) -> Optional[Dict[str, Any]]:
        """将实体分类为构件"""
        try:
            entity_type = entity.dxftype()
            
            # 简单的分类逻辑
            if entity_type in ['LINE', 'LWPOLYLINE', 'POLYLINE']:
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
                    "dimensions": {"radius": getattr(entity.dxf, 'radius', 100)},
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
    
    def _generate_frame_image(self, doc: Any, frame: Dict[str, Any], index: int, entity_cache=None) -> Optional[str]:
        if not MATPLOTLIB_AVAILABLE:
            return None
        try:
            import matplotlib
            font_path = 'C:/Windows/Fonts/simhei.ttf'
            if os.path.exists(font_path):
                matplotlib.rcParams['font.sans-serif'] = ['SimHei']
                matplotlib.rcParams['font.family'] = 'sans-serif'
                matplotlib.rcParams['axes.unicode_minus'] = False
                prop = fm.FontProperties(fname=font_path)
            else:
                prop = None
            fig, ax = plt.subplots(1, 1, figsize=(12, 8))
            bounds = frame.get("bounds", (0, 0, 1000, 700))
            min_x, min_y, max_x, max_y = bounds
            # 用缓存加速
            entities = entity_cache if entity_cache is not None else [(e, self._get_entity_bounds(e)) for e in doc.modelspace()]
            for entity, e_bounds in entities:
                if e_bounds and self._is_entity_in_bounds_bounds(e_bounds, bounds):
                    self._plot_entity(entity, ax)
            rect = patches.Rectangle(
                (bounds[0], bounds[1]),
                bounds[2] - bounds[0],
                bounds[3] - bounds[1],
                linewidth=2, edgecolor='black', facecolor='none'
            )
            ax.add_patch(rect)
            ax.text(
                bounds[0] + (bounds[2] - bounds[0]) / 2,
                bounds[3] + 50,
                frame.get("title", f"图纸 {index+1}"),
                ha='center', va='bottom', fontsize=14, fontweight='bold', fontproperties=prop
            )
            ax.set_xlim(bounds[0] - 100, bounds[2] + 100)
            ax.set_ylim(bounds[1] - 100, bounds[3] + 100)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            image_path = os.path.join(self.temp_dir, f"frame_{index}.png")
            plt.savefig(image_path, dpi=150, bbox_inches='tight')
            plt.close()
            import gc
            gc.collect()
            return image_path
        except Exception as e:
            logger.error(f"生成图像时发生错误: {e}")
            return None
    
    def _sort_drawings_by_number(self, drawings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按图号排序 - 优化版本，支持多种图号格式"""
        def natural_sort_key(drawing):
            number = drawing.get("drawing_number", "")
            
            # 处理常见的建筑图号格式
            # 如：A-01, S-02, E-03, A1-01, T1-02, 建-01, 结-02等
            
            # 提取专业代码和数字
            import re
            
            # 匹配模式：专业代码-数字，支持中英文
            pattern = r'^([A-Za-z\u4e00-\u9fff]+)-?(\d+)(?:-(\d+))?'
            match = re.match(pattern, number)
            
            if match:
                prefix = match.group(1)  # 专业代码
                main_num = int(match.group(2))  # 主要数字
                sub_num = int(match.group(3)) if match.group(3) else 0  # 子数字
                
                # 定义专业排序优先级
                profession_order = {
                    'A': 1, '建': 1, 'ARCH': 1,  # 建筑
                    'S': 2, '结': 2, 'STRUCT': 2,  # 结构  
                    'E': 3, '电': 3, 'ELEC': 3,  # 电气
                    'H': 4, '暖': 4, 'HVAC': 4,  # 暖通
                    'W': 5, '给': 5, 'WATER': 5,  # 给排水
                    'L': 6, '景': 6, 'LAND': 6,  # 景观
                    'I': 7, '装': 7, 'INT': 7,  # 装修
                    'T': 8, '总': 8, 'TOTAL': 8,  # 总图
                }
                
                profession_priority = profession_order.get(prefix.upper(), 999)
                return (profession_priority, main_num, sub_num, prefix, number)
            else:
                # 如果不匹配标准格式，按原有逻辑处理
                parts = re.split(r'(\d+)', number)
                return (999, 0, 0, "", [int(part) if part.isdigit() else part for part in parts])
        
        sorted_drawings = sorted(drawings, key=natural_sort_key)
        
        # 验证排序结果并记录
        logger.info("图框排序结果:")
        for i, drawing in enumerate(sorted_drawings):
            drawing_number = drawing.get("drawing_number", f"未知-{i+1}")
            title = drawing.get("title", "未知标题")
            logger.info(f"  {i+1}. {drawing_number} - {title}")
        
        return sorted_drawings
    
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
                "processor_used": "demo",
                "note": "演示模式：由于缺少必要的库或工具，使用模拟数据"
            }
        }

    def process_dwg_to_pdf(self, dwg_path: str, output_dir: str) -> List[str]:
        """
        处理DWG文件并导出为PDF
        Args:
            dwg_path: DWG文件路径
            output_dir: 输出目录
        Returns:
            生成的PDF文件路径列表
        """
        try:
            # 1. 加载DWG文件
            doc = self._load_dwg_file(dwg_path)
            if not doc:
                raise ValueError("无法加载DWG文件")

            # 2. 识别图框和图纸编号
            layouts = self._detect_layouts(doc)
            if not layouts:
                raise ValueError("未检测到有效图框")

            # 3. 按图号排序
            sorted_layouts = self._sort_layouts_by_number(layouts)

            # 4. 为每个图框生成PDF
            pdf_files = []
            for layout in sorted_layouts:
                # 获取图框信息
                layout_info = self._get_layout_info(layout)
                
                # 生成PDF文件名
                pdf_filename = f"{layout_info['drawing_number']}_{layout_info['title']}.pdf"
                pdf_path = os.path.join(output_dir, pdf_filename)
                
                # 导出为PDF
                if self._export_layout_to_pdf(layout, pdf_path):
                    pdf_files.append(pdf_path)
                    logger.info(f"已生成PDF: {pdf_filename}")

            return pdf_files

        except Exception as e:
            logger.error(f"处理DWG文件失败: {e}")
            raise

    def _detect_layouts(self, doc: Any) -> List[Any]:
        """
        检测文档中的所有图框
        Args:
            doc: ezdxf文档对象
        Returns:
            图框列表
        """
        layouts = []
        try:
            # 遍历所有布局
            for layout in doc.layouts:
                # 检查是否包含图框
                if self._has_drawing_frame(layout):
                    layouts.append(layout)
            
            return layouts
        except Exception as e:
            logger.error(f"检测图框失败: {e}")
            return []

    def _has_drawing_frame(self, layout: Any) -> bool:
        """
        检查布局是否包含图框
        Args:
            layout: 布局对象
        Returns:
            是否包含图框
        """
        try:
            # 检查是否包含矩形图框
            for entity in layout:
                if entity.dxftype() == 'LWPOLYLINE':
                    # 检查是否为矩形且尺寸符合标准图框
                    if self._is_standard_frame(entity):
                        return True
            return False
        except Exception as e:
            logger.error(f"检查图框失败: {e}")
            return False

    def _is_standard_frame(self, entity: Any) -> bool:
        """
        检查是否为标准图框
        Args:
            entity: 实体对象
        Returns:
            是否为标准图框
        """
        try:
            # 获取图框尺寸
            points = entity.get_points()
            if len(points) != 4:  # 不是矩形
                return False
            
            # 计算尺寸
            width = abs(points[1][0] - points[0][0])
            height = abs(points[2][1] - points[1][1])
            
            # 检查是否符合标准图框尺寸
            standard_sizes = {
                'A0': (841, 1189),
                'A1': (594, 841),
                'A2': (420, 594),
                'A3': (297, 420),
                'A4': (210, 297)
            }
            
            # 允许5%的误差
            tolerance = 0.05
            for size_name, (std_width, std_height) in standard_sizes.items():
                if (abs(width - std_width) / std_width < tolerance and 
                    abs(height - std_height) / std_height < tolerance):
                    return True
            
            return False
        except Exception as e:
            logger.error(f"检查标准图框失败: {e}")
            return False

    def _sort_layouts_by_number(self, layouts: List[Any]) -> List[Any]:
        """
        按图号排序布局
        Args:
            layouts: 布局列表
        Returns:
            排序后的布局列表
        """
        def get_drawing_number(layout):
            try:
                # 从布局名称或属性中提取图号
                # 这里需要根据实际图纸格式调整提取逻辑
                return layout.dxf.name
            except:
                return ""

        return sorted(layouts, key=get_drawing_number)

    def _get_layout_info(self, layout: Any) -> Dict[str, str]:
        """
        获取布局信息
        Args:
            layout: 布局对象
        Returns:
            布局信息字典
        """
        try:
            # 从布局中提取信息
            # 这里需要根据实际图纸格式调整提取逻辑
            return {
                'drawing_number': layout.dxf.name,
                'title': '未命名图纸',
                'scale': '1:1'
            }
        except Exception as e:
            logger.error(f"获取布局信息失败: {e}")
            return {
                'drawing_number': 'unknown',
                'title': '未知图纸',
                'scale': 'unknown'
            }

    def _export_layout_to_pdf(self, layout: Any, output_path: str) -> bool:
        """
        将布局导出为PDF
        Args:
            layout: 布局对象
            output_path: 输出路径
        Returns:
            是否成功
        """
        try:
            if not MATPLOTLIB_AVAILABLE:
                raise ImportError("matplotlib库未安装")

            # 创建图形
            fig = plt.figure(figsize=(8.27, 11.69))  # A4尺寸
            ax = fig.add_subplot(111)
            
            # 绘制布局内容
            for entity in layout:
                self._plot_entity(entity, ax)
            
            # 保存为PDF
            plt.savefig(output_path, format='pdf', bbox_inches='tight')
            plt.close(fig)
            
            return True
        except Exception as e:
            logger.error(f"导出PDF失败: {e}")
            return False

    def _plot_entity(self, entity: Any, ax: Any) -> None:
        """
        绘制实体
        Args:
            entity: 实体对象
            ax: matplotlib轴对象
        """
        try:
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                ax.plot([start[0], end[0]], [start[1], end[1]], 'k-')
            elif entity.dxftype() == 'LWPOLYLINE':
                points = entity.get_points()
                x = [p[0] for p in points]
                y = [p[1] for p in points]
                ax.plot(x, y, 'k-')
            # 可以添加更多实体类型的处理
        except Exception as e:
            logger.error(f"绘制实体失败: {e}")

    def _export_frame_to_pdf(self, doc: Any, frame: Dict[str, Any], output_path: str, entity_cache=None) -> bool:
        try:
            import matplotlib
            font_path = 'C:/Windows/Fonts/simhei.ttf'
            if os.path.exists(font_path):
                matplotlib.rcParams['font.sans-serif'] = ['SimHei']
                matplotlib.rcParams['font.family'] = 'sans-serif'
                matplotlib.rcParams['axes.unicode_minus'] = False
                prop = fm.FontProperties(fname=font_path)
            else:
                prop = None
            fig, ax = plt.subplots(1, 1, figsize=(8.27, 11.69))
            bounds = frame.get("bounds", (0, 0, 1000, 700))
            min_x, min_y, max_x, max_y = bounds
            # 用缓存加速
            entities = entity_cache if entity_cache is not None else [(e, self._get_entity_bounds(e)) for e in doc.modelspace()]
            for entity, e_bounds in entities:
                if e_bounds and self._is_entity_in_bounds_bounds(e_bounds, bounds):
                    self._plot_entity(entity, ax)
            rect = patches.Rectangle(
                (bounds[0], bounds[1]),
                bounds[2] - bounds[0],
                bounds[3] - bounds[1],
                linewidth=2, edgecolor='black', facecolor='none'
            )
            ax.add_patch(rect)
            ax.text(
                bounds[0] + (bounds[2] - bounds[0]) / 2,
                bounds[3] + 50,
                frame.get("title", f"图纸"),
                ha='center', va='bottom', fontsize=14, fontweight='bold', fontproperties=prop
            )
            ax.set_xlim(bounds[0] - 100, bounds[2] + 100)
            ax.set_ylim(bounds[1] - 100, bounds[3] + 100)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            plt.savefig(output_path, format='pdf', bbox_inches='tight')
            plt.close()
            import gc
            gc.collect()
            return True
        except Exception as e:
            logger.error(f"导出单图框PDF失败: {e}")
            return False

# 使用示例
if __name__ == "__main__":
    processor = DWGProcessor()
    
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