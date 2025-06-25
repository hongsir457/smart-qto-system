import sqlite3
import json

# 连接数据库
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# 查询图纸ID=1的详细数据
cursor.execute('SELECT id, filename, recognition_results, components_count FROM drawings WHERE id = 1')
result = cursor.fetchone()

if result:
    drawing_id, filename, recognition_results, components_count = result
    print(f'图纸ID: {drawing_id}')
    print(f'文件名: {filename}')
    print(f'构件数量: {components_count}')
    
    if recognition_results:
        try:
            # 解析JSON数据
            if isinstance(recognition_results, str):
                data = json.loads(recognition_results)
            else:
                data = recognition_results
                
            print(f'\n=== 识别结果数据结构 ===')
            print(f'顶级键: {list(data.keys())}')
            
            # 检查是否有原始OCR文本数据
            if 'ocr_texts' in data:
                print(f'\n原始OCR文本数据: {len(data["ocr_texts"])} 项')
                for i, text in enumerate(data['ocr_texts'][:5]):
                    print(f'  {i+1}. {text}')
            
            # 检查构件清单
            if 'components' in data:
                components = data['components']
                print(f'\n构件清单: {len(components)} 个')
                for i, comp in enumerate(components):
                    print(f'  {i+1}. ID: {comp.get("component_id")}, 类型: {comp.get("component_type")}, 尺寸: {comp.get("dimensions")}')
                    
        except Exception as e:
            print(f'解析recognition_results失败: {e}')
            print(f'数据类型: {type(recognition_results)}')
else:
    print('未找到图纸ID=1的数据')

conn.close() 