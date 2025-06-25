import json

# 模拟后端返回的ID=3数据
mock_drawing_data = {
    "id": 3,
    "filename": "一层柱结构改造加固平面图.pdf",
    "recognition_results": {
        "analysis_summary": "识别到5个加固柱构件的改造加固信息",
        "analysis_engine": "GPT-4o",
        "pipeline_type": "A→B→C数据流",
        "processing_time": "2.8秒",
        "ocr_texts": [
            "加固柱 JGZ-1 原400×400 加固至500×500",
            "加固柱 JGZ-2 原350×350 加固至450×450", 
            "JGZ-3 原500×500 增设钢板",
            "新增柱 XZ-1 400×600 C40",
            "新增柱 XZ-2 350×350 C40混凝土",
            "加固材料 Q345钢板",
            "植筋胶 HRB400",
            "一层柱结构改造加固平面图",
            "比例 1:100",
            "图号 JG-01", 
            "项目 旧楼加固改造",
            "设计 张工程师",
            "审核 李总工",
            "2025年1月施工"
        ],
        "components": [
            {
                "component_id": "JGZ-1",
                "component_type": "加固柱",
                "dimensions": "400×400→500×500",
                "material": "原C30+新增C40",
                "quantity": 6,
                "unit": "根"
            },
            {
                "component_id": "JGZ-2", 
                "component_type": "加固柱",
                "dimensions": "350×350→450×450",
                "material": "原C30+新增C40",
                "quantity": 4,
                "unit": "根"
            },
            {
                "component_id": "JGZ-3",
                "component_type": "加固柱", 
                "dimensions": "500×500+钢板",
                "material": "C30+Q345钢板",
                "quantity": 2,
                "unit": "根"
            },
            {
                "component_id": "XZ-1",
                "component_type": "新增柱",
                "dimensions": "400×600", 
                "material": "C40混凝土",
                "quantity": 3,
                "unit": "根"
            },
            {
                "component_id": "XZ-2",
                "component_type": "新增柱",
                "dimensions": "350×350",
                "material": "C40混凝土", 
                "quantity": 2,
                "unit": "根"
            }
        ]
    }
}

print("=== 模拟前端数据处理 ===")
print(f"图纸ID: {mock_drawing_data['id']}")
print(f"文件名: {mock_drawing_data['filename']}")

recognition_results = mock_drawing_data.get('recognition_results')
if recognition_results:
    ocr_texts = recognition_results.get('ocr_texts', [])
    components = recognition_results.get('components', [])
    
    print(f"\n提取的OCR文本（{len(ocr_texts)}条）:")
    for i, text in enumerate(ocr_texts[:5]):
        print(f"  {i+1}. {text}")
    
    print(f"\n提取的构件（{len(components)}个）:")
    for i, comp in enumerate(components[:3]):
        print(f"  {i+1}. {comp['component_id']} - {comp['component_type']}")
    
    # 模拟extractRealOcrData函数的逻辑
    print(f"\n=== extractRealOcrData 结果 ===")
    has_ocr_texts = (recognition_results and 
                    recognition_results.get('ocr_texts') and 
                    isinstance(recognition_results.get('ocr_texts'), list) and
                    len(recognition_results.get('ocr_texts')) > 0)
    
    print(f"检测到OCR文本数组: {has_ocr_texts}")
    if has_ocr_texts:
        print(f"OCR文本数量: {len(ocr_texts)}")
        print(f"应该使用简单测试数据处理流程")
    else:
        print("未检测到OCR文本数组，可能会走其他处理流程")

else:
    print("❌ 没有recognition_results数据")

print(f"\n如果前端显示的不是这些数据，说明存在数据混乱或缓存问题。") 