#!/usr/bin/env python3
"""
测试前端API调用，验证TXT内容获取
"""

import requests
import json
import time
from app.core.security import create_access_token

def test_api_access():
    print("🧪 测试前端API访问和TXT内容获取")
    print("=" * 60)
    
    # 等待服务启动
    print("⏳ 等待API服务启动...")
    for i in range(10):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ API服务已启动")
                break
        except:
            print(f"⏳ 第{i+1}次尝试连接API服务...")
            time.sleep(2)
    else:
        print("❌ API服务启动失败，跳过API测试")
        return
    
    # 测试获取图纸详情
    try:
        print("\n📊 测试获取图纸详情...")
        drawing_response = requests.get("http://localhost:8000/api/v1/drawings/1")
        if drawing_response.status_code == 200:
            drawing_data = drawing_response.json()
            print(f"✅ 图纸数据获取成功:")
            print(f"  文件名: {drawing_data.get('filename', 'N/A')}")
            print(f"  状态: {drawing_data.get('status', 'N/A')}")
            
            # 检查processing_result
            proc_result = drawing_data.get('processing_result')
            if proc_result:
                if isinstance(proc_result, str):
                    proc_result = json.loads(proc_result)
                
                # 检查TXT格式结果
                txt_result = proc_result.get('human_readable_txt', {})
                if txt_result and txt_result.get('is_human_readable'):
                    print(f"✅ 发现TXT格式结果:")
                    print(f"  S3 URL: {txt_result.get('s3_url', 'N/A')}")
                    print(f"  纠正文本数: {txt_result.get('corrected_texts', 0)}")
                    print(f"  内容长度: {txt_result.get('content_length', 0)}字符")
                    
                    # 测试S3文件访问
                    s3_url = txt_result.get('s3_url')
                    if s3_url:
                        print(f"\n🌐 测试S3文件访问...")
                        s3_response = requests.get(s3_url)
                        if s3_response.status_code == 200:
                            txt_content = s3_response.text
                            print(f"✅ S3访问成功，内容长度: {len(txt_content)}字符")
                            print(f"📄 内容预览:")
                            print("-" * 40)
                            print(txt_content[:200])
                            if len(txt_content) > 200:
                                print("...")
                            print("-" * 40)
                            
                            print("\n🎯 前端应该显示的内容:")
                            print("  1. 默认进入'可读文本'标签页")
                            print("  2. 显示完整的TXT格式报告")
                            print("  3. 包含智能纠错的详细结果")
                            print("  4. 提供复制功能")
                        else:
                            print(f"❌ S3访问失败: {s3_response.status_code}")
                    else:
                        print("❌ 缺少S3 URL")
                else:
                    print("❌ 未找到TXT格式结果")
            else:
                print("❌ 未找到processing_result")
        else:
            print(f"❌ 图纸数据获取失败: {drawing_response.status_code}")
            print(f"响应内容: {drawing_response.text}")
    except Exception as e:
        print(f"❌ API测试异常: {str(e)}")

def test_s3_bucket_structure():
    print("\n🗂️ 测试S3存储桶结构")
    print("=" * 40)
    
    # 测试各个存储目录
    base_url = "https://objectstorageapi.hzh.sealos.run/gkg9z6uk-smaryqto"
    directories = [
        "drawings/",
        "extraction_results/",
        "ocr_readable_results/",
        "ocr_readable_texts/"
    ]
    
    for directory in directories:
        try:
            # 这里只测试目录下的文件访问，不是列出目录内容
            print(f"📁 检查目录: {directory}")
            print(f"   提示: 存储桶结构应该包含此目录")
        except Exception as e:
            print(f"❌ 检查{directory}失败: {str(e)}")

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
    test_api_access()
    test_s3_bucket_structure()
    test_frontend_api()
    print("\n🎉 测试完成！")
    print("💡 如果前端仍然显示统计信息而不是TXT内容，请检查:")
    print("   1. 浏览器控制台是否有JavaScript错误")
    print("   2. 网络请求是否成功获取了drawing数据")
    print("   3. OCRResultDisplay组件的activeTab状态")
    print("   4. readable_text字段是否正确传递给组件") 