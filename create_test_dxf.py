#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建包含48个图框的测试DXF文件，用于验证图框检测算法
"""

import ezdxf
import os

def create_test_dxf_with_frames():
    """创建包含48个图框的测试DXF文件"""
    print("🏗️  正在创建包含48个图框的测试DXF文件...")
    
    # 创建新的DXF文档
    doc = ezdxf.new('R2010')
    
    # 获取模型空间
    modelspace = doc.modelspace()
    
    # A3图纸尺寸 (297mm x 420mm)
    frame_width = 420
    frame_height = 297
    
    # 网格排列：8行6列 = 48个图框
    rows = 8
    cols = 6
    spacing = 50  # 图框间距
    
    # 图框类别
    frame_types = [
        ("建筑", "A"),
        ("结构", "S"), 
        ("给排水", "W"),
        ("电气", "E"),
        ("暖通", "H"),
        ("装修", "D")
    ]
    
    frame_index = 0
    
    for row in range(rows):
        for col in range(cols):
            if frame_index >= 48:
                break
                
            # 计算图框位置
            x_offset = col * (frame_width + spacing)
            y_offset = row * (frame_height + spacing)
            
            # 创建图框外边界
            frame_corners = [
                (x_offset, y_offset),
                (x_offset + frame_width, y_offset),
                (x_offset + frame_width, y_offset + frame_height),
                (x_offset, y_offset + frame_height),
                (x_offset, y_offset)  # 闭合
            ]
            
            # 绘制图框边界
            modelspace.add_lwpolyline(frame_corners, dxfattribs={'layer': 'FRAME'})
            
            # 确定图纸类型
            type_info = frame_types[frame_index % len(frame_types)]
            type_name, type_code = type_info
            
            # 生成图号
            drawing_number = f"{type_code}-{(frame_index // len(frame_types) + 1):02d}"
            
            # 创建图签区域 (右下角)
            title_block_width = frame_width * 0.3
            title_block_height = frame_height * 0.2
            title_x = x_offset + frame_width - title_block_width
            title_y = y_offset
            
            # 绘制图签外框
            title_corners = [
                (title_x, title_y),
                (title_x + title_block_width, title_y),
                (title_x + title_block_width, title_y + title_block_height),
                (title_x, title_y + title_block_height),
                (title_x, title_y)
            ]
            modelspace.add_lwpolyline(title_corners, dxfattribs={'layer': 'TITLE_BLOCK'})
            
            # 添加图签内部分隔线
            # 水平分隔线
            for i in range(1, 4):
                line_y = title_y + (title_block_height / 4) * i
                modelspace.add_line(
                    (title_x, line_y), 
                    (title_x + title_block_width, line_y),
                    dxfattribs={'layer': 'TITLE_LINES'}
                )
            
            # 垂直分隔线
            for i in range(1, 3):
                line_x = title_x + (title_block_width / 3) * i
                modelspace.add_line(
                    (line_x, title_y), 
                    (line_x, title_y + title_block_height),
                    dxfattribs={'layer': 'TITLE_LINES'}
                )
            
            # 添加图签文本信息
            text_height = 8
            
            # 图号
            modelspace.add_text(
                drawing_number,
                dxfattribs={
                    'layer': 'TEXT',
                    'height': text_height,
                    'insert': (title_x + 10, title_y + title_block_height - 15)
                }
            )
            
            # 图名
            drawing_title = f"{type_name}平面图"
            modelspace.add_text(
                drawing_title,
                dxfattribs={
                    'layer': 'TEXT',
                    'height': text_height,
                    'insert': (title_x + 10, title_y + title_block_height - 35)
                }
            )
            
            # 比例
            scale_text = "1:100"
            modelspace.add_text(
                scale_text,
                dxfattribs={
                    'layer': 'TEXT',
                    'height': text_height - 2,
                    'insert': (title_x + 10, title_y + title_block_height - 50)
                }
            )
            
            # 设计
            modelspace.add_text(
                "设计:",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': text_height - 2,
                    'insert': (title_x + title_block_width * 0.4, title_y + title_block_height - 15)
                }
            )
            
            # 审核
            modelspace.add_text(
                "审核:",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': text_height - 2,
                    'insert': (title_x + title_block_width * 0.4, title_y + title_block_height - 35)
                }
            )
            
            # 日期
            modelspace.add_text(
                "2024.05.28",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': text_height - 2,
                    'insert': (title_x + title_block_width * 0.7, title_y + title_block_height - 15)
                }
            )
            
            # 添加执业章位置标记（小圆圈）
            seal_x = title_x + title_block_width * 0.8
            seal_y = title_y + title_block_height * 0.3
            modelspace.add_circle(
                center=(seal_x, seal_y),
                radius=15,
                dxfattribs={'layer': 'SEAL'}
            )
            
            # 添加出图章位置标记（小方块）
            stamp_x = title_x + title_block_width * 0.8
            stamp_y = title_y + title_block_height * 0.7
            stamp_corners = [
                (stamp_x - 10, stamp_y - 10),
                (stamp_x + 10, stamp_y - 10),
                (stamp_x + 10, stamp_y + 10),
                (stamp_x - 10, stamp_y + 10),
                (stamp_x - 10, stamp_y - 10)
            ]
            modelspace.add_lwpolyline(stamp_corners, dxfattribs={'layer': 'STAMP'})
            
            # 在图框内添加一些装饰性内容（模拟建筑图纸内容）
            content_x = x_offset + 20
            content_y = y_offset + 20
            content_width = frame_width - title_block_width - 40
            content_height = frame_height - 40
            
            # 添加一些直线（模拟墙体）
            for i in range(5):
                line_x = content_x + (content_width / 5) * i
                modelspace.add_line(
                    (line_x, content_y),
                    (line_x, content_y + content_height),
                    dxfattribs={'layer': 'CONTENT'}
                )
            
            for i in range(3):
                line_y = content_y + (content_height / 3) * i
                modelspace.add_line(
                    (content_x, line_y),
                    (content_x + content_width, line_y),
                    dxfattribs={'layer': 'CONTENT'}
                )
            
            frame_index += 1
    
    # 添加一些干扰性的大矩形（非图框）
    print("🎭 添加干扰性矩形...")
    
    # 添加标题框
    title_rect_corners = [
        (100, -100),
        (2000, -100),
        (2000, -50),
        (100, -50),
        (100, -100)
    ]
    modelspace.add_lwpolyline(title_rect_corners, dxfattribs={'layer': 'DECORATION'})
    modelspace.add_text(
        "某某工程建筑施工图",
        dxfattribs={
            'layer': 'TEXT',
            'height': 20,
            'insert': (1050, -80)
        }
    )
    
    # 添加图例框
    legend_corners = [
        (-200, 500),
        (100, 500),
        (100, 1000),
        (-200, 1000),
        (-200, 500)
    ]
    modelspace.add_lwpolyline(legend_corners, dxfattribs={'layer': 'DECORATION'})
    
    # 添加注释框
    note_corners = [
        (3000, 0),
        (3300, 0),
        (3300, 800),
        (3000, 800),
        (3000, 0)
    ]
    modelspace.add_lwpolyline(note_corners, dxfattribs={'layer': 'DECORATION'})
    
    # 保存文件
    filename = "test_48_frames.dxf"
    doc.saveas(filename)
    
    print(f"✅ 测试DXF文件已创建: {filename}")
    print(f"📊 包含:")
    print(f"   - 48个标准图框 (包含图签、执业章、出图章位置)")
    print(f"   - 3个干扰性矩形 (非图框)")
    print(f"   - 丰富的文本信息和表格结构")
    
    return filename

if __name__ == "__main__":
    try:
        test_file = create_test_dxf_with_frames()
        
        # 验证文件
        if os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            print(f"📏 文件大小: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        else:
            print("❌ 文件创建失败")
            
    except Exception as e:
        print(f"❌ 创建测试文件时发生错误: {e}")
        import traceback
        traceback.print_exc() 