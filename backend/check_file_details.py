from app.database import get_db
from app.models.drawing import Drawing
import json
import os

# 获取数据库会话
db_gen = get_db()
db = next(db_gen)

# 查询图纸
drawing = db.query(Drawing).first()

if drawing:
    print(f'📊 图纸详细信息:')
    print(f'  ID: {drawing.id}')
    print(f'  文件名: {drawing.filename}')
    print(f'  状态: {drawing.status}')
    print(f'  创建时间: {drawing.created_at}')
    print(f'  更新时间: {drawing.updated_at}')
    print(f'  文件大小: {drawing.file_size} bytes')
    print(f'  文件类型: {drawing.file_type}')
    print(f'  本地文件路径: {drawing.file_path}')
    print(f'  S3存储键: {drawing.s3_key}')
    print(f'  S3存储URL: {drawing.s3_url}')
    print(f'  S3存储桶: {drawing.s3_bucket}')
    print(f'  任务ID: {drawing.task_id}')
    
    # 检查本地文件是否存在
    if drawing.file_path:
        if os.path.exists(drawing.file_path):
            print(f'  ✅ 本地文件存在')
        else:
            print(f'  ❌ 本地文件不存在')
    else:
        print(f'  ❓ 没有本地文件路径')
    
    # 检查OCR结果来源
    print(f'\n🔍 OCR结果分析:')
    if drawing.ocr_results:
        try:
            ocr_data = json.loads(drawing.ocr_results)
            print(f'  OCR数据来源分析:')
            
            # 检查坐标框
            if 'text_regions' in ocr_data:
                regions = ocr_data['text_regions']
                has_realistic_coords = False
                for region in regions:
                    if 'bbox' in region:
                        bbox = region['bbox']
                        if isinstance(bbox, dict):
                            # 检查坐标是否为整数且规律
                            x_coords = [bbox.get('x_min', 0), bbox.get('x_max', 0)]
                            y_coords = [bbox.get('y_min', 0), bbox.get('y_max', 0)]
                            
                            # 如果所有坐标都是100的倍数，可能是测试数据
                            is_round_numbers = all(x % 50 == 0 for x in x_coords + y_coords)
                            if is_round_numbers:
                                print(f'    ⚠️ 坐标过于规整，疑似测试数据: {bbox}')
                            else:
                                has_realistic_coords = True
                                
                if not has_realistic_coords:
                    print(f'    ❌ 所有坐标都过于规整，这很可能是测试数据而非真实OCR结果')
                else:
                    print(f'    ✅ 坐标看起来像真实的OCR识别结果')
            
            # 检查置信度分布
            confidences = []
            for region in ocr_data.get('text_regions', []):
                if 'confidence' in region:
                    confidences.append(region['confidence'])
            
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                # 检查置信度是否过于完美
                high_conf_count = sum(1 for c in confidences if c >= 0.9)
                if high_conf_count == len(confidences) and all(c in [0.92, 0.95, 0.98] for c in confidences):
                    print(f'    ⚠️ 置信度过于完美，疑似人工设定: {confidences}')
                else:
                    print(f'    置信度分布: {confidences}')
            
        except Exception as e:
            print(f'    ❌ OCR数据解析失败: {e}')
    
    # 检查处理结果
    print(f'\n📋 处理结果分析:')
    if drawing.processing_result:
        try:
            if isinstance(drawing.processing_result, str):
                proc_result = json.loads(drawing.processing_result)
            else:
                proc_result = drawing.processing_result
            
            print(f'  处理结果键: {list(proc_result.keys()) if proc_result else "无"}')
            
            if 'ocr_results' in proc_result:
                ocr_in_proc = proc_result['ocr_results']
                if isinstance(ocr_in_proc, dict) and 'processing_engine' in ocr_in_proc:
                    engine = ocr_in_proc['processing_engine']
                    print(f'  OCR引擎: {engine}')
                    
                    # 检查是否有文本块数据
                    if 'total_text_blocks' in ocr_in_proc:
                        print(f'  文本块数: {ocr_in_proc["total_text_blocks"]}')
                    if 'texts' in ocr_in_proc:
                        print(f'  识别文本: {ocr_in_proc["texts"][:3]}...' if len(ocr_in_proc["texts"]) > 3 else ocr_in_proc["texts"])
                        
                        # 对比识别文本和当前OCR结果
                        current_texts = [r['text'] for r in ocr_data.get('text_regions', [])]
                        if set(ocr_in_proc["texts"]) != set(current_texts):
                            print(f'    ⚠️ 处理结果中的文本与当前OCR结果不匹配!')
                            print(f'    处理结果文本: {ocr_in_proc["texts"]}')
                            print(f'    当前OCR文本: {current_texts}')
                            
        except Exception as e:
            print(f'  ❌ 处理结果解析失败: {e}')
            
    # 最终判断
    print(f'\n🎯 结论:')
    
    # 检查多个证据
    evidence_count = 0
    
    # 证据1: 文件路径和实际文件
    if not drawing.file_path or not os.path.exists(drawing.file_path or ''):
        print(f'  🔴 证据1: 没有实际的图纸文件')
        evidence_count += 1
    else:
        print(f'  🟢 证据1: 有实际的图纸文件')
    
    # 证据2: OCR结果的坐标规整程度
    if drawing.ocr_results:
        ocr_data = json.loads(drawing.ocr_results)
        regions = ocr_data.get('text_regions', [])
        if regions and all('bbox' in r for r in regions):
            all_coords = []
            for r in regions:
                bbox = r['bbox']
                all_coords.extend([bbox.get('x_min', 0), bbox.get('x_max', 0), 
                                 bbox.get('y_min', 0), bbox.get('y_max', 0)])
            
            # 如果所有坐标都是50的倍数，很可能是测试数据
            if all(x % 50 == 0 for x in all_coords):
                print(f'  🔴 证据2: OCR坐标过于规整，疑似测试数据')
                evidence_count += 1
            else:
                print(f'  🟢 证据2: OCR坐标看起来真实')
    
    # 证据3: 置信度分布
    if drawing.ocr_results:
        ocr_data = json.loads(drawing.ocr_results)
        confidences = [r.get('confidence', 0) for r in ocr_data.get('text_regions', [])]
        if confidences and all(c in [0.92, 0.95, 0.98] for c in confidences):
            print(f'  🔴 证据3: 置信度数值过于完美，疑似人工设定')
            evidence_count += 1
        else:
            print(f'  🟢 证据3: 置信度分布看起来正常')
    
    if evidence_count >= 2:
        print(f'  \n❌ 综合判断: 这很可能是测试数据，而不是真实的图纸OCR识别结果')
        print(f'     建议: 上传真实图纸进行OCR识别测试')
    else:
        print(f'  \n✅ 综合判断: 这看起来是真实的OCR识别结果')

else:
    print('❌ 没有找到图纸记录') 