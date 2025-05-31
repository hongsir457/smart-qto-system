#!/usr/bin/env python3
import sys
sys.path.append('.')

try:
    print("开始调试测试...")
    
    # 测试导入
    from app.api import deps
    from app.database import SessionLocal
    from app.models.drawing import Drawing as DrawingModel
    from app.models.user import User as UserModel
    from app.schemas.drawing import DrawingList
    print("✓ 所有模块导入成功")
    
    # 测试数据库连接
    db = SessionLocal()
    print("✓ 数据库连接成功")
    
    # 测试查询
    drawing_count = db.query(DrawingModel).count()
    user_count = db.query(UserModel).count()
    print(f"✓ 数据库查询成功 - 图纸记录: {drawing_count}, 用户记录: {user_count}")
    
    # 测试用户查询
    test_email = "oin1914@gamil.com"
    user = db.query(UserModel).filter(UserModel.email == test_email).first()
    if user:
        print(f"✓ 找到用户: {user.email}, ID: {user.id}")
        
        # 测试该用户的图纸查询
        user_drawings = db.query(DrawingModel).filter(DrawingModel.user_id == user.id).all()
        print(f"✓ 用户图纸数量: {len(user_drawings)}")
        
        # 测试分页查询
        page = 1
        size = 10
        skip = (page - 1) * size
        
        total = db.query(DrawingModel).filter(DrawingModel.user_id == user.id).count()
        drawings = db.query(DrawingModel).filter(
            DrawingModel.user_id == user.id
        ).order_by(DrawingModel.created_at.desc()).offset(skip).limit(size).all()
        
        print(f"✓ 分页查询成功 - 总数: {total}, 当前页: {len(drawings)}")
        
        # 测试创建DrawingList实例
        drawing_list = DrawingList(
            items=drawings,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        print(f"✓ DrawingList创建成功 - 页数: {drawing_list.pages}")
        
        # 测试序列化
        import json
        for drawing in drawings[:3]:  # 只测试前3条
            try:
                drawing_dict = {
                    "id": drawing.id,
                    "filename": drawing.filename,
                    "file_path": drawing.file_path,
                    "file_type": drawing.file_type,
                    "status": drawing.status,
                    "error_message": drawing.error_message,
                    "created_at": drawing.created_at.isoformat() if drawing.created_at else None,
                    "updated_at": drawing.updated_at.isoformat() if drawing.updated_at else None,
                    "user_id": drawing.user_id,
                    "recognition_results": drawing.recognition_results,
                    "ocr_results": drawing.ocr_results,
                    "task_id": drawing.task_id
                }
                json_str = json.dumps(drawing_dict, ensure_ascii=False)
                print(f"✓ 图纸 {drawing.id} 序列化成功")
            except Exception as e:
                print(f"✗ 图纸 {drawing.id} 序列化失败: {e}")
                print(f"  - filename: {drawing.filename}")
                print(f"  - recognition_results type: {type(drawing.recognition_results)}")
                print(f"  - ocr_results type: {type(drawing.ocr_results)}")
                
    else:
        print(f"✗ 未找到用户: {test_email}")
    
    db.close()
    print("✓ 调试测试完成")
    
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc() 