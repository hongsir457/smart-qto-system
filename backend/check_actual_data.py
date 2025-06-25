from app.database import get_db
from app.models.drawing import Drawing
import json

def check_data():
    session = next(get_db())
    drawing = session.query(Drawing).filter(Drawing.id == 1).first()
    
    print("=== 检查实际数据内容 ===")
    print(f"图纸ID: {drawing.id}")
    print(f"文件名: {drawing.filename}")
    print(f"状态: {drawing.status}")
    print()
    
    pr = drawing.processing_result
    if pr:
        print(f"processing_result类型: {type(pr)}")
        print(f"processing_result键数量: {len(pr.keys())}")
        
        # 显示所有键
        print("所有键:")
        for i, key in enumerate(pr.keys(), 1):
            print(f"  {i}. {key}")
        
        print()
        
        # 检查是否有新添加的键
        recent_keys = [k for k in pr.keys() if any(x in k for x in ['result_', 'pipeline_', 'human_readable'])]
        if recent_keys:
            print("可能相关的键:")
            for key in recent_keys:
                value = pr[key]
                if isinstance(value, dict):
                    print(f"  {key}: dict with keys {list(value.keys())}")
                    if 's3_url' in value:
                        print(f"    s3_url: {value['s3_url']}")
                else:
                    print(f"  {key}: {type(value)} = {str(value)[:100]}")
        else:
            print("❌ 未找到A→B→C相关键")
    
    session.close()

if __name__ == "__main__":
    check_data() 