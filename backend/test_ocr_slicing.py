#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能切片OCR测试脚本
验证PaddleOCR + 智能切片的集成效果
"""

import asyncio
import logging
import time
from pathlib import Path
import sys
import os
from PIL import Image, ImageDraw, ImageFont
import tempfile

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ocr.paddle_ocr_service import PaddleOCRService
from app.services.ocr.paddle_ocr_with_slicing import PaddleOCRWithSlicing

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_image(width: int = 3000, height: int = 4000, text_count: int = 20) -> str:
    """创建测试图像"""
    
    # 创建白色背景图像
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 尝试使用系统字体
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 40)  # Windows中文字体
        except:
            font = ImageFont.load_default()
    
    # 添加标题
    title_text = "建筑结构图纸 - 智能切片OCR测试"
    title_bbox = draw.textbbox((0, 0), title_text, font=font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, 50), title_text, fill='black', font=font)
    
    # 添加各种文本内容
    test_texts = [
        "C1柱 400×400",
        "主梁 300×600", 
        "次梁 250×500",
        "楼板厚度120mm",
        "墙体厚度200mm",
        "基础埋深-2.5m",
        "楼梯间",
        "电梯井",
        "卫生间",
        "厨房",
        "客厅",
        "卧室",
        "阳台",
        "走廊",
        "设备房",
        "强电井",
        "弱电井",
        "消防通道",
        "安全出口",
        "疏散楼梯"
    ]
    
    # 在图像上随机分布文本
    import random
    random.seed(42)  # 固定种子以获得一致的结果
    
    for i, text in enumerate(test_texts[:text_count]):
        x = random.randint(100, width - 300)
        y = random.randint(150, height - 100)
        
        # 添加背景框
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 绘制背景矩形
        draw.rectangle([x-5, y-5, x+text_width+5, y+text_height+5], outline='blue', width=2)
        
        # 绘制文本
        draw.text((x, y), text, fill='black', font=font)
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        img.save(tmp_file.name, 'PNG', dpi=(300, 300))
        logger.info(f"测试图像已创建: {tmp_file.name}, 尺寸: {width}x{height}")
        return tmp_file.name

async def test_ocr_service_basic():
    """测试基础OCR服务"""
    print("\n🧪 测试1: 基础OCR服务")
    print("=" * 50)
    
    # 创建测试图像
    test_image = create_test_image(1024, 1024, 10)  # 小图像，不会触发切片
    
    try:
        # 初始化服务
        ocr_service = PaddleOCRService()
        
        if not ocr_service.is_available():
            print("❌ OCR服务不可用")
            return False
        
        print(f"✅ OCR服务状态: {ocr_service.get_status()}")
        
        # 执行OCR
        start_time = time.time()
        result = await ocr_service.process_image_async(test_image, use_slicing=False)
        processing_time = time.time() - start_time
        
        print(f"✅ 处理完成，耗时: {processing_time:.2f}s")
        print(f"✅ 处理方法: {result.get('processing_method', 'unknown')}")
        print(f"✅ 识别文本区域: {result.get('statistics', {}).get('total_regions', 0)}")
        print(f"✅ 平均置信度: {result.get('statistics', {}).get('avg_confidence', 0):.2f}")
        
        # 显示识别的文本
        texts = result.get('texts', [])
        if texts:
            print(f"✅ 识别的文本内容:")
            for i, text_info in enumerate(texts[:5]):  # 只显示前5个
                text = text_info.get('text', '')
                confidence = text_info.get('confidence', 0)
                print(f"   {i+1}. {text} (置信度: {confidence:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础OCR测试失败: {e}")
        return False
    
    finally:
        # 清理测试文件
        try:
            os.unlink(test_image)
        except:
            pass

async def test_ocr_with_auto_slicing():
    """测试自动切片OCR"""
    print("\n🧪 测试2: 自动切片OCR")
    print("=" * 50)
    
    # 创建大图像，会触发自动切片
    test_image = create_test_image(3000, 4000, 20)
    
    try:
        # 初始化服务
        ocr_service = PaddleOCRService()
        
        # 执行自动判断的OCR
        start_time = time.time()
        result = await ocr_service.process_image_async(test_image, use_slicing=None)  # 自动判断
        processing_time = time.time() - start_time
        
        print(f"✅ 处理完成，耗时: {processing_time:.2f}s")
        print(f"✅ 处理方法: {result.get('processing_method', 'unknown')}")
        print(f"✅ 识别文本区域: {result.get('statistics', {}).get('total_regions', 0)}")
        print(f"✅ 平均置信度: {result.get('statistics', {}).get('avg_confidence', 0):.2f}")
        
        # 如果使用了切片，显示切片信息
        slicing_info = result.get('slicing_info', {})
        if slicing_info:
            print(f"✅ 切片信息:")
            print(f"   总切片数: {slicing_info.get('total_slices', 0)}")
            print(f"   成功切片数: {slicing_info.get('successful_slices', 0)}")
            print(f"   成功率: {slicing_info.get('success_rate', 0):.2%}")
        
        # 显示处理摘要
        processing_summary = result.get('processing_summary', {})
        if processing_summary:
            ocr_stats = processing_summary.get('ocr_statistics', {})
            print(f"✅ OCR统计:")
            print(f"   去重前文本区域: {ocr_stats.get('total_text_regions_before_dedup', 0)}")
            print(f"   去重后文本区域: {ocr_stats.get('total_text_regions_after_dedup', 0)}")
            print(f"   去重率: {ocr_stats.get('deduplication_rate', 0):.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 自动切片OCR测试失败: {e}")
        return False
    
    finally:
        # 清理测试文件
        try:
            os.unlink(test_image)
        except:
            pass

async def test_forced_slicing():
    """测试强制切片OCR"""
    print("\n🧪 测试3: 强制切片OCR")
    print("=" * 50)
    
    # 创建中等大小图像
    test_image = create_test_image(2000, 2500, 15)
    
    try:
        # 初始化服务
        ocr_service = PaddleOCRService()
        
        # 执行强制切片OCR
        start_time = time.time()
        result = await ocr_service.process_with_slicing_forced(test_image, "test_forced")
        processing_time = time.time() - start_time
        
        print(f"✅ 强制切片处理完成，耗时: {processing_time:.2f}s")
        print(f"✅ 识别文本区域: {result.get('statistics', {}).get('total_regions', 0)}")
        print(f"✅ 平均置信度: {result.get('statistics', {}).get('avg_confidence', 0):.2f}")
        
        slicing_info = result.get('slicing_info', {})
        print(f"✅ 切片信息:")
        print(f"   总切片数: {slicing_info.get('total_slices', 0)}")
        print(f"   成功切片数: {slicing_info.get('successful_slices', 0)}")
        print(f"   成功率: {slicing_info.get('success_rate', 0):.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 强制切片OCR测试失败: {e}")
        return False
    
    finally:
        # 清理测试文件
        try:
            os.unlink(test_image)
        except:
            pass

async def test_method_comparison():
    """测试方法比较"""
    print("\n🧪 测试4: 方法比较")
    print("=" * 50)
    
    # 创建大图像进行比较
    test_image = create_test_image(2500, 3000, 18)
    
    try:
        # 初始化服务
        ocr_service = PaddleOCRService()
        
        # 执行方法比较
        start_time = time.time()
        comparison_result = await ocr_service.compare_methods(test_image)
        processing_time = time.time() - start_time
        
        print(f"✅ 方法比较完成，总耗时: {processing_time:.2f}s")
        
        # 显示比较结果
        comparison = comparison_result.get('comparison', {})
        
        print(f"📊 直接OCR结果:")
        direct = comparison.get('direct_ocr', {})
        print(f"   成功: {direct.get('success', False)}")
        print(f"   文本区域: {direct.get('text_regions', 0)}")
        print(f"   平均置信度: {direct.get('avg_confidence', 0):.2f}")
        print(f"   处理时间: {direct.get('processing_time', 0):.2f}s")
        
        print(f"📊 切片OCR结果:")
        slicing = comparison.get('slicing_ocr', {})
        print(f"   成功: {slicing.get('success', False)}")
        print(f"   文本区域: {slicing.get('text_regions', 0)}")
        print(f"   平均置信度: {slicing.get('avg_confidence', 0):.2f}")
        print(f"   处理时间: {slicing.get('processing_time', 0):.2f}s")
        
        # 显示推荐方法
        recommendation = comparison.get('recommendation', {})
        print(f"🎯 推荐方法: {recommendation.get('method', 'unknown')}")
        print(f"🎯 推荐理由: {recommendation.get('reason', 'unknown')}")
        
        # 显示改进指标
        improvement = comparison.get('improvement', {})
        if improvement:
            print(f"📈 改进指标:")
            print(f"   文本区域改进: {improvement.get('text_regions_improvement', 0):.2%}")
            print(f"   置信度改进: {improvement.get('confidence_improvement', 0):.2f}")
            print(f"   处理时间比率: {improvement.get('processing_time_ratio', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 方法比较测试失败: {e}")
        return False
    
    finally:
        # 清理测试文件
        try:
            os.unlink(test_image)
        except:
            pass

async def test_slicing_service_directly():
    """直接测试切片OCR服务"""
    print("\n🧪 测试5: 直接测试切片OCR服务")
    print("=" * 50)
    
    # 创建大图像
    test_image = create_test_image(3500, 4500, 25)
    
    try:
        # 直接使用切片OCR服务
        slicing_service = PaddleOCRWithSlicing()
        
        if not slicing_service.is_available():
            print("❌ 切片OCR服务不可用")
            return False
        
        # 执行切片OCR
        start_time = time.time()
        merged_result = await slicing_service.process_image_with_slicing(
            image_path=test_image,
            task_id="test_direct_slicing",
            save_to_storage=False
        )
        processing_time = time.time() - start_time
        
        print(f"✅ 切片OCR处理完成，耗时: {processing_time:.2f}s")
        print(f"✅ 总切片数: {merged_result.total_slices}")
        print(f"✅ 成功切片数: {merged_result.successful_slices}")
        print(f"✅ 成功率: {merged_result.success_rate:.2%}")
        print(f"✅ 文本区域数: {merged_result.total_text_regions}")
        
        # 显示处理摘要
        summary = merged_result.processing_summary
        print(f"📊 处理摘要:")
        print(f"   原图尺寸: {summary['original_image']['width']}x{summary['original_image']['height']}")
        print(f"   总像素: {summary['original_image']['total_pixels']:,}")
        print(f"   去重率: {summary['ocr_statistics']['deduplication_rate']:.2%}")
        print(f"   平均置信度: {summary['ocr_statistics']['avg_confidence']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 直接切片OCR测试失败: {e}")
        return False
    
    finally:
        # 清理测试文件
        try:
            os.unlink(test_image)
        except:
            pass

async def main():
    """主测试函数"""
    print("🚀 智能切片OCR测试开始")
    print("=" * 60)
    
    # 测试列表
    tests = [
        ("基础OCR服务", test_ocr_service_basic),
        ("自动切片OCR", test_ocr_with_auto_slicing),
        ("强制切片OCR", test_forced_slicing),
        ("方法比较", test_method_comparison),
        ("直接切片服务", test_slicing_service_directly),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 执行测试: {test_name}")
            success = await test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
                
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
            results.append((test_name, False))
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 总体结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！智能切片OCR功能正常")
    else:
        print("⚠️ 部分测试失败，需要检查相关功能")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main()) 