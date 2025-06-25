# 通用工具函数
import re

def extract_dimension_value(dimension_str: str) -> float:
    if not dimension_str or dimension_str == '-':
        return 0.0
    numbers = re.findall(r'\d+\.?\d*', str(dimension_str))
    if numbers:
        value = float(numbers[0])
        if 'mm' in str(dimension_str):
            return value / 1000.0
        return value
    return 0.0 