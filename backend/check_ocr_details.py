from app.database import get_db
from app.models.drawing import Drawing
import json

# 获取数据库会话
db_gen = get_db()
db = next(db_gen)

# 查询图纸
drawing = db.query(Drawing).first()

if drawing:
    print(f'📊 图纸信息:')
    print(f'  ID: {drawing.id}')
    print(f'  文件名: {drawing.filename}')
    print(f'  状态: {drawing.status}')
    print(f'  是否有OCR结果: {drawing.ocr_results is not None}')
    
    if drawing.ocr_results:
        try:
            ocr_data = json.loads(drawing.ocr_results)
            print(f'\n🔍 OCR识别详情:')
            
            if 'text_regions' in ocr_data:
                text_regions = ocr_data['text_regions']
                print(f'  总文本数量: {len(text_regions)}项')
                
                print(f'\n📝 识别内容:')
                for i, item in enumerate(text_regions, 1):
                    text = item.get('text', '')
                    confidence = item.get('confidence', 0)
                    print(f'  [{i}] "{text}" (置信度: {confidence:.2f})')
                
                if 'statistics' in ocr_data:
                    stats = ocr_data['statistics']
                    print(f'\n📈 统计信息:')
                    for key, value in stats.items():
                        print(f'  {key}: {value}')
            else:
                print(f'  OCR数据格式: {list(ocr_data.keys())}')
                
        except json.JSONDecodeError as e:
            print(f'❌ JSON解析失败: {e}')
            print(f'  原始数据类型: {type(drawing.ocr_results)}')
            print(f'  原始数据长度: {len(drawing.ocr_results)}')
            print(f'  前100字符: {drawing.ocr_results[:100]}...')
    else:
        print('❌ 没有OCR结果')
else:
    print('❌ 没有找到图纸记录') 