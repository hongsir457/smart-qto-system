from app.database import get_db
from app.models.drawing import Drawing
import json

def deep_search(obj, path="", max_depth=5):
    """深度搜索数据结构"""
    if max_depth <= 0:
        return
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            
            if isinstance(value, list):
                print(f"列表字段: {new_path}, 长度: {len(value)}")
                if value and len(value) <= 5:  # 显示小列表的内容
                    print(f"  内容: {value}")
                elif value and len(value) > 5:  # 大列表显示样例
                    print(f"  前3个项目: {value[:3]}")
                    print(f"  样例项目类型: {type(value[0])}")
                    
            elif isinstance(value, str) and len(value) > 100:
                print(f"长字符串字段: {new_path}, 长度: {len(value)}")
                print(f"  开头: {value[:100]}...")
                
            elif isinstance(value, dict):
                print(f"字典字段: {new_path}, keys: {list(value.keys())}")
                deep_search(value, new_path, max_depth - 1)
                
            else:
                print(f"字段: {new_path} = {value} ({type(value).__name__})")
    
    elif isinstance(obj, list) and len(obj) > 0:
        print(f"列表内容类型: {type(obj[0])}")
        if isinstance(obj[0], dict):
            print(f"  第一个dict的keys: {list(obj[0].keys())}")

session = next(get_db())
drawing = session.query(Drawing).filter(Drawing.id == 1).first()

print("=== 深度搜索数据结构 ===")
print()

print("1. recognition_results结构:")
if drawing.recognition_results:
    deep_search(drawing.recognition_results, "recognition_results", 3)
print()

print("2. processing_result结构:")
if drawing.processing_result:
    deep_search(drawing.processing_result, "processing_result", 3)
print()

print("3. ocr_results结构:")
if drawing.ocr_results:
    deep_search(drawing.ocr_results, "ocr_results", 3)
else:
    print("ocr_results为空")

session.close() 