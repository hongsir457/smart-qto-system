#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能工程量计算系统 API 调用示例
演示如何通过API上传PDF图纸文件并获取构件识别和工程量计算结果
"""

import requests
import time
import json
from pathlib import Path

class SmartQTOAPI:
    """智能工程量计算API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", username: str = None, password: str = None):
        self.base_url = base_url
        self.token = None
        
        if username and password:
            self.login(username, password)
    
    def login(self, username: str, password: str) -> bool:
        """用户登录获取Token"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                data={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"✅ 登录成功，获取到Token")
                return True
            else:
                print(f"❌ 登录失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 登录异常: {str(e)}")
            return False
    
    def _get_headers(self):
        """获取认证头"""
        if not self.token:
            raise Exception("请先登录获取Token")
        
        return {
            "Authorization": f"Bearer {self.token}"
        }
    
    def upload_pdf(self, pdf_file_path: str) -> dict:
        """
        上传PDF图纸文件
        
        Args:
            pdf_file_path: PDF文件路径
            
        Returns:
            dict: 上传结果，包含drawing_id
        """
        if not Path(pdf_file_path).exists():
            raise FileNotFoundError(f"文件不存在: {pdf_file_path}")
        
        print(f"📤 开始上传PDF文件: {pdf_file_path}")
        
        try:
            with open(pdf_file_path, 'rb') as f:
                files = {'file': (Path(pdf_file_path).name, f, 'application/pdf')}
                
                response = requests.post(
                    f"{self.base_url}/api/v1/drawings/upload",
                    files=files,
                    headers=self._get_headers(),
                    timeout=60
                )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 文件上传成功")
                print(f"   图纸ID: {data['id']}")
                print(f"   文件名: {data['filename']}")
                print(f"   状态: {data['status']}")
                return data
            else:
                print(f"❌ 文件上传失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ 文件上传异常: {str(e)}")
            return None
    
    def get_drawing_status(self, drawing_id: int) -> dict:
        """获取图纸处理状态"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/drawings/{drawing_id}",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 获取状态失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 获取状态异常: {str(e)}")
            return None
    
    def wait_for_processing(self, drawing_id: int, max_wait_time: int = 300) -> dict:
        """
        等待图纸处理完成
        
        Args:
            drawing_id: 图纸ID
            max_wait_time: 最大等待时间（秒）
            
        Returns:
            dict: 最终处理结果
        """
        print(f"⏳ 等待图纸 {drawing_id} 处理完成...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            status_data = self.get_drawing_status(drawing_id)
            
            if not status_data:
                time.sleep(5)
                continue
            
            status = status_data.get('status', 'unknown')
            print(f"   当前状态: {status}")
            
            if status == 'completed':
                print(f"✅ 处理完成!")
                return status_data
            elif status == 'error':
                error_msg = status_data.get('error_message', '未知错误')
                print(f"❌ 处理失败: {error_msg}")
                return status_data
            elif status in ['pending', 'processing']:
                print(f"   继续等待...")
                time.sleep(10)
            else:
                print(f"   未知状态: {status}")
                time.sleep(5)
        
        print(f"❌ 处理超时 ({max_wait_time}秒)")
        return None
    
    def get_recognition_results(self, drawing_id: int) -> dict:
        """获取构件识别结果"""
        drawing_data = self.get_drawing_status(drawing_id)
        
        if not drawing_data:
            return None
        
        recognition_results = drawing_data.get('recognition_results')
        if not recognition_results:
            print("❌ 未找到识别结果")
            return None
        
        print(f"📊 构件识别结果统计:")
        
        # 分析识别结果
        if 'recognition' in recognition_results:
            components = recognition_results['recognition']
            total_components = 0
            
            for component_type, data in components.items():
                if isinstance(data, list):
                    count = len(data)
                    total_components += count
                    print(f"   {component_type}: {count} 个")
            
            print(f"   总计: {total_components} 个构件")
        
        return recognition_results
    
    def get_quantity_results(self, drawing_id: int) -> dict:
        """获取工程量计算结果"""
        drawing_data = self.get_drawing_status(drawing_id)
        
        if not drawing_data:
            return None
        
        recognition_results = drawing_data.get('recognition_results')
        if not recognition_results or 'quantities' not in recognition_results:
            print("❌ 未找到工程量计算结果")
            return None
        
        quantities = recognition_results['quantities']
        
        print(f"📈 工程量计算结果:")
        
        # 显示各构件类型的工程量
        component_types = ['walls', 'columns', 'beams', 'slabs', 'foundations']
        
        for comp_type in component_types:
            if comp_type in quantities:
                items = quantities[comp_type]
                if isinstance(items, list) and items:
                    print(f"   {comp_type}: {len(items)} 项")
                    
                    # 计算总体积
                    total_volume = sum(item.get('volume', 0) for item in items)
                    if total_volume > 0:
                        print(f"     总体积: {total_volume:.3f} m³")
        
        # 显示总量统计
        if 'total' in quantities:
            total = quantities['total']
            print(f"\n   📊 总量统计:")
            
            volume_keys = [
                ('墙体总体积', 'wall_volume'),
                ('柱子总体积', 'column_volume'),
                ('梁总体积', 'beam_volume'),
                ('板总体积', 'slab_volume'),
                ('基础总体积', 'foundation_volume'),
                ('总体积', 'total_volume')
            ]
            
            for name, key in volume_keys:
                if key in total and total[key] > 0:
                    print(f"     {name}: {total[key]:.3f} m³")
        
        return quantities
    
    def export_results(self, drawing_id: int, output_file: str = None) -> str:
        """
        导出工程量计算结果为Excel文件
        
        Args:
            drawing_id: 图纸ID
            output_file: 输出文件路径（可选）
            
        Returns:
            str: 导出文件路径
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/drawings/{drawing_id}/export",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                if not output_file:
                    output_file = f"quantities_drawing_{drawing_id}.xlsx"
                
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ 工程量结果已导出到: {output_file}")
                return output_file
            else:
                print(f"❌ 导出失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 导出异常: {str(e)}")
            return None


def main():
    """API调用示例主函数"""
    
    print("=" * 80)
    print("智能工程量计算系统 API 调用示例")
    print("=" * 80)
    
    # 1. 初始化API客户端
    api = SmartQTOAPI(
        base_url="http://localhost:8000",
        username="test@example.com",  # 替换为实际用户名
        password="123456"            # 替换为实际密码
    )
    
    # 2. 上传PDF文件
    pdf_file = "your_building_plan.pdf"  # 替换为实际PDF文件路径
    
    # 检查文件是否存在
    if not Path(pdf_file).exists():
        print(f"❌ 请将PDF文件放置在: {pdf_file}")
        print("   或修改代码中的文件路径")
        return
    
    # 上传文件
    upload_result = api.upload_pdf(pdf_file)
    if not upload_result:
        return
    
    drawing_id = upload_result['id']
    
    # 3. 等待处理完成
    print(f"\n🔄 开始处理PDF文件...")
    final_result = api.wait_for_processing(drawing_id, max_wait_time=300)
    
    if not final_result or final_result.get('status') != 'completed':
        print("❌ 处理未能成功完成")
        return
    
    # 4. 获取构件识别结果
    print(f"\n🔍 获取构件识别结果:")
    recognition_results = api.get_recognition_results(drawing_id)
    
    # 5. 获取工程量计算结果
    print(f"\n📊 获取工程量计算结果:")
    quantity_results = api.get_quantity_results(drawing_id)
    
    # 6. 导出结果到Excel文件
    print(f"\n📤 导出工程量计算结果:")
    export_file = api.export_results(drawing_id, f"工程量计算结果_{drawing_id}.xlsx")
    
    print(f"\n✅ 全部完成!")
    print(f"   图纸ID: {drawing_id}")
    print(f"   导出文件: {export_file}")
    
    # 7. 保存完整结果到JSON文件
    complete_results = {
        "drawing_id": drawing_id,
        "file_name": upload_result['filename'],
        "recognition_results": recognition_results,
        "quantity_results": quantity_results,
        "processing_status": final_result.get('status'),
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    json_file = f"完整结果_{drawing_id}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(complete_results, f, ensure_ascii=False, indent=2)
    
    print(f"   完整结果: {json_file}")


if __name__ == "__main__":
    main() 