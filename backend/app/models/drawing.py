from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, BigInteger, func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Drawing(Base):
    __tablename__ = "drawings"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)  # 修改为可选，因为文件可能存储在S3
    file_size = Column(BigInteger, nullable=True)  # 文件大小（字节）
    file_type = Column(String, nullable=True)  # pdf, dwg, dxf, jpg, png
    status = Column(String, default="uploaded")  # uploaded, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # S3存储相关字段
    s3_key = Column(String, nullable=True)  # S3文件键名
    s3_url = Column(String, nullable=True)  # S3文件访问URL
    s3_bucket = Column(String, nullable=True)  # S3桶名
    
    # OCR处理结果字段
    ocr_merged_result_key = Column(String, nullable=True)  # PaddleOCR合并结果存储键
    ocr_corrected_result_key = Column(String, nullable=True)  # GPT纠正后OCR结果存储键
    ocr_correction_summary = Column(JSON, nullable=True)  # OCR纠正处理摘要
    
    # 双轨协同分别保存的两个输出点
    ocr_recognition_display = Column(JSON, nullable=True)  # 轨道1输出：OCR识别块（图纸基本信息+构件概览）
    quantity_list_display = Column(JSON, nullable=True)   # 轨道2输出：工程量清单块（构件几何数据表格）
    
    # 处理结果相关字段
    recognition_results = Column(JSON, nullable=True)  # 保留兼容性：OCR和AI识别结果
    quantity_results = Column(JSON, nullable=True)  # 工程量计算结果
    processing_result = Column(JSON, nullable=True)  # 完整的处理结果JSON
    components_count = Column(Integer, nullable=True, default=0)  # 识别到的构件数量
    
    # 任务管理
    task_id = Column(String, nullable=True)  # 存储Celery任务ID
    celery_task_id = Column(String, nullable=True)  # Celery内部任务ID
    
    # 向后兼容的字段（逐步废弃）
    ocr_results = Column(JSON, nullable=True)
    s3_urls = Column(JSON, nullable=True)  # 废弃，改用s3_url
    
    # 时间字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 用户关系
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="drawings", passive_deletes=True)

    class Config:
        orm_mode = True 