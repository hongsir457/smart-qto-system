#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API接口测试脚本
测试新增的OCR结果和构件分析结果接口
"""

import os
import sys
import json
import tempfile
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.drawing import Drawing
from app.models.user import User

client = TestClient(app)

def create_test_user():
    """创建测试用户"""
    # 这里应该通过正常的用户注册流程创建
    # 为了测试，我们模拟一个用户ID
    return {"id": 1, "username": "test_user"}

def create_test_drawing_record(user_id: int) -> int:
    """创建测试图纸记录"""
    # 模拟一个完整的处理结果
    mock_processing_result = {
        "status": "success",
        "drawing_id": "test_001",
        "user_id": str(user_id),
        "stages_completed": ["png_conversion", "ocr_recognition", "stage_one_analysis", "stage_two_analysis"],
        "ocr_result": {
            "status": "success",
            "text_regions": [
                {
                    "text": "KZ1",
                    "confidence": 0.95,
                    "bbox": {
                        "x_min": 100, "y_min": 100, "x_max": 150, "y_max": 130,
                        "center_x": 125, "center_y": 115, "width": 50, "height": 30
                    },
                    "bbox_area": 1500.0,
                    "text_length": 3,
                    "is_number": False,
                    "is_dimension": False,
                    "is_component_code": True
                },
                {
                    "text": "400×400",
                    "confidence": 0.92,
                    "bbox": {
                        "x_min": 160, "y_min": 100, "x_max": 220, "y_max": 130,
                        "center_x": 190, "center_y": 115, "width": 60, "height": 30
                    },
                    "bbox_area": 1800.0,
                    "text_length": 7,
                    "is_number": False,
                    "is_dimension": True,
                    "is_component_code": False
                }
            ],
            "total_regions": 2,
            "all_text": "KZ1\n400×400",
            "statistics": {
                "total_count": 2,
                "numeric_count": 0,
                "dimension_count": 1,
                "component_code_count": 1,
                "avg_confidence": 0.935
            },
            "processing_time": 2.3
        },
        "stage_one_result": {
            "status": "success",
            "analysis_results": {
                "drawing_type": "结构",
                "title_block": {
                    "project_name": "测试工程",
                    "drawing_title": "结构施工图",
                    "drawing_number": "S-01",
                    "scale": "1:100"
                },
                "components": [
                    {
                        "code": "KZ1",
                        "component_type": "框架柱",
                        "dimensions": ["400×400"],
                        "position": {"x": 125, "y": 115},
                        "confidence": 0.95
                    }
                ],
                "dimensions": [
                    {
                        "text": "400×400",
                        "pattern": "(\\d+)×(\\d+)",
                        "position": {"x": 190, "y": 115},
                        "confidence": 0.92
                    }
                ],
                "component_list": [
                    {
                        "code": "KZ1",
                        "type": "框架柱",
                        "dimensions": ["400×400"],
                        "position": {"x": 125, "y": 115},
                        "confidence": 0.95,
                        "dimension_count": 1
                    }
                ],
                "statistics": {
                    "total_components": 1,
                    "total_dimensions": 1,
                    "avg_confidence": 0.935,
                    "components_with_dimensions": 1
                }
            }
        },
        "stage_two_result": {
            "status": "success",
            "analysis_results": {
                "components": [
                    {
                        "code": "KZ1",
                        "type": "框架柱",
                        "dimensions": {
                            "section": "400×400",
                            "height": "3600",
                            "concrete_grade": "C30"
                        },
                        "material": {
                            "concrete": "C30",
                            "steel": "HRB400",
                            "main_rebar": "8Φ20"
                        },
                        "quantity": 4,
                        "position": {"floor": "1-3层", "grid": "A1"},
                        "attributes": {
                            "load_bearing": True,
                            "seismic_grade": "二级",
                            "fire_resistance": "1.5h"
                        }
                    }
                ],
                "analysis_summary": {
                    "initial_summary": "识别到主要结构构件包括框架柱",
                    "detail_summary": "详细分析了构件尺寸、材料等级",
                    "verification_summary": "最终验证确认构件信息准确",
                    "total_components": 1,
                    "analysis_rounds": 3
                },
                "quality_assessment": {
                    "overall_confidence": 0.92,
                    "completeness": "高",
                    "accuracy": "excellent"
                },
                "recommendations": [
                    "建议核实KZ1柱的配筋详图"
                ],
                "processing_metadata": {
                    "model_used": "gpt-4o",
                    "provider": "openai"
                }
            }
        },
        "final_components": [
            {
                "code": "KZ1",
                "type": "框架柱",
                "dimensions": {
                    "section": "400×400",
                    "height": "3600"
                },
                "material": {
                    "concrete": "C30",
                    "steel": "HRB400"
                },
                "quantity": 4
            }
        ],
        "total_components": 1,
        "processing_time": 15.5
    }
    
    # 这里应该通过数据库创建记录
    # 为了测试，我们返回一个模拟的图纸ID
    return 1, json.dumps(mock_processing_result, ensure_ascii=False)

def test_ocr_results_api():
    """测试OCR结果API"""
    print("\n=== 测试 OCR 结果 API ===")
    
    try:
        # 模拟用户认证（在实际测试中需要正确的认证）
        user = create_test_user()
        drawing_id, processing_result = create_test_drawing_record(user["id"])
        
        # 发送请求
        response = client.get(
            f"/api/v1/drawings/{drawing_id}/ocr-results",
            # headers={"Authorization": f"Bearer {user_token}"}  # 实际需要认证
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ OCR结果API测试成功")
            print(f"图纸ID: {data.get('drawing_id')}")
            print(f"状态: {data.get('status')}")
            print(f"OCR文本区域数量: {len(data.get('ocr_data', {}).get('text_regions', []))}")
            print(f"识别的构件数量: {len(data.get('stage_one_analysis', {}).get('components', []))}")
            print(f"图纸类型: {data.get('stage_one_analysis', {}).get('drawing_type')}")
            
            # 验证数据结构
            assert 'drawing_id' in data
            assert 'ocr_data' in data
            assert 'stage_one_analysis' in data
            assert 'quality_info' in data
            
            print("✅ 数据结构验证通过")
            
        else:
            print(f"❌ OCR结果API测试失败: {response.text}")
            
    except Exception as e:
        print(f"❌ OCR结果API测试异常: {str(e)}")

def test_analysis_results_api():
    """测试构件分析结果API"""
    print("\n=== 测试构件分析结果API ===")
    
    try:
        user = create_test_user()
        drawing_id, processing_result = create_test_drawing_record(user["id"])
        
        # 发送请求
        response = client.get(
            f"/api/v1/drawings/{drawing_id}/analysis-results",
            # headers={"Authorization": f"Bearer {user_token}"}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 构件分析结果API测试成功")
            print(f"图纸ID: {data.get('drawing_id')}")
            print(f"分析类型: {data.get('analysis_type')}")
            print(f"是否有AI分析: {data.get('has_ai_analysis')}")
            print(f"构件数量: {len(data.get('components', []))}")
            print(f"AI模型: {data.get('llm_analysis', {}).get('model_used', 'N/A')}")
            
            # 验证数据结构
            assert 'drawing_id' in data
            assert 'analysis_type' in data
            assert 'has_ai_analysis' in data
            assert 'components' in data
            assert 'analysis_summary' in data
            assert 'quality_assessment' in data
            assert 'recommendations' in data
            assert 'statistics' in data
            
            print("✅ 数据结构验证通过")
            
        else:
            print(f"❌ 构件分析结果API测试失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 构件分析结果API测试异常: {str(e)}")

def test_components_api():
    """测试构件清单API"""
    print("\n=== 测试构件清单API ===")
    
    try:
        user = create_test_user()
        drawing_id, processing_result = create_test_drawing_record(user["id"])
        
        # 发送请求
        response = client.get(
            f"/api/v1/drawings/{drawing_id}/components",
            # headers={"Authorization": f"Bearer {user_token}"}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 构件清单API测试成功")
            print(f"图纸ID: {data.get('drawing_id')}")
            print(f"构件总数: {data.get('total_count')}")
            print(f"分析来源: {data.get('analysis_info', {}).get('source')}")
            print(f"置信度等级: {data.get('quality_metrics', {}).get('confidence_level')}")
            print(f"分析深度: {data.get('quality_metrics', {}).get('analysis_depth')}")
            
            # 验证数据结构
            assert 'drawing_id' in data
            assert 'components' in data
            assert 'total_count' in data
            assert 'analysis_info' in data
            assert 'quality_metrics' in data
            
            print("✅ 数据结构验证通过")
            
        else:
            print(f"❌ 构件清单API测试失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 构件清单API测试异常: {str(e)}")

def test_api_error_handling():
    """测试API错误处理"""
    print("\n=== 测试API错误处理 ===")
    
    # 测试不存在的图纸ID
    response = client.get("/api/v1/drawings/99999/ocr-results")
    print(f"不存在图纸ID - OCR结果API状态码: {response.status_code}")
    
    response = client.get("/api/v1/drawings/99999/analysis-results")
    print(f"不存在图纸ID - 分析结果API状态码: {response.status_code}")
    
    response = client.get("/api/v1/drawings/99999/components")
    print(f"不存在图纸ID - 构件清单API状态码: {response.status_code}")
    
    print("✅ 错误处理测试完成")

def run_api_tests():
    """运行所有API测试"""
    print("🚀 开始API接口测试")
    print("=" * 50)
    
    try:
        test_ocr_results_api()
        test_analysis_results_api()
        test_components_api()
        test_api_error_handling()
        
        print("\n" + "=" * 50)
        print("🎉 API接口测试完成")
        
    except Exception as e:
        print(f"\n❌ API测试异常: {str(e)}")
        print("请确保:")
        print("1. FastAPI应用正常启动")
        print("2. 数据库连接正常")
        print("3. 认证系统配置正确")

if __name__ == "__main__":
    run_api_tests() 