#!/usr/bin/env python3
"""
调试PDF处理问题的脚本
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.file_processor import FileProcessor
from app.database import SessionLocal
from app.models.drawing import Drawing

def create_test_pdf():
    """创建一个简单的测试PDF文件"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # 创建临时PDF文件
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf.close()
        
        # 使用reportlab创建一个简单的PDF
        c = canvas.Canvas(temp_pdf.name, pagesize=letter)
        c.drawString(100, 750, "测试PDF文件")
        c.drawString(100, 700, "这是一个用于调试的测试文件")
        c.showPage()
        c.save()
        
        print(f"✅ 创建测试PDF: {temp_pdf.name}")
        return temp_pdf.name
        
    except ImportError:
        print("❌ reportlab未安装，无法创建测试PDF")
        return None
    except Exception as e:
        print(f"❌ 创建测试PDF失败: {e}")
        return None

def test_pdf_processing():
    """测试PDF处理功能"""
    print("🧪 开始测试PDF处理功能")
    
    # 创建测试PDF
    test_pdf_path = create_test_pdf()
    if not test_pdf_path:
        print("❌ 无法创建测试PDF，跳过测试")
        return False
    
    try:
        # 创建文件处理器
        processor = FileProcessor()
        
        # 检查文件
        print(f"📄 测试文件: {test_pdf_path}")
        print(f"📏 文件大小: {os.path.getsize(test_pdf_path)} 字节")
        
        # 处理PDF
        result = processor.process_pdf(test_pdf_path)
        
        print(f"📊 处理结果:")
        print(f"  状态: {result.get('status')}")
        print(f"  方法: {result.get('processing_method')}")
        print(f"  图片数量: {len(result.get('image_paths', []))}")
        
        if result.get('status') == 'error':
            print(f"  错误: {result.get('error')}")
            return False
        else:
            print("✅ PDF处理成功")
            return True
            
    except Exception as e:
        print(f"❌ PDF处理测试异常: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            if test_pdf_path and os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
                print(f"🗑️ 清理测试文件: {test_pdf_path}")
        except:
            pass

def test_empty_pdf():
    """测试空PDF文件的处理"""
    print("\n🧪 测试空PDF文件处理")
    
    # 创建空文件
    temp_empty = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_empty.close()
    
    try:
        processor = FileProcessor()
        result = processor.process_pdf(temp_empty.name)
        
        print(f"📊 空文件处理结果:")
        print(f"  状态: {result.get('status')}")
        print(f"  错误: {result.get('error')}")
        
        if result.get('status') == 'error' and 'empty' in str(result.get('error', '')).lower():
            print("✅ 空文件错误处理正确")
            return True
        else:
            print("❌ 空文件错误处理不正确")
            return False
            
    finally:
        os.unlink(temp_empty.name)

def check_recent_drawings():
    """检查最近的图纸记录"""
    print("\n🔍 检查最近的图纸记录")
    
    db = SessionLocal()
    try:
        # 获取最近的图纸
        recent_drawings = db.query(Drawing).order_by(Drawing.id.desc()).limit(5).all()
        
        for drawing in recent_drawings:
            print(f"📋 图纸 {drawing.id}:")
            print(f"  文件名: {drawing.filename}")
            print(f"  状态: {drawing.status}")
            print(f"  文件类型: {drawing.file_type}")
            print(f"  S3键: {drawing.s3_key}")
            print(f"  错误信息: {drawing.error_message}")
            print("---")
            
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 PDF处理调试工具")
    print("=" * 50)
    
    # 检查最近的图纸记录
    check_recent_drawings()
    
    # 测试PDF处理
    test1_result = test_pdf_processing()
    test2_result = test_empty_pdf()
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果汇总:")
    print(f"  正常PDF处理: {'✅' if test1_result else '❌'}")
    print(f"  空PDF处理: {'✅' if test2_result else '❌'}")
    
    if test1_result and test2_result:
        print("🎉 PDF处理功能测试通过")
    else:
        print("⚠️ PDF处理功能存在问题")

if __name__ == "__main__":
    main() 