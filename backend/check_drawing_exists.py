from app.database import get_db
from app.models.drawing import Drawing
from sqlalchemy.orm import Session

def check_drawings():
    """检查数据库中的图纸情况"""
    db = next(get_db())
    
    try:
        # 检查所有图纸
        drawings = db.query(Drawing).all()
        print(f"数据库中总共有 {len(drawings)} 个图纸:")
        
        for drawing in drawings:
            print(f"  ID: {drawing.id}, 文件名: {drawing.filename}, 状态: {drawing.status}, 用户ID: {drawing.user_id}")
        
        # 特别检查ID为2的图纸
        drawing_2 = db.query(Drawing).filter(Drawing.id == 2).first()
        if drawing_2:
            print(f"\nID为2的图纸存在:")
            print(f"  文件名: {drawing_2.filename}")
            print(f"  状态: {drawing_2.status}")
            print(f"  用户ID: {drawing_2.user_id}")
        else:
            print(f"\nID为2的图纸不存在")
            
    except Exception as e:
        print(f"检查过程中出现错误: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_drawings() 