import requests
import json

# 测试图纸ID=3的API
api_url = "http://127.0.0.1:8000/api/v1/drawings/3"

try:
    # 先设置认证token
    token = "test_token_for_development"
    
    response = requests.get(api_url, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    })
    
    if response.status_code == 200:
        data = response.json()
        print("✅ API调用成功")
        print(f"返回的图纸ID: {data.get('id')}")
        print(f"返回的文件名: {data.get('filename')}")
        
        recognition_results = data.get('recognition_results')
        if recognition_results:
            ocr_texts = recognition_results.get('ocr_texts', [])
            print(f"\nAPI返回的OCR文本前5条:")
            for i, text in enumerate(ocr_texts[:5]):
                print(f"  {i+1}. {text}")
                
            components = recognition_results.get('components', [])
            print(f"\nAPI返回的构件前3个:")
            for i, comp in enumerate(components[:3]):
                print(f"  {i+1}. {comp.get('component_id')} - {comp.get('component_type')}")
        else:
            print("❌ API返回的数据中没有recognition_results")
            
    else:
        print(f"❌ API调用失败: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ 错误: {e}") 