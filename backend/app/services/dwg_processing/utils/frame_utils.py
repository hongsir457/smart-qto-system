# 图框工具函数
# 这里迁移frame_utils.py的内容，如有需要可补充

# 示例：
def safe_filename(s: str) -> str:
    import re
    return re.sub(r'[\\/:*?"<>|%\s]+', '_', s) 