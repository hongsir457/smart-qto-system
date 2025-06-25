#!/usr/bin/env python3
"""
修复Vision构件数据丢失问题
问题：切片分析51个构件 → 双轨协同26个构件 → Vision结果合并0个构件
根因：数据传递断链，没有正确使用合并后的构件数据
"""

import re

def fix_vision_component_data_loss():
    """修复Vision构件数据丢失问题"""
    
    file_path = "app/tasks/drawing_tasks.py"
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找到数据汇总阶段的代码
        old_pattern = r'''if vision_success:
                logger\.info\("✅ 使用Vision Scan结果进行后续计算。"\)
                analysis_result = vision_scan_result\.get\("qto_data", \{\}\)
                if not analysis_result:
                    analysis_result = vision_scan_result if isinstance\(vision_scan_result, dict\) and "components" in vision_scan_result else \{\}
                components = analysis_result\.get\("components", \[\]\)'''
        
        new_pattern = '''if vision_success:
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
        new_content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE | re.DOTALL)
        
        # 检查是否替换成功
        if new_content != content:
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("✅ 成功修复Vision构件数据丢失问题")
            return True
        else:
            print("⚠️ 没有找到需要修复的内容")
            return False
            
    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    fix_vision_component_data_loss() 