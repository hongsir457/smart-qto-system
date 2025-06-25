from app.database import get_db
from app.models.drawing import Drawing
import json

# 获取数据库会话
db_gen = get_db()
db = next(db_gen)

# 查询图纸
drawing = db.query(Drawing).first()

if drawing:
    print('🔍 检查真实OCR结果存储位置')
    print('='*60)
    
    # 检查recognition_results
    if drawing.recognition_results:
        rec_result = drawing.recognition_results
        print(f'📊 recognition_results:')
        print(f'  • 识别引擎: {rec_result.get("analysis_engine")}')
        print(f'  • 总OCR文本数: {rec_result.get("analysis_summary", {}).get("total_ocr_texts", 0)}')
        print(f'  • 成功处理图片: {rec_result.get("analysis_summary", {}).get("successful_images", 0)}')
        print(f'  • 构件数量: {rec_result.get("total_components", 0)}')
        print(f'  • 处理时间: {rec_result.get("processing_time", 0):.2f}秒')
        
        # 检查是否有components详情
        components = rec_result.get("components", [])
        if components:
            print(f'  • 构件详情: {len(components)}个')
            for i, comp in enumerate(components[:3]):  # 显示前3个
                print(f'    [{i+1}] {comp}')
        else:
            print(f'  • 构件详情: 无')
    
    # 检查processing_result
    print(f'\n📋 processing_result:')
    if drawing.processing_result:
        proc_result = json.loads(drawing.processing_result) if isinstance(drawing.processing_result, str) else drawing.processing_result
        print(f'  • 状态: {proc_result.get("status")}')
        print(f'  • 处理类型: {proc_result.get("processing_type")}')
        
        # 检查ocr_result
        ocr_result = proc_result.get("ocr_result", {})
        if ocr_result:
            text_regions = ocr_result.get("text_regions", [])
            print(f'  • OCR文本数: {len(text_regions)}个')
            statistics = ocr_result.get("statistics", {})
            print(f'  • 统计信息: {statistics}')
    
    # 检查ocr_results（向后兼容字段）
    print(f'\n📄 ocr_results（向后兼容）:')
    if drawing.ocr_results:
        if isinstance(drawing.ocr_results, str):
            ocr_data = json.loads(drawing.ocr_results)
        else:
            ocr_data = drawing.ocr_results
        
        text_regions = ocr_data.get("text_regions", [])
        print(f'  • 文本数量: {len(text_regions)}个')
        statistics = ocr_data.get("statistics", {})
        print(f'  • 统计信息: {statistics}')
    
    print('\n' + '='*60)
    print('🎯 结论分析:')
    
    # 比较数据源
    recognition_ocr_count = drawing.recognition_results.get("analysis_summary", {}).get("total_ocr_texts", 0) if drawing.recognition_results else 0
    processing_ocr_count = 0
    if drawing.processing_result:
        proc_result = json.loads(drawing.processing_result) if isinstance(drawing.processing_result, str) else drawing.processing_result
        ocr_result = proc_result.get("ocr_result", {})
        processing_ocr_count = len(ocr_result.get("text_regions", []))
    
    compat_ocr_count = 0
    if drawing.ocr_results:
        if isinstance(drawing.ocr_results, str):
            ocr_data = json.loads(drawing.ocr_results)
        else:
            ocr_data = drawing.ocr_results
        compat_ocr_count = len(ocr_data.get("text_regions", []))
    
    print(f'  • recognition_results中的OCR文本数: {recognition_ocr_count}')
    print(f'  • processing_result中的OCR文本数: {processing_ocr_count}')
    print(f'  • ocr_results中的OCR文本数: {compat_ocr_count}')
    
    if recognition_ocr_count > processing_ocr_count and recognition_ocr_count > compat_ocr_count:
        print('  ✅ 真实OCR结果应该在recognition_results中！')
        print('  💡 建议: 前端应该从recognition_results获取真实的OCR数据')
    elif processing_ocr_count == compat_ocr_count and processing_ocr_count > 0:
        print('  ⚠️ processing_result和ocr_results显示相同的测试数据')
        print('  💡 建议: 需要重新执行真实的OCR识别')
    else:
        print('  ❓ 数据状态异常，需要进一步检查')

else:
    print('❌ 未找到图纸记录') 