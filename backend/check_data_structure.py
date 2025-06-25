from app.database import get_db
from app.models.drawing import Drawing
import json

def check_drawing_data():
    session = next(get_db())
    drawing = session.query(Drawing).filter(Drawing.id == 1).first()
    
    print("=== 图纸1的数据结构检查 ===")
    print(f"文件名: {drawing.filename}")
    print(f"状态: {drawing.status}")
    print()
    
    print("数据库字段存在情况:")
    print(f"  recognition_results: {'✅' if drawing.recognition_results else '❌'}")
    print(f"  processing_result: {'✅' if drawing.processing_result else '❌'}")
    print(f"  ocr_results: {'✅' if drawing.ocr_results else '❌'}")
    print()
    
    if drawing.processing_result:
        pr = drawing.processing_result
        print("processing_result字段结构:")
        for key, value in pr.items():
            print(f"  {key}: {type(value).__name__}")
            if key.startswith('result_') and isinstance(value, dict):
                if 's3_url' in value:
                    print(f"    s3_url: {value['s3_url']}")
        print()
    
    if drawing.recognition_results:
        rr = drawing.recognition_results
        print("recognition_results字段结构:")
        if isinstance(rr, dict):
            for key, value in rr.items():
                print(f"  {key}: {type(value).__name__}")
        print()
    
    if drawing.ocr_results:
        ocr = drawing.ocr_results
        print("ocr_results字段结构:")
        if isinstance(ocr, dict):
            for key, value in ocr.items():
                print(f"  {key}: {type(value).__name__}")
        print()
    
    session.close()

if __name__ == "__main__":
    check_drawing_data() 