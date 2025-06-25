#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查图纸OCR结果
"""

from app.database import get_db
from app.models.drawing import Drawing
from sqlalchemy.orm import Session

def check_drawing_ocr():
    """检查图纸OCR结果"""
    # 获取数据库会话
    db_gen = get_db()
    db = next(db_gen)

    try:
        # 查询图纸ID=1的OCR结果
        drawing = db.query(Drawing).filter(Drawing.id == 1).first()
        if drawing:
            print(f'图纸ID: {drawing.id}')
            print(f'文件名: {drawing.filename}')
            print(f'状态: {drawing.status}')
            print(f'有OCR结果: {drawing.ocr_results is not None}')
            if drawing.ocr_results:
                print(f'OCR结果长度: {len(str(drawing.ocr_results))}')
                print(f'OCR结果类型: {type(drawing.ocr_results)}')
                # 显示OCR结果的前100个字符
                ocr_str = str(drawing.ocr_results)[:200]
                print(f'OCR结果预览: {ocr_str}...')
            else:
                print('OCR结果为空')
        else:
            print('未找到图纸ID=1')
    finally:
        db.close()

if __name__ == "__main__":
    check_drawing_ocr() 