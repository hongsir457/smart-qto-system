from app.database import get_db
from app.models.drawing import Drawing
import json

session = next(get_db())
drawing = session.query(Drawing).filter(Drawing.id == 1).first()

print("=== 寻找70个OCR文本 ===")

rr = drawing.recognition_results
if rr:
    print("analysis_summary:", rr.get('analysis_summary'))
    print()
    
    # 深度搜索所有可能包含OCR文本的字段
    def search_ocr_texts(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                if isinstance(value, list) and len(value) > 10:  # 可能是OCR文本列表
                    print(f"发现列表字段: {new_path}, 长度: {len(value)}")
                    if value and isinstance(value[0], (str, dict)):
                        print(f"  前3个项目: {value[:3]}")
                elif isinstance(value, (dict, list)):
                    search_ocr_texts(value, new_path)
    
    search_ocr_texts(rr)
    
    # 特别检查components字段
    components = rr.get('components', [])
    print(f"\ncomponents数量: {len(components)}")
    if components:
        print("前3个components:")
        for i, comp in enumerate(components[:3]):
            print(f"  {i+1}: {comp}")

session.close() 