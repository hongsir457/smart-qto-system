#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查最新的真实LLM结果
"""

import json
import tempfile
import os
from app.services.s3_service import s3_service

def check_latest_llm_result():
    """检查最新的LLM结果文件"""
    print("🔍 检查最新的真实LLM结果")
    print("=" * 60)
    
    # 检查日志中提到的文件
    latest_file = "llm_results/3/aa060eaf-bc75-49fa-b18b-926350bcd2ec.json"
    
    # 先检查文件是否存在
    file_info = s3_service.get_file_info(latest_file)
    if not file_info:
        print(f"❌ 文件不存在: {latest_file}")
        return
    
    print(f"✅ 文件存在: {latest_file}")
    print(f"📏 文件大小: {file_info.get('size', 'unknown')} 字节")
    print(f"🕒 修改时间: {file_info.get('last_modified', 'unknown')}")
    
    # 下载文件到临时位置
    try:
        import uuid
        tmp_filename = f"temp_llm_result_{uuid.uuid4().hex[:8]}.json"
        
        success = s3_service.download_file(latest_file, tmp_filename)
        
        if not success:
            print("❌ 下载文件失败")
            return
        
        # 读取文件内容
        try:
            with open(tmp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
        finally:
            # 清理临时文件
            if os.path.exists(tmp_filename):
                os.unlink(tmp_filename)
            
            print(f"\n📄 文件内容分析:")
            print(f"   • 内容长度: {len(content)} 字符")
            
            # 解析JSON
            try:
                data = json.loads(content)
                print(f"   • JSON解析: ✅ 成功")
                print(f"   • 顶层字段: {list(data.keys())}")
                print(f"   • 成功状态: {data.get('success', 'unknown')}")
                
                if 'qto_data' in data:
                    qto_data = data['qto_data']
                    print(f"   • QTO数据存在: ✅")
                    print(f"   • QTO字段: {list(qto_data.keys())}")
                    
                    if 'components' in qto_data:
                        components = qto_data['components']
                        print(f"   • 构件数量: {len(components)}")
                        
                        if components:
                            print(f"\n🏗️ 构件分析:")
                            print(f"   • 第一个构件字段: {list(components[0].keys())}")
                            
                            # 统计构件类型
                            component_types = {}
                            for comp in components:
                                comp_type = comp.get('component_type', '未知')
                                component_types[comp_type] = component_types.get(comp_type, 0) + 1
                            
                            print(f"   • 构件类型分布:")
                            for comp_type, count in component_types.items():
                                print(f"     - {comp_type}: {count}个")
                            
                            # 显示前3个构件的详细信息
                            print(f"\n📋 前3个构件详情:")
                            for i, comp in enumerate(components[:3]):
                                print(f"   [{i+1}] {comp.get('component_id', 'N/A')} - {comp.get('component_type', 'N/A')}")
                                print(f"       尺寸: {comp.get('dimensions', 'N/A')}")
                                print(f"       配筋: {comp.get('reinforcement', 'N/A')}")
                                if 'notes' in comp:
                                    print(f"       备注: {comp.get('notes', 'N/A')}")
                    
                    # 检查是否有图纸信息
                    if 'drawing_info' in qto_data:
                        drawing_info = qto_data['drawing_info']
                        print(f"\n📐 图纸信息:")
                        for key, value in drawing_info.items():
                            print(f"   • {key}: {value}")
                
                # 检查是否包含AI分析元数据
                if 'result_s3_url' in data:
                    print(f"\n🔗 结果URL: {data['result_s3_url']}")
                
                # 判断是否为真实数据
                print(f"\n✅ 数据类型判断:")
                
                # 检查特征
                is_real_data = True
                test_indicators = []
                
                # 检查是否有模拟数据的特征
                if 'qto_data' in data and 'components' in data['qto_data']:
                    components = data['qto_data']['components']
                    for comp in components:
                        comp_id = comp.get('component_id', '')
                        if comp_id.startswith('K-JKZ') or comp_id.startswith('TEST'):
                            test_indicators.append(f"规律性编号: {comp_id}")
                        
                        # 检查项目信息
                        if 'drawing_info' in data['qto_data']:
                            project_name = data['qto_data']['drawing_info'].get('project_name', '')
                            if project_name == "上海市某建筑工程":
                                test_indicators.append(f"通用项目名: {project_name}")
                
                if test_indicators:
                    print(f"   ⚠️  发现测试数据特征:")
                    for indicator in test_indicators:
                        print(f"     - {indicator}")
                    is_real_data = False
                else:
                    print(f"   ✅ 未发现测试数据特征，这可能是真实的LLM识别结果")
                
                return is_real_data, data
                
            except json.JSONDecodeError as e:
                print(f"   • JSON解析: ❌ 失败 - {e}")
                print(f"   • 原始内容预览: {content[:200]}...")
                return False, None
                
    except Exception as e:
        print(f"❌ 处理文件时出错: {e}")
        return False, None

if __name__ == "__main__":
    result = check_latest_llm_result()
    if result:
        is_real, data = result
        if is_real:
            print(f"\n🎉 确认：这是真实的LLM识别结果！")
        else:
            print(f"\n⚠️  警告：仍然包含测试数据特征")
    else:
        print(f"\n❌ 无法分析LLM结果") 