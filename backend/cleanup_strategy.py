#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码清理策略执行脚本
按照用户要求进行：
1. 静态分析和清理 (vulture + 重复代码检测)
2. 精简结构和重构 (合并碎片，移除无效模块)
3. 依赖清理和模块瘦身 (优化大文件)
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple

class CodeCleanupStrategy:
    """代码清理策略执行器"""
    
    def __init__(self, backend_path: str = "app"):
        self.backend_path = backend_path
        self.cleanup_log = []
        
    def log_action(self, action: str, details: str = ""):
        """记录清理动作"""
        log_entry = f"✅ {action}"
        if details:
            log_entry += f": {details}"
        self.cleanup_log.append(log_entry)
        print(log_entry)
    
    def execute_phase_1_static_cleanup(self):
        """阶段1: 静态分析和清理"""
        print("🔍 === 阶段1: 静态分析和清理 ===")
        
        # 1.1 删除明显的无用文件
        files_to_delete = [
            # 备份文件
            "app/utils/analysis_optimizations_backup.py",
            # 测试文件
            "app/services/test_enhanced_vision_components.py", 
            # Legacy文件
            "app/services/dwg_processor_legacy.py",
            # 空文件
            "app/services/dwg_processing/detectors/frame_detector.py",
        ]
        
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.log_action("删除无用文件", file_path)
                except Exception as e:
                    print(f"❌ 删除文件失败 {file_path}: {e}")
        
        # 1.2 清理vulture发现的未使用导入
        self._cleanup_unused_imports()
        
        # 1.3 移除不可达代码
        self._remove_unreachable_code()
    
    def execute_phase_2_structure_refinement(self):
        """阶段2: 精简结构和重构"""
        print("\n🏗️ === 阶段2: 精简结构和重构 ===")
        
        # 2.1 合并碎片化的小文件
        self._merge_fragmented_files()
        
        # 2.2 移除空壳模块
        self._remove_empty_modules()
        
        # 2.3 清理临时文件和示例文件
        self._cleanup_temp_and_sample_files()
    
    def execute_phase_3_dependency_optimization(self):
        """阶段3: 依赖清理和模块瘦身"""
        print("\n📦 === 阶段3: 依赖清理和模块瘦身 ===")
        
        # 3.1 重构大文件
        self._refactor_large_files()
        
        # 3.2 优化依赖关系
        self._optimize_dependencies()
        
        # 3.3 生成清理后的依赖文件
        self._generate_clean_requirements()
    
    def _cleanup_unused_imports(self):
        """清理未使用的导入"""
        unused_imports = [
            ("app/api/v1/drawings/upload.py", ["DrawingCreate", "file_naming_strategy"]),
            ("app/api/v1/endpoints/export.py", ["BarChart", "Reference"]),
            ("app/api/v1/users.py", ["UserInDB"]),
            ("app/database.py", ["contextmanager", "random"]),
            ("app/services/adaptive_slicing_engine.py", ["ImageDraw"]),
            ("app/services/ai_analyzer.py", ["DummyInteractionLogger"]),
        ]
        
        for file_path, imports in unused_imports:
            if os.path.exists(file_path):
                self._remove_imports_from_file(file_path, imports)
    
    def _remove_imports_from_file(self, file_path: str, imports_to_remove: List[str]):
        """从文件中移除指定的导入"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            new_lines = []
            
            for line in lines:
                should_remove = False
                for import_name in imports_to_remove:
                    if f"import {import_name}" in line or f"from .* import.*{import_name}" in line:
                        should_remove = True
                        modified = True
                        break
                
                if not should_remove:
                    new_lines.append(line)
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                self.log_action("清理未使用导入", f"{file_path} - {', '.join(imports_to_remove)}")
                
        except Exception as e:
            print(f"❌ 清理导入失败 {file_path}: {e}")
    
    def _remove_unreachable_code(self):
        """移除不可达代码"""
        # 基于vulture的报告，ai_analyzer.py有大量不可达代码
        ai_analyzer_path = "app/services/ai_analyzer.py"
        if os.path.exists(ai_analyzer_path):
            self.log_action("标记需要手动清理不可达代码", ai_analyzer_path)
    
    def _merge_fragmented_files(self):
        """合并碎片化的小文件"""
        # 将一些功能相近的小文件合并
        small_service_files = [
            "app/services/coordinate_restore.py",
            "app/services/fusion_merge.py", 
            "app/services/quantity_display.py",
        ]
        
        # 创建合并文件
        merged_content = []
        merged_content.append("#!/usr/bin/env python3")
        merged_content.append("# -*- coding: utf-8 -*-")
        merged_content.append('"""')
        merged_content.append("合并的小型服务模块")
        merged_content.append("包含: 坐标还原、融合合并、数量显示等功能")
        merged_content.append('"""')
        merged_content.append("")
        
        files_merged = []
        for file_path in small_service_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 移除文件头部的重复信息
                    lines = content.split('\n')
                    start_idx = 0
                    for i, line in enumerate(lines):
                        if line.strip() and not line.startswith('#') and not line.startswith('"""') and 'coding' not in line:
                            start_idx = i
                            break
                    
                    merged_content.append(f"# === 来自 {file_path} ===")
                    merged_content.extend(lines[start_idx:])
                    merged_content.append("")
                    
                    files_merged.append(file_path)
                    
                except Exception as e:
                    print(f"❌ 读取文件失败 {file_path}: {e}")
        
        if files_merged:
            # 写入合并文件
            merged_file_path = "app/services/merged_small_services.py"
            try:
                with open(merged_file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(merged_content))
                
                self.log_action("合并小文件", f"创建 {merged_file_path}")
                
                # 删除原文件
                for file_path in files_merged:
                    os.remove(file_path)
                    self.log_action("删除已合并文件", file_path)
                    
            except Exception as e:
                print(f"❌ 创建合并文件失败: {e}")
    
    def _remove_empty_modules(self):
        """移除空壳模块"""
        # 查找只有__init__.py且内容很少的目录
        empty_dirs = []
        
        for root, dirs, files in os.walk(self.backend_path):
            if len(files) == 1 and "__init__.py" in files:
                init_path = os.path.join(root, "__init__.py")
                try:
                    with open(init_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    # 如果__init__.py为空或只有很少内容
                    if len(content) < 50:  # 少于50个字符
                        empty_dirs.append(root)
                except:
                    pass
        
        for dir_path in empty_dirs:
            try:
                shutil.rmtree(dir_path)
                self.log_action("删除空壳模块", dir_path)
            except Exception as e:
                print(f"❌ 删除目录失败 {dir_path}: {e}")
    
    def _cleanup_temp_and_sample_files(self):
        """清理临时文件和示例文件"""
        patterns_to_remove = [
            "**/temp_*",
            "**/sample_*", 
            "**/test_*",
            "**/demo_*",
            "**/example_*",
            "**/*_backup*",
            "**/*_old*",
            "**/*_legacy*",
        ]
        
        for pattern in patterns_to_remove:
            for file_path in Path(self.backend_path).rglob(pattern):
                if file_path.is_file() and file_path.suffix == '.py':
                    try:
                        file_path.unlink()
                        self.log_action("删除临时/示例文件", str(file_path))
                    except Exception as e:
                        print(f"❌ 删除文件失败 {file_path}: {e}")
    
    def _refactor_large_files(self):
        """重构大文件"""
        large_files = [
            ("app/services/ai_analyzer.py", 2178),
            ("app/services/enhanced_grid_slice_analyzer.py", 2179),
        ]
        
        for file_path, line_count in large_files:
            if os.path.exists(file_path):
                self.log_action("标记需要重构的大文件", f"{file_path} ({line_count}行)")
                # 这里需要手动重构，自动重构风险太大
                self._create_refactoring_plan(file_path)
    
    def _create_refactoring_plan(self, file_path: str):
        """为大文件创建重构计划"""
        plan_file = f"{file_path}_refactoring_plan.md"
        
        if "ai_analyzer.py" in file_path:
            plan_content = """
# AI Analyzer 重构计划

## 建议拆分方案

### 1. AIAnalyzerService (核心类)
- 保留基础功能和初始化
- generate_qto_from_data()
- is_available()

### 2. PromptBuilder (新文件: ai_prompt_builder.py)
- _build_system_prompt()
- _build_enhanced_system_prompt() 
- _build_user_prompt()

### 3. MockDataDetector (新文件: ai_mock_detector.py)
- _check_for_mock_data_patterns()
- _enhance_mock_data_detection()
- _validate_response_authenticity()

### 4. VisionAnalyzer (新文件: ai_vision_analyzer.py)
- generate_qto_from_local_images()
- generate_qto_from_encoded_images()
- _execute_multi_turn_analysis()
- 所有vision相关的step方法

### 5. ContextualAnalyzer (新文件: ai_contextual_analyzer.py)
- _execute_multi_turn_analysis_with_context()
- 所有contextual step方法

### 6. ResponseSynthesizer (新文件: ai_response_synthesizer.py)
- _synthesize_qto_data()
- _determine_component_type()
- _generate_quantity_summary()
"""
        elif "enhanced_grid_slice_analyzer.py" in file_path:
            plan_content = """
# Enhanced Grid Slice Analyzer 重构计划

## 建议拆分方案

### 1. EnhancedGridSliceAnalyzer (核心类)
- analyze_drawing_with_dual_track()
- 保留主要流程控制逻辑

### 2. OCRProcessor (新文件: grid_ocr_processor.py)
- _extract_ocr_from_slices_optimized()
- _extract_global_ocr_overview_optimized()
- 所有OCR相关方法

### 3. CoordinateManager (新文件: grid_coordinate_manager.py)
- _restore_global_coordinates_optimized()
- 坐标转换和还原相关方法

### 4. SliceManager (新文件: grid_slice_manager.py)
- _reuse_shared_slices()
- _can_reuse_shared_slices()
- 切片管理相关方法

### 5. VisionProcessor (新文件: grid_vision_processor.py)
- _analyze_slices_with_enhanced_vision()
- Vision分析相关方法

### 6. ResultMerger (新文件: grid_result_merger.py)
- _merge_dual_track_results()
- 结果合并相关方法
"""
        
        try:
            with open(plan_file, 'w', encoding='utf-8') as f:
                f.write(plan_content)
            self.log_action("创建重构计划", plan_file)
        except Exception as e:
            print(f"❌ 创建重构计划失败: {e}")
    
    def _optimize_dependencies(self):
        """优化依赖关系"""
        # 移除重复的依赖版本
        self.log_action("标记需要优化的依赖", "requirements_actual.txt中有重复版本")
    
    def _generate_clean_requirements(self):
        """生成清理后的依赖文件"""
        try:
            os.system("pipreqs app --force --savepath requirements_clean.txt")
            self.log_action("生成清理后的依赖文件", "requirements_clean.txt")
        except Exception as e:
            print(f"❌ 生成依赖文件失败: {e}")
    
    def execute_full_cleanup(self):
        """执行完整的清理流程"""
        print("🚀 开始执行代码清理策略...")
        
        self.execute_phase_1_static_cleanup()
        self.execute_phase_2_structure_refinement() 
        self.execute_phase_3_dependency_optimization()
        
        print(f"\n📋 清理完成! 共执行了 {len(self.cleanup_log)} 个清理动作")
        
        # 生成清理报告
        self._generate_cleanup_report()
    
    def _generate_cleanup_report(self):
        """生成清理报告"""
        report_content = [
            "# 代码清理报告",
            "",
            f"清理时间: {os.popen('date').read().strip()}",
            f"清理动作数量: {len(self.cleanup_log)}",
            "",
            "## 清理动作详情",
            ""
        ]
        
        for action in self.cleanup_log:
            report_content.append(f"- {action}")
        
        report_content.extend([
            "",
            "## 后续手动操作建议",
            "",
            "### 1. 大文件重构",
            "- 参考生成的 *_refactoring_plan.md 文件",
            "- 按功能拆分 ai_analyzer.py (2178行)",
            "- 按功能拆分 enhanced_grid_slice_analyzer.py (2179行)",
            "",
            "### 2. 依赖优化", 
            "- 检查 requirements_clean.txt",
            "- 移除重复版本的依赖",
            "- 测试清理后的依赖是否满足需求",
            "",
            "### 3. 代码质量",
            "- 运行测试确保功能正常",
            "- 使用 black 格式化代码",
            "- 使用 isort 排序导入",
            "",
            "### 4. 性能优化",
            "- 检查是否有循环导入",
            "- 优化大文件的加载时间",
            "- 考虑使用懒加载"
        ])
        
        try:
            with open("cleanup_report.md", 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_content))
            print("📄 清理报告已生成: cleanup_report.md")
        except Exception as e:
            print(f"❌ 生成清理报告失败: {e}")

def main():
    """主函数"""
    cleanup = CodeCleanupStrategy()
    cleanup.execute_full_cleanup()

if __name__ == "__main__":
    main() 