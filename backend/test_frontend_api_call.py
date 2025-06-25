#!/usr/bin/env python3
"""测试前端API调用"""

import requests
import json
from app.core.security import create_access_token

def test_frontend_api():
    print("🔍 测试前端API调用")
    print("=" * 60)
    
    # 创建测试token
    token = create_access_token(data={"sub": "1"})
    print(f"🔑 生成测试token: {token[:50]}...")
    
    # 模拟前端API调用
    api_url = "http://localhost:8000/api/v1/drawings/1"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"📡 请求URL: {api_url}")
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API调用成功")
            
            print(f"\n📋 图纸基本信息:")
            print(f"  ID: {data.get('id')}")
            print(f"  文件名: {data.get('filename')}")
            print(f"  状态: {data.get('status')}")
            
            print(f"\n🔍 recognition_results检查:")
            rr = data.get('recognition_results')
            if rr:
                print(f"  类型: {type(rr)}")
                print(f"  字段: {list(rr.keys()) if isinstance(rr, dict) else 'not dict'}")
                if 'analysis_summary' in rr:
                    summary = rr['analysis_summary']
                    print(f"  ✅ analysis_summary: {summary}")
                    print(f"  ✅ total_ocr_texts: {summary.get('total_ocr_texts')}")
            else:
                print("  ❌ recognition_results为空")
                
            print(f"\n🔍 processing_result检查:")
            pr = data.get('processing_result')
            if pr:
                print(f"  类型: {type(pr)}")
                if isinstance(pr, str):
                    try:
                        pr_obj = json.loads(pr)
                        print(f"  解析后字段: {list(pr_obj.keys())}")
                        if 'human_readable_txt' in pr_obj:
                            hrt = pr_obj['human_readable_txt']
                            print(f"  ✅ human_readable_txt:")
                            print(f"    S3 URL: {hrt.get('s3_url')}")
                            print(f"    是否可读: {hrt.get('is_human_readable')}")
                            print(f"    总文本数: {hrt.get('total_ocr_texts')}")
                        else:
                            print("  ❌ 没有human_readable_txt字段")
                    except Exception as e:
                        print(f"  ❌ JSON解析失败: {e}")
                elif isinstance(pr, dict):
                    print(f"  字段: {list(pr.keys())}")
                    if 'human_readable_txt' in pr:
                        hrt = pr['human_readable_txt']
                        print(f"  ✅ human_readable_txt:")
                        print(f"    S3 URL: {hrt.get('s3_url')}")
                        print(f"    是否可读: {hrt.get('is_human_readable')}")
                        print(f"    总文本数: {hrt.get('total_ocr_texts')}")
                    else:
                        print("  ❌ 没有human_readable_txt字段")
            else:
                print("  ❌ processing_result为空")
                
            # 模拟前端数据处理逻辑
            print(f"\n🔧 模拟前端数据处理:")
            
            # 检查extractRealOcrData逻辑
            if (rr and rr.get('analysis_summary') and 
                rr['analysis_summary'].get('total_ocr_texts', 0) > 0):
                print("  ✅ extractRealOcrData应该能提取到真实OCR数据")
                print(f"    source: recognition_results")
                print(f"    real_ocr_count: {rr['analysis_summary']['total_ocr_texts']}")
                
                # 检查handleRecognitionResults逻辑
                if pr:
                    if isinstance(pr, str):
                        pr_obj = json.loads(pr)
                    else:
                        pr_obj = pr
                        
                    humanReadableTxt = pr_obj.get('human_readable_txt')
                    if (humanReadableTxt and humanReadableTxt.get('s3_url') and 
                        humanReadableTxt.get('is_human_readable')):
                        print("  ✅ 应该调用handleHumanReadableTxt")
                        print(f"    S3 URL: {humanReadableTxt['s3_url']}")
                        
                        # 测试S3链接
                        s3_url = humanReadableTxt['s3_url']
                        try:
                            s3_response = requests.get(s3_url, timeout=10)
                            if s3_response.status_code == 200:
                                content = s3_response.text
                                print(f"  ✅ S3内容获取成功，长度: {len(content)} 字符")
                                print(f"  📄 内容预览: {content[:200]}...")
                            else:
                                print(f"  ❌ S3内容获取失败: {s3_response.status_code}")
                        except Exception as e:
                            print(f"  ❌ S3访问失败: {e}")
                    else:
                        print("  ❌ human_readable_txt不完整，会显示基本统计信息")
                        print(f"    humanReadableTxt: {humanReadableTxt}")
                else:
                    print("  ❌ processing_result为空，会显示基本统计信息")
            else:
                print("  ❌ recognition_results不完整，可能无法提取真实OCR数据")
                
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    test_frontend_api() 