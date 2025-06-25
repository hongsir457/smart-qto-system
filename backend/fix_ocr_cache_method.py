#!/usr/bin/env python3
"""
修复OCRCacheManager缺少get_cached_ocr方法的问题
"""

import re

def fix_ocr_cache_manager():
    """修复OCRCacheManager类，添加get_cached_ocr方法"""
    
    file_path = "app/utils/analysis_optimizations.py"
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找get_ocr_result方法的位置，在其前面添加get_cached_ocr方法
        pattern = r'(\s+)def get_ocr_result\(self, slice_key: str, cache_type: str = "auto"\) -> Optional\[Any\]:'
        
        replacement = r'''\1def get_cached_ocr(self, slice_key: str, cache_type: str = "auto") -> Optional[Any]:
\1    """获取缓存的OCR结果（get_ocr_result的别名）"""
\1    return self.get_ocr_result(slice_key, cache_type)
\1
\1def get_ocr_result(self, slice_key: str, cache_type: str = "auto") -> Optional[Any]:'''
        
        # 执行替换
        new_content = re.sub(pattern, replacement, content)
        
        # 检查是否替换成功
        if new_content != content:
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("✅ 成功修复OCRCacheManager，添加了get_cached_ocr方法")
            return True
        else:
            print("⚠️ 没有找到需要修复的内容")
            return False
            
    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    fix_ocr_cache_manager() 