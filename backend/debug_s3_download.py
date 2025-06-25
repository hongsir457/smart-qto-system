#!/usr/bin/env python3
"""
调试S3下载问题的脚本
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.s3_service import s3_service
from app.database import SessionLocal
from app.models.drawing import Drawing

def test_s3_download_for_failed_drawings():
    """测试失败图纸的S3下载"""
    print("🔍 调试失败图纸的S3下载问题")
    
    db = SessionLocal()
    try:
        # 获取失败的图纸
        failed_drawings = db.query(Drawing).filter(
            Drawing.status == "failed",
            Drawing.s3_key.isnot(None)
        ).limit(3).all()
        
        print(f"📋 找到 {len(failed_drawings)} 个失败的图纸")
        
        for drawing in failed_drawings:
            print(f"\n🔍 测试图纸 {drawing.id}: {drawing.filename}")
            print(f"📁 S3键: {drawing.s3_key}")
            print(f"❌ 错误信息: {drawing.error_message}")
            
            # 测试下载
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{drawing.file_type}") as temp_file:
                temp_path = temp_file.name
            
            try:
                # 尝试下载文件
                print(f"📥 尝试下载到: {temp_path}")
                
                download_success = s3_service.download_file(
                    s3_key=drawing.s3_key,
                    local_path=temp_path
                )
                
                if download_success:
                    file_size = os.path.getsize(temp_path)
                    print(f"✅ 下载成功，文件大小: {file_size} 字节")
                    
                    # 如果是PDF，检查文件头
                    if drawing.file_type and drawing.file_type.lower() == 'pdf':
                        try:
                            with open(temp_path, 'rb') as f:
                                header = f.read(16)
                                print(f"📄 PDF文件头: {header}")
                                
                                if header.startswith(b'%PDF'):
                                    print("✅ PDF文件头正确")
                                else:
                                    print("❌ PDF文件头无效")
                        except Exception as e:
                            print(f"❌ 读取文件头失败: {e}")
                    
                    # 尝试用我们的处理器处理
                    from app.services.file_processor import FileProcessor
                    processor = FileProcessor()
                    
                    print("🔄 尝试用FileProcessor处理...")
                    result = processor.process_file(temp_path, drawing.file_type)
                    
                    print(f"📊 处理结果:")
                    print(f"  状态: {result.get('status')}")
                    print(f"  错误: {result.get('error')}")
                    print(f"  方法: {result.get('processing_method')}")
                    
                else:
                    print("❌ 下载失败")
                
            except Exception as e:
                print(f"❌ 测试异常: {e}")
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
                    
    finally:
        db.close()

def test_s3_service_status():
    """测试S3服务状态"""
    print("\n🔍 检查S3服务状态")
    
    print(f"📁 使用本地存储: {s3_service.use_local_storage}")
    
    if s3_service.use_local_storage:
        print(f"📂 本地存储路径: {s3_service.local_storage_path}")
        print(f"📂 本地存储路径存在: {s3_service.local_storage_path.exists()}")
        
        # 列出drawings文件夹内容
        drawings_path = s3_service.local_storage_path / "drawings"
        if drawings_path.exists():
            files = list(drawings_path.glob("*.pdf"))
            print(f"📄 drawings文件夹中的PDF文件: {len(files)} 个")
            for file in files[:5]:  # 只显示前5个
                size = file.stat().st_size
                print(f"  - {file.name}: {size} 字节")
        else:
            print("❌ drawings文件夹不存在")
    else:
        print(f"☁️ S3配置:")
        print(f"  Endpoint: {getattr(s3_service, 'endpoint_url', 'N/A')}")
        print(f"  Bucket: {getattr(s3_service, 'bucket_name', 'N/A')}")

def main():
    """主函数"""
    print("🚀 S3下载问题调试工具")
    print("=" * 50)
    
    test_s3_service_status()
    test_s3_download_for_failed_drawings()
    
    print("\n" + "=" * 50)
    print("🎯 调试完成")

if __name__ == "__main__":
    main() 