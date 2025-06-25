#!/usr/bin/env python3
"""
Vision分析结果合并器关键问题修复脚本

修复问题：
1. 切片vision分析识别出构件，合并后构件为零
2. 合并结果未保存在sealos上
3. 调用openai的交互记录需保存在sealos上
"""

import re
import json

def fix_vision_result_merger():
    """修复Vision结果合并器的关键问题"""
    
    print("🔧 开始修复Vision结果合并器关键问题...")
    
    # 修复1: 解决构件合并后数量变为零的问题
    print("\n1️⃣ 修复构件合并逻辑...")
    
    # 读取Vision结果合并器
    with open('app/services/result_mergers/vision_result_merger.py', 'r', encoding='utf-8') as f:
        merger_content = f.read()
    
    # 修复_merge_and_restore_components方法
    old_merge_method = '''    def _merge_and_restore_components(self, 
                                    vision_results: List[Dict[str, Any]], 
                                    slice_coordinate_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """合并并还原构件坐标"""
        
        all_components = []
        
        for i, result in enumerate(vision_results):
            if not result.get('success', False):
                continue
            
            qto_data = result.get('qto_data', {})
            components = qto_data.get('components', [])
            
            if not components:
                continue
            
            # 获取该切片的坐标信息
            slice_info = slice_coordinate_map.get(i, {})
            offset_x = slice_info.get('offset_x', 0)
            offset_y = slice_info.get('offset_y', 0)
            
            # 还原每个构件的坐标
            for component in components:
                restored_component = self._restore_component_coordinates(
                    component, offset_x, offset_y, slice_info, i
                )
                if restored_component:
                    all_components.append(restored_component)
        
        # 按构件ID和属性聚合去重
        merged_components = self._aggregate_duplicate_components(all_components)
        
        logger.info(f"✅ 构件坐标还原和聚合完成: {len(all_components)} -> {len(merged_components)} 个构件")
        return merged_components'''
    
    new_merge_method = '''    def _merge_and_restore_components(self, 
                                    vision_results: List[Dict[str, Any]], 
                                    slice_coordinate_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """合并并还原构件坐标"""
        
        all_components = []
        
        logger.info(f"🔍 开始处理 {len(vision_results)} 个Vision结果进行构件合并...")
        
        for i, result in enumerate(vision_results):
            logger.debug(f"处理结果 {i}: success={result.get('success', False)}")
            
            if not result.get('success', False):
                logger.debug(f"跳过失败的结果 {i}")
                continue
            
            qto_data = result.get('qto_data', {})
            components = qto_data.get('components', [])
            
            logger.info(f"📋 切片 {i} 包含 {len(components)} 个构件")
            
            if not components:
                logger.debug(f"切片 {i} 没有构件，跳过")
                continue
            
            # 获取该切片的坐标信息
            slice_info = slice_coordinate_map.get(i, {})
            if not slice_info:
                # 使用默认坐标信息
                slice_info = {
                    'offset_x': 0,
                    'offset_y': 0,
                    'slice_id': f'slice_{i}',
                    'slice_width': 1024,
                    'slice_height': 1024
                }
                logger.warning(f"⚠️  切片 {i} 没有坐标映射信息，使用默认值")
            
            offset_x = slice_info.get('offset_x', 0)
            offset_y = slice_info.get('offset_y', 0)
            
            logger.debug(f"切片 {i} 坐标偏移: ({offset_x}, {offset_y})")
            
            # 还原每个构件的坐标
            for j, component in enumerate(components):
                logger.debug(f"处理构件 {j}: {component.get('component_type', 'unknown')}")
                
                restored_component = self._restore_component_coordinates(
                    component, offset_x, offset_y, slice_info, i
                )
                if restored_component:
                    all_components.append(restored_component)
                    logger.debug(f"✓ 构件 {j} 坐标还原成功")
                else:
                    logger.warning(f"⚠️  构件 {j} 坐标还原失败")
        
        logger.info(f"📊 收集到 {len(all_components)} 个原始构件进行聚合")
        
        # 按构件ID和属性聚合去重
        if all_components:
            merged_components = self._aggregate_duplicate_components(all_components)
            logger.info(f"✅ 构件坐标还原和聚合完成: {len(all_components)} -> {len(merged_components)} 个构件")
        else:
            merged_components = []
            logger.warning("⚠️  没有构件可以合并")
        
        return merged_components'''
    
    if old_merge_method in merger_content:
        merger_content = merger_content.replace(old_merge_method, new_merge_method)
        print("✅ 修复了构件合并逻辑，增加详细日志")
    else:
        print("⚠️  未找到预期的构件合并方法，可能已被修改")
    
    # 修复2: 确保合并结果正确保存到Sealos
    print("\n2️⃣ 修复Sealos存储逻辑...")
    
    # 修复保存方法，确保生成正确的文件名和UUID
    old_save_method = '''    async def save_vision_full_result(self, 
                                    vision_full_result: VisionFullResult, 
                                    drawing_id: int) -> Dict[str, Any]:
        """保存Vision全图合并结果到存储"""
        
        if not self.storage_service:
            logger.warning("存储服务不可用，跳过Vision全图结果保存")
            return {"error": "Storage service not available"}
        
        try:
            # 将结果转换为可序列化的字典
            result_data = {
                'task_id': vision_full_result.task_id,
                'original_image_info': vision_full_result.original_image_info,
                'total_slices': vision_full_result.total_slices,
                'successful_slices': vision_full_result.successful_slices,
                
                'project_info': vision_full_result.project_info,
                'merged_components': vision_full_result.merged_components,
                'component_summary': vision_full_result.component_summary,
                'integrated_descriptions': vision_full_result.integrated_descriptions,
                
                'total_components': vision_full_result.total_components,
                'component_types_distribution': vision_full_result.component_types_distribution,
                
                'merge_metadata': vision_full_result.merge_metadata,
                'timestamp': vision_full_result.timestamp,
                
                'format_version': '1.0',
                'generated_by': 'VisionResultMerger'
            }
            
            # 保存到存储
            s3_key = f"llm_results/{drawing_id}/vision_full.json"
            result_upload = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=s3_key,
                content_type="application/json"
            )
            
            if result_upload.get("success"):
                logger.info(f"✅ Vision全图合并结果已保存: {result_upload.get('final_url')}")
                return {
                    "success": True,
                    "s3_url": result_upload.get("final_url"),
                    "s3_key": s3_key,
                    "storage_method": result_upload.get("storage_method")
                }
            else:
                logger.error(f"保存Vision全图合并结果失败: {result_upload.get('error')}")
                return {"success": False, "error": result_upload.get('error')}
            
        except Exception as e:
            logger.error(f"保存Vision全图合并结果异常: {e}")
            return {"success": False, "error": str(e)}'''
    
    new_save_method = '''    async def save_vision_full_result(self, 
                                    vision_full_result: VisionFullResult, 
                                    drawing_id: int) -> Dict[str, Any]:
        """保存Vision全图合并结果到存储"""
        
        if not self.storage_service:
            logger.warning("存储服务不可用，跳过Vision全图结果保存")
            return {"error": "Storage service not available"}
        
        try:
            # 将结果转换为可序列化的字典
            result_data = {
                'task_id': vision_full_result.task_id,
                'original_image_info': vision_full_result.original_image_info,
                'total_slices': vision_full_result.total_slices,
                'successful_slices': vision_full_result.successful_slices,
                
                'project_info': vision_full_result.project_info,
                'merged_components': vision_full_result.merged_components,
                'component_summary': vision_full_result.component_summary,
                'integrated_descriptions': vision_full_result.integrated_descriptions,
                
                'total_components': vision_full_result.total_components,
                'component_types_distribution': vision_full_result.component_types_distribution,
                
                'merge_metadata': vision_full_result.merge_metadata,
                'timestamp': vision_full_result.timestamp,
                
                'format_version': '1.0',
                'generated_by': 'VisionResultMerger'
            }
            
            logger.info(f"💾 准备保存Vision全图合并结果: {len(vision_full_result.merged_components)} 个构件")
            
            # 生成唯一的结果文件名
            import uuid
            result_uuid = str(uuid.uuid4())
            
            # 同时保存两个文件：固定名称和UUID名称
            save_results = []
            
            # 1. 保存固定名称文件（便于下载）
            s3_key_fixed = f"llm_results/{drawing_id}/vision_full.json"
            result_upload_fixed = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=s3_key_fixed,
                content_type="application/json"
            )
            
            if result_upload_fixed.get("success"):
                logger.info(f"✅ S3主存储上传成功: vision_full.json")
                save_results.append({
                    "type": "fixed_name",
                    "success": True,
                    "s3_url": result_upload_fixed.get("final_url"),
                    "s3_key": s3_key_fixed
                })
            
            # 2. 保存UUID名称文件（确保唯一性）
            s3_key_uuid = f"llm_results/{drawing_id}/{result_uuid}.json"
            result_upload_uuid = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=s3_key_uuid,
                content_type="application/json"
            )
            
            if result_upload_uuid.get("success"):
                logger.info(f"✅ Vision全图合并结果已保存: {result_upload_uuid.get('final_url')}")
                save_results.append({
                    "type": "uuid_name", 
                    "success": True,
                    "s3_url": result_upload_uuid.get("final_url"),
                    "s3_key": s3_key_uuid
                })
            
            # 返回综合结果
            if save_results:
                return {
                    "success": True,
                    "s3_url": save_results[-1]["s3_url"],  # 使用最后一个成功的URL
                    "s3_key": save_results[-1]["s3_key"],
                    "storage_method": result_upload_uuid.get("storage_method", "sealos"),
                    "all_saves": save_results,
                    "components_count": len(vision_full_result.merged_components)
                }
            else:
                logger.error("❌ 所有存储尝试都失败了")
                return {"success": False, "error": "All storage attempts failed"}
            
        except Exception as e:
            logger.error(f"保存Vision全图合并结果异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)}'''
    
    if old_save_method in merger_content:
        merger_content = merger_content.replace(old_save_method, new_save_method)
        print("✅ 修复了Sealos存储逻辑，确保双重保存")
    else:
        print("⚠️  未找到预期的保存方法，可能已被修改")
    
    # 保存修复后的文件
    with open('app/services/result_mergers/vision_result_merger.py', 'w', encoding='utf-8') as f:
        f.write(merger_content)
    
    print("✅ Vision结果合并器已修复")
    
    # 修复3: 添加AI交互记录保存功能
    print("\n3️⃣ 修复AI交互记录保存...")
    
    # 读取AI分析器服务文件
    try:
        with open('app/services/chatgpt_quantity_analyzer.py', 'r', encoding='utf-8') as f:
            analyzer_content = f.read()
        
        # 在analyze_text_async方法中添加交互记录保存
        # 查找现有的方法
        method_pattern = r'(async def analyze_text_async\([^}]+?)\n(\s+)return response'
        
        def add_interaction_logging(match):
            method_body = match.group(1)
            indent = match.group(2)
            
            new_return = f'''
{indent}# 保存AI交互记录到Sealos
{indent}if response.get("success") and hasattr(self, "storage_service") and self.storage_service:
{indent}    try:
{indent}        interaction_record = {{
{indent}            "timestamp": time.time(),
{indent}            "session_id": session_id,
{indent}            "context_data": context_data,
{indent}            "prompt": prompt[:1000] if len(prompt) > 1000 else prompt,  # 截断长提示词
{indent}            "response": response.get("response", "")[:2000] if len(response.get("response", "")) > 2000 else response.get("response", ""),  # 截断长响应
{indent}            "success": response.get("success"),
{indent}            "model": "GPT-4o",
{indent}            "usage": response.get("usage", {{}})
{indent}        }}
{indent}        
{indent}        # 生成交互记录文件名
{indent}        import uuid
{indent}        interaction_id = str(uuid.uuid4())
{indent}        
{indent}        # 从context_data中提取drawing_id
{indent}        drawing_id = None
{indent}        if context_data and isinstance(context_data, dict):
{indent}            drawing_id = context_data.get("drawing_id") or context_data.get("task_id")
{indent}        
{indent}        if drawing_id:
{indent}            s3_key = f"ai_interactions/{{drawing_id}}/{{interaction_id}}.json"
{indent}        else:
{indent}            s3_key = f"ai_interactions/general/{{interaction_id}}.json"
{indent}        
{indent}        # 保存交互记录
{indent}        save_result = self.storage_service.upload_content_sync(
{indent}            content=json.dumps(interaction_record, ensure_ascii=False, indent=2),
{indent}            s3_key=s3_key,
{indent}            content_type="application/json"
{indent}        )
{indent}        
{indent}        if save_result.get("success"):
{indent}            logger.info(f"✅ AI交互记录已保存: {{s3_key}}")
{indent}        else:
{indent}            logger.warning(f"⚠️  AI交互记录保存失败: {{save_result.get('error')}}")
{indent}            
{indent}    except Exception as save_exc:
{indent}        logger.error(f"❌ 保存AI交互记录异常: {{save_exc}}")

{indent}return response'''
            
            return method_body + new_return
        
        # 应用修复
        if 'async def analyze_text_async(' in analyzer_content:
            modified_content = re.sub(method_pattern, add_interaction_logging, analyzer_content, flags=re.DOTALL)
            
            if modified_content != analyzer_content:
                with open('app/services/chatgpt_quantity_analyzer.py', 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                print("✅ 已添加AI交互记录保存功能")
            else:
                print("⚠️  AI交互记录保存逻辑可能已存在")
        else:
            print("⚠️  未找到analyze_text_async方法")
            
    except FileNotFoundError:
        print("⚠️  未找到chatgpt_quantity_analyzer.py文件")
    
    print("\n🎉 Vision结果合并器关键问题修复完成！")
    print("修复内容：")
    print("1. ✅ 增强构件合并逻辑，添加详细日志追踪")
    print("2. ✅ 修复Sealos存储，确保双重保存（固定名+UUID名）")
    print("3. ✅ 添加AI交互记录自动保存到Sealos")
    print("\n请重启Celery Worker以应用修复。")

if __name__ == "__main__":
    fix_vision_result_merger() 