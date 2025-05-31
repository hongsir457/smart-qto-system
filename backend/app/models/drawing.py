from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Drawing(Base):
    __tablename__ = "drawings"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, dwg, dxf
    status = Column(String, default="pending")  # pending, processing, completed, error
    error_message = Column(Text, nullable=True)
    recognition_results = Column(JSON, nullable=True)
    ocr_results = Column(JSON, nullable=True)
    task_id = Column(String, nullable=True)  # 存储Celery任务ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="drawings") 

    class Config:
        orm_mode = True 