import requests
import json

# 测试API端点
api_url = "http://127.0.0.1:8000/api/v1/drawings/1"

try:
    response = requests.get(api_url)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ API调用成功")
        print(f"图纸ID: {data.get('id')}")
        print(f"文件名: {data.get('filename')}")
        
        recognition_results = data.get('recognition_results')
        if recognition_results:
            print(f"\n=== OCR识别结果结构 ===")
            print(f"顶级键: {list(recognition_results.keys())}")
            
            # 检查OCR文本
            ocr_texts = recognition_results.get('ocr_texts', [])
            print(f"\n原始OCR文本: {len(ocr_texts)} 条")
            for i, text in enumerate(ocr_texts[:3]):
                print(f"  {i+1}. {text}")
            
            # 检查构件
            components = recognition_results.get('components', [])
            print(f"\n构件数据: {len(components)} 个")
            for i, comp in enumerate(components[:3]):
                print(f"  {i+1}. {comp.get('component_id')} - {comp.get('component_type')}")
                
        else:
            print("❌ 没有识别结果")
            
    else:
        print(f"❌ API调用失败: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ 错误: {e}") 