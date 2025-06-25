from app.database import get_db
from app.models.drawing import Drawing
import json

def check_ocr_data():
    session = next(get_db())
    drawing = session.query(Drawing).filter(Drawing.id == 1).first()
    
    print("=== 图纸1的OCR数据内容检查 ===")
    print()
    
    if drawing.recognition_results:
        rr = drawing.recognition_results
        print("recognition_results详细内容:")
        print(f"  analysis_engine: {rr.get('analysis_engine')}")
        print(f"  source_type: {rr.get('source_type')}")
        print(f"  total_components: {rr.get('total_components')}")
        print()
        
        components = rr.get('components', [])
        print(f"  components数量: {len(components)}")
        if components:
            print("  前3个components示例:")
            for i, comp in enumerate(components[:3]):
                print(f"    {i+1}: {comp}")
        print()
        
        analysis_summary = rr.get('analysis_summary', {})
        print("  analysis_summary:")
        for key, value in analysis_summary.items():
            print(f"    {key}: {value}")
        print()
        
        # 检查是否有原始OCR文本数据
        if 'ocr_texts' in rr:
            ocr_texts = rr['ocr_texts']
            print(f"  ocr_texts数量: {len(ocr_texts)}")
            if ocr_texts:
                print("  前5个OCR文本示例:")
                for i, text in enumerate(ocr_texts[:5]):
                    print(f"    {i+1}: {text}")
        
        elif 'text_regions' in rr:
            text_regions = rr['text_regions']
            print(f"  text_regions数量: {len(text_regions)}")
            if text_regions:
                print("  前5个text_regions示例:")
                for i, region in enumerate(text_regions[:5]):
                    print(f"    {i+1}: {region}")
                    
        elif 'raw_ocr_data' in rr:
            raw_ocr = rr['raw_ocr_data']
            print(f"  raw_ocr_data类型: {type(raw_ocr)}")
            if isinstance(raw_ocr, list):
                print(f"  raw_ocr_data数量: {len(raw_ocr)}")
                if raw_ocr:
                    print("  前3个raw_ocr示例:")
                    for i, item in enumerate(raw_ocr[:3]):
                        print(f"    {i+1}: {item}")
    
    print()
    print("=== 检查S3相关信息 ===")
    
    if drawing.processing_result:
        pr = drawing.processing_result
        # 检查是否有任何S3相关信息
        s3_found = False
        for key, value in pr.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if 's3' in str(subkey).lower() or 'sealos' in str(subkey).lower():
                        print(f"  发现S3相关字段: {key}.{subkey} = {subvalue}")
                        s3_found = True
        
        if not s3_found:
            print("  ❌ 未发现任何S3存储信息")
    
    session.close()

if __name__ == "__main__":
    check_ocr_data() 