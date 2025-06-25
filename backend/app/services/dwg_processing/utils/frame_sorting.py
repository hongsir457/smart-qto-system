# 图框排序相关方法

def sort_drawings_by_number(drawings):
    """按图号自然顺序排序图框列表"""
    import re
    def natural_sort_key(drawing):
        s = drawing.get('drawing_number', '')
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
    return sorted(drawings, key=natural_sort_key) 