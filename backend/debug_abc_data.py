from app.database import get_db
from app.models.drawing import Drawing
import json

session = next(get_db())
drawing = session.query(Drawing).filter(Drawing.id == 1).first()

print("=== 调试A→B→C数据存储 ===")
pr = drawing.processing_result

print("processing_result类型:", type(pr))
print("processing_result键:", list(pr.keys()) if isinstance(pr, dict) else "非字典类型")
print()

# 检查是否有pipeline相关字段
pipeline_keys = ['pipeline_id', 'pipeline_status', 'processing_time']
for key in pipeline_keys:
    if key in pr:
        print(f"{key}: {pr[key]}")

print()

# 检查所有包含 'result' 的键
result_keys = [k for k in pr.keys() if 'result' in k.lower()]
print("包含'result'的键:", result_keys)

for key in result_keys:
    value = pr[key]
    print(f"{key}: {type(value)} - {str(value)[:100]}...")

session.close() 