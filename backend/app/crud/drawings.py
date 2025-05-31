from sqlalchemy.orm import Session
from app.models.drawing import Drawing
from app.models.user import User

def get(db: Session, drawing_id: int) -> Drawing:
    """
    获取单个图纸
    """
    return db.query(Drawing).filter(Drawing.id == drawing_id).first()

def get_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """
    获取用户的所有图纸
    """
    return db.query(Drawing).filter(Drawing.user_id == user_id).offset(skip).limit(limit).all()

def create(db: Session, drawing_data: dict, user_id: int) -> Drawing:
    """
    创建新图纸
    """
    drawing = Drawing(**drawing_data, user_id=user_id)
    db.add(drawing)
    db.commit()
    db.refresh(drawing)
    return drawing

def update(db: Session, drawing_id: int, drawing_data: dict) -> Drawing:
    """
    更新图纸信息
    """
    drawing = get(db, drawing_id)
    if drawing:
        for key, value in drawing_data.items():
            setattr(drawing, key, value)
        db.commit()
        db.refresh(drawing)
    return drawing

def delete(db: Session, drawing_id: int):
    """
    删除图纸
    """
    drawing = get(db, drawing_id)
    if drawing:
        db.delete(drawing)
        db.commit()
    return drawing 