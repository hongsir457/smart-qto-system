#!/usr/bin/env python3
"""
修复Vision重复分析同一切片的问题

根本原因：
1. 批次重叠：每个批次都处理全部切片，而不是分配不同的切片
2. 缺乏Vision缓存：没有Vision结果的复用机制
3. 错误的分片策略：应该按切片分批，不是按时间分批

解决方案：
1. 修改批次分配逻辑：每个批次只处理分配给它的切片
2. 添加Vision结果缓存机制
3. 跳过已分析的切片
"""

import re
import os

def fix_vision_duplicate_analysis():
    """修复Vision重复分析问题"""
    
    print("🔧 开始修复Vision重复分析问题...")
    
    # 1. 修复 VisionScannerService._process_slices_in_batches
    fix_batch_processing()
    
    # 2. 修复 EnhancedGridSliceAnalyzer._analyze_slices_with_enhanced_vision
    fix_vision_analysis_method()
    
    # 3. 添加Vision缓存机制
    add_vision_cache_mechanism()
    
    print("✅ Vision重复分析问题修复完成")

def fix_batch_processing():
    """修复批次处理逻辑"""
    file_path = "app/services/vision_scanner.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找到问题代码段
        old_pattern = r'''# 执行双轨协同分析
                        batch_result = dual_track_analyzer\.analyze_drawing_with_dual_track\(
                            image_path=batch_image_paths\[0\],  # 主图像路径
                            drawing_info=\{
                                "batch_id": batch_idx \+ 1,
                                "slice_count": len\(batch_data\),
                                "processing_method": "batch_dual_track",
                                "ocr_cache_enabled": ocr_cache_initialized
                            \},
                            task_id=batch_task_id,
                            output_dir=f"temp_batch_\{batch_task_id\}",
                            shared_slice_results=shared_slice_results  # 传递共享切片结果
                        \)'''
        
        new_pattern = '''# 🔧 修复：只处理当前批次分配的切片
                        # 计算当前批次应该处理的切片范围
                        batch_slice_range = {
                            'start_index': start_idx,
                            'end_index': end_idx - 1,
                            'slice_indices': list(range(start_idx, end_idx))
                        }
                        
                        logger.info(f"🎯 批次 {batch_idx + 1} 只处理切片索引: {batch_slice_range['slice_indices']}")
                        
                        # 执行双轨协同分析（限制切片范围）
                        batch_result = dual_track_analyzer.analyze_drawing_with_dual_track(
                            image_path=batch_image_paths[0],  # 主图像路径
                            drawing_info={
                                "batch_id": batch_idx + 1,
                                "slice_count": len(batch_data),
                                "processing_method": "batch_dual_track",
                                "ocr_cache_enabled": ocr_cache_initialized,
                                "slice_range": batch_slice_range  # 🔧 新增：限制切片范围
                            },
                            task_id=batch_task_id,
                            output_dir=f"temp_batch_{batch_task_id}",
                            shared_slice_results=shared_slice_results  # 传递共享切片结果
                        )'''
        
        # 执行替换
        new_content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE | re.DOTALL)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ 修复 {file_path} 中的批次处理逻辑")
        else:
            print(f"⚠️ {file_path} 未找到需要修复的代码")
            
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")

def fix_vision_analysis_method():
    """修复Vision分析方法，添加切片范围限制"""
    file_path = "app/services/enhanced_grid_slice_analyzer.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找到Vision分析方法
        old_pattern = r'''def _analyze_slices_with_enhanced_vision\(self, drawing_info: Dict\[str, Any\], task_id: str\) -> Dict\[str, Any\]:
        """Step 4: 基于OCR增强提示的Vision分析"""
        if not self\.ai_analyzer or not self\.ai_analyzer\.is_available\(\):
            return \{"success": False, "error": "AI分析器不可用"\}
        
        try:
            analyzed_count = 0
            enhanced_analysis_count = 0
            failed_count = 0
            
            for slice_info in self\.enhanced_slices:'''
        
        new_pattern = '''def _analyze_slices_with_enhanced_vision(self, drawing_info: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Step 4: 基于OCR增强提示的Vision分析（支持切片范围限制）"""
        if not self.ai_analyzer or not self.ai_analyzer.is_available():
            return {"success": False, "error": "AI分析器不可用"}
        
        try:
            analyzed_count = 0
            enhanced_analysis_count = 0
            failed_count = 0
            skipped_count = 0
            
            # 🔧 获取切片范围限制
            slice_range = drawing_info.get('slice_range', {})
            slice_indices = slice_range.get('slice_indices', [])
            
            # 🔧 添加Vision缓存检查
            vision_cache = getattr(self, '_vision_cache', {})
            
            for i, slice_info in enumerate(self.enhanced_slices):
                # 🔧 检查切片范围限制
                if slice_indices and i not in slice_indices:
                    skipped_count += 1
                    logger.debug(f"⏭️ 跳过切片 {slice_info.row}_{slice_info.col} (不在当前批次范围)")
                    continue
                
                # 🔧 检查Vision缓存
                cache_key = f"{slice_info.row}_{slice_info.col}"
                if cache_key in vision_cache:
                    self.slice_components[cache_key] = vision_cache[cache_key]
                    analyzed_count += 1
                    logger.info(f"♻️ 复用切片 {cache_key} 的Vision分析结果: {len(vision_cache[cache_key])} 个构件")
                    continue'''
        
        # 执行替换
        new_content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE | re.DOTALL)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ 修复 {file_path} 中的Vision分析方法")
        else:
            print(f"⚠️ {file_path} 未找到需要修复的代码")
            
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")

def add_vision_cache_mechanism():
    """添加Vision缓存机制"""
    file_path = "app/services/enhanced_grid_slice_analyzer.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 在__init__方法中添加Vision缓存
        old_init = r'''def __init__\(self, slice_size: int = 1024, overlap: int = 128\):
        self\.slice_size = slice_size
        self\.overlap = overlap
        self\.ai_analyzer = None
        
        # 存储缓存数据
        self\.ocr_cache = OCRCacheManager\(\)'''
        
        new_init = '''def __init__(self, slice_size: int = 1024, overlap: int = 128):
        self.slice_size = slice_size
        self.overlap = overlap
        self.ai_analyzer = None
        
        # 存储缓存数据
        self.ocr_cache = OCRCacheManager()
        self._vision_cache = {}  # 🔧 新增：Vision结果缓存'''
        
        # 执行替换
        new_content = content.replace(old_init, new_init)
        
        # 在Vision分析成功后添加缓存保存
        old_success = r'''if vision_result\["success"\]:
                    # 解析构件信息
                    components = self\._parse_vision_components\(vision_result\["data"\], slice_info\)
                    self\.slice_components\[f"\{slice_info\.row\}_\{slice_info\.col\}"\] = components
                    analyzed_count \+= 1'''
        
        new_success = '''if vision_result["success"]:
                    # 解析构件信息
                    components = self._parse_vision_components(vision_result["data"], slice_info)
                    cache_key = f"{slice_info.row}_{slice_info.col}"
                    self.slice_components[cache_key] = components
                    
                    # 🔧 新增：保存到Vision缓存
                    self._vision_cache[cache_key] = components
                    
                    analyzed_count += 1'''
        
        new_content = new_content.replace(old_success, new_success)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ 添加Vision缓存机制到 {file_path}")
        else:
            print(f"⚠️ {file_path} Vision缓存添加失败")
            
    except Exception as e:
        print(f"❌ 添加Vision缓存失败: {e}")

if __name__ == "__main__":
    fix_vision_duplicate_analysis() 