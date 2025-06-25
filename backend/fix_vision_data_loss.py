#!/usr/bin/env python3
import re

# 读取文件
with open('app/tasks/drawing_tasks.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定义要替换的代码段
old_code = '''            if vision_success:
                logger.info("✅ 使用Vision Scan结果进行后续计算。")
                analysis_result = vision_scan_result.get("qto_data", {})
                if not analysis_result:
                    analysis_result = vision_scan_result if isinstance(vision_scan_result, dict) and "components" in vision_scan_result else {}
                components = analysis_result.get("components", [])'''

new_code = '''            if vision_success:
                logger.info("✅ 使用Vision Scan结果进行后续计算。")
                
                # 优先使用合并后的Vision结果（包含所有构件）
                analysis_result = {}
                components = []
                
                # 1. 优先检查合并后的完整结果
                if vision_scan_result.get('merged_full_result'):
                    merged_result = vision_scan_result['merged_full_result']
                    components = merged_result.get('merged_components', [])
                    analysis_result = {
                        "components": components,
                        "project_info": merged_result.get('project_info', {}),
                        "component_summary": merged_result.get('component_summary', {}),
                        "source": "vision_merged_full",
                        "total_slices": merged_result.get('total_slices', 0)
                    }
                    logger.info(f"🎯 使用合并Vision结果: {len(components)} 个构件 (来源: merged_full_result)")
                
                # 2. 降级到批次结果
                elif 'batch_results' in vision_scan_result:
                    batch_results = vision_scan_result['batch_results']
                    for batch_result in batch_results:
                        if batch_result.get('qto_data', {}).get('components'):
                            components.extend(batch_result['qto_data']['components'])
                    analysis_result = {
                        "components": components,
                        "source": "vision_batch_results",
                        "total_batches": len(batch_results)
                    }
                    logger.info(f"🎯 使用批次Vision结果: {len(components)} 个构件 (来源: batch_results)")
                
                # 3. 最后降级到单一结果
                elif vision_scan_result.get("qto_data"):
                    analysis_result = vision_scan_result.get("qto_data", {})
                    components = analysis_result.get("components", [])
                    logger.info(f"🎯 使用单一Vision结果: {len(components)} 个构件 (来源: qto_data)")
                
                # 4. 兜底使用原始结果
                else:
                    analysis_result = vision_scan_result if isinstance(vision_scan_result, dict) and "components" in vision_scan_result else {}
                    components = analysis_result.get("components", [])
                    logger.info(f"🎯 使用原始Vision结果: {len(components)} 个构件 (来源: fallback)")'''

# 执行替换
new_content = content.replace(old_code, new_code)

if new_content != content:
    with open('app/tasks/drawing_tasks.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('✅ 成功修复Vision构件数据丢失问题')
else:
    print('⚠️ 替换失败，可能代码格式有变化') 