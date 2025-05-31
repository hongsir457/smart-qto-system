#!/usr/bin/env python3
"""
简化的文件上传和构件识别测试脚本
"""

import requests
import json
import os
import time

def test_upload_and_detect():
    """测试文件上传和构件识别功能"""
    
    print("🚀 文件上传和构件识别测试")
    print("=" * 50)
    
    # API基础配置
    base_url = "http://localhost:8000"
    
    # 1. 检查后端服务状态
    print("📡 检查后端服务...")
    try:
        api_response = requests.get(f"{base_url}/docs", timeout=5)
        print(f"✅ 后端API状态: {api_response.status_code}")
    except Exception as e:
        print(f"❌ 后端服务检查失败: {str(e)}")
        return
    
    # 2. 查找测试文件
    print("\n📁 查找测试文件...")
    test_files = [
        "../../一层柱结构改造加固平面图.pdf",
        "../../一层柱结构改造加固平面图.jpg", 
        "../../一层板结构改造加固平面图.pdf",
        "../../一层梁结构改造加固平面图.pdf",
        "complex_building_plan.png"
    ]
    
    upload_file = None
    for file_path in test_files:
        if os.path.exists(file_path):
            upload_file = file_path
            print(f"✅ 找到测试文件: {upload_file}")
            break
    
    if not upload_file:
        print("❌ 未找到测试文件")
        return
    
    # 3. 创建测试用户（如果需要）
    print("\n👤 创建测试用户...")
    try:
        user_data = {
            "email": "test@example.com",
            "password": "testpassword",
            "full_name": "Test User"
        }
        
        register_response = requests.post(
            f"{base_url}/api/v1/auth/register",
            json=user_data,
            timeout=10
        )
        
        if register_response.status_code in [200, 201]:
            print("✅ 测试用户创建成功")
        elif register_response.status_code == 400:
            print("ℹ️  测试用户已存在")
        else:
            print(f"⚠️  用户创建响应: {register_response.status_code}")
            
    except Exception as e:
        print(f"⚠️  用户创建失败: {str(e)}")
    
    # 4. 用户登录
    print("\n🔐 用户登录...")
    try:
        login_data = {
            "username": "test@example.com",
            "password": "testpassword"
        }
        
        login_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            timeout=10
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            print("✅ 登录成功")
            headers = {"Authorization": f"Bearer {token}"}
        else:
            print(f"⚠️  登录失败: {login_response.status_code}")
            print("继续测试（无认证）...")
            headers = {}
            
    except Exception as e:
        print(f"⚠️  登录异常: {str(e)}")
        headers = {}
    
    # 5. 上传文件
    print(f"\n📤 上传文件: {os.path.basename(upload_file)}")
    try:
        with open(upload_file, 'rb') as f:
            # 根据文件扩展名设置正确的MIME类型
            file_ext = os.path.splitext(upload_file)[1].lower()
            if file_ext == '.pdf':
                mime_type = 'application/pdf'
            elif file_ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif file_ext == '.png':
                mime_type = 'image/png'
            else:
                mime_type = 'application/octet-stream'
            
            files = {'file': (os.path.basename(upload_file), f, mime_type)}
            
            upload_response = requests.post(
                f"{base_url}/api/v1/drawings/upload",
                files=files,
                headers=headers,
                timeout=60
            )
            
        if upload_response.status_code == 200:
            drawing_data = upload_response.json()
            drawing_id = drawing_data["id"]
            print(f"✅ 文件上传成功")
            print(f"   图纸ID: {drawing_id}")
            print(f"   文件名: {drawing_data['filename']}")
            print(f"   状态: {drawing_data['status']}")
        else:
            print(f"❌ 文件上传失败: {upload_response.status_code}")
            print(f"   错误信息: {upload_response.text}")
            return
            
    except Exception as e:
        print(f"❌ 文件上传异常: {str(e)}")
        return
    
    # 6. 等待初始处理完成
    print("\n⏳ 等待初始处理...")
    time.sleep(5)
    
    # 7. 执行构件识别
    print("\n🔍 启动构件识别...")
    try:
        detect_response = requests.post(
            f"{base_url}/api/v1/drawings/{drawing_id}/detect-components",
            headers=headers,
            timeout=30
        )
        
        if detect_response.status_code == 200:
            detect_data = detect_response.json()
            task_id = detect_data.get("task_id")
            print(f"✅ 构件识别任务已启动")
            print(f"   任务ID: {task_id}")
            print(f"   状态: {detect_data['status']}")
        else:
            print(f"❌ 构件识别启动失败: {detect_response.status_code}")
            print(f"   错误信息: {detect_response.text}")
            return
            
    except Exception as e:
        print(f"❌ 构件识别请求异常: {str(e)}")
        return
    
    # 8. 轮询任务状态
    print("\n⏳ 等待构件识别完成...")
    max_wait = 60
    wait_time = 0
    
    while wait_time < max_wait:
        try:
            if task_id:
                task_response = requests.get(
                    f"{base_url}/api/v1/drawings/tasks/{task_id}",
                    headers=headers,
                    timeout=10
                )
                
                if task_response.status_code == 200:
                    task_data = task_response.json()
                    task_status = task_data["status"]
                    print(f"   任务状态: {task_status}")
                    
                    if task_status == "completed":
                        result = task_data.get("result", {})
                        print("✅ 构件识别完成！")
                        
                        # 显示识别结果
                        if "components" in result:
                            components = result["components"]
                            print("\n📊 构件识别结果:")
                            
                            total_components = 0
                            for comp_type, comp_list in components.items():
                                count = len(comp_list)
                                total_components += count
                                if count > 0:
                                    print(f"   🏗️  {comp_type}: {count}个")
                                    
                                    # 显示前2个构件的详细信息
                                    for i, component in enumerate(comp_list[:2]):
                                        conf = component.get('confidence', 0)
                                        dims = component.get('dimensions', {})
                                        width = dims.get('width', 0)
                                        height = dims.get('height', 0)
                                        print(f"      [{i+1}] 置信度: {conf:.2f}, 尺寸: {width:.0f}×{height:.0f}mm")
                                    
                                    if count > 2:
                                        print(f"      ... 还有 {count - 2} 个")
                            
                            print(f"\n🎯 总计检测到 {total_components} 个构件")
                        else:
                            print("⚠️  未找到构件识别结果")
                        
                        break
                        
                    elif task_status == "failed":
                        error = task_data.get("error", "未知错误")
                        print(f"❌ 构件识别失败: {error}")
                        break
            
            time.sleep(3)
            wait_time += 3
            
        except Exception as e:
            print(f"   任务状态检查失败: {str(e)}")
            break
    
    if wait_time >= max_wait:
        print("⏰ 等待超时")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")
    print(f"💡 您可以访问 http://localhost:3000/drawings/{drawing_id} 查看详细结果")

if __name__ == "__main__":
    test_upload_and_detect() 