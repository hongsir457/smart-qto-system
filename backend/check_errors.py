from app.database import SessionLocal
from app.models.drawing import Drawing

def check_errors():
    db = SessionLocal()
    try:
        # 查找错误的图纸
        error_drawings = db.query(Drawing).filter(Drawing.status == 'error').order_by(Drawing.updated_at.desc()).limit(5).all()
        
        print("=== 最近的错误记录 ===")
        for d in error_drawings:
            print(f"图纸ID: {d.id}")
            print(f"文件名: {d.filename}")
            print(f"文件类型: {d.file_type}")
            print(f"错误信息: {d.error_message}")
            print(f"更新时间: {d.updated_at}")
            print("-" * 50)
            
        # 查找处理中的图纸
        processing_drawings = db.query(Drawing).filter(Drawing.status == 'processing').all()
        print(f"\n=== 处理中的图纸数量: {len(processing_drawings)} ===")
        
        # 查找ID为43的图纸
        drawing_43 = db.query(Drawing).filter(Drawing.id == 43).first()
        if drawing_43:
            print(f"\n=== 图纸ID 43 的状态 ===")
            print(f"状态: {drawing_43.status}")
            print(f"错误信息: {drawing_43.error_message}")
            print(f"文件路径: {drawing_43.file_path}")
            print(f"OCR结果: {drawing_43.ocr_results}")
            print(f"识别结果: {drawing_43.recognition_results}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_errors() 