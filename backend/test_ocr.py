import requests
import json

def test_ocr():
    base_url = "http://localhost:8000"
    
    # 测试API连接
    try:
        response = requests.get(f"{base_url}/api/v1/drawings/")
        print(f"API连接状态: {response.status_code}")
        
        if response.status_code == 200:
            drawings = response.json()
            print(f"图纸总数: {len(drawings)}")
            
            # 查找图纸43
            drawing_43 = None
            for drawing in drawings:
                if drawing['id'] == 43:
                    drawing_43 = drawing
                    break
            
            if drawing_43:
                print(f"\n=== 图纸43信息 ===")
                print(f"文件名: {drawing_43['filename']}")
                print(f"状态: {drawing_43['status']}")
                print(f"文件类型: {drawing_43['file_type']}")
                print(f"错误信息: {drawing_43.get('error_message', '无')}")
                
                # 尝试触发OCR
                print(f"\n=== 尝试触发OCR ===")
                ocr_response = requests.post(f"{base_url}/api/v1/drawings/43/ocr")
                print(f"OCR请求状态: {ocr_response.status_code}")
                print(f"OCR响应: {ocr_response.text}")
                
                # 检查OCR状态
                status_response = requests.get(f"{base_url}/api/v1/drawings/43/ocr/status")
                print(f"状态查询: {status_response.status_code}")
                print(f"状态响应: {status_response.text}")
                
            else:
                print("未找到图纸43")
        else:
            print(f"API连接失败: {response.text}")
            
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == "__main__":
    test_ocr() 