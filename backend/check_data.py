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
        # 直接解析JSON字符串
        data = json.loads(recognition_results)
        print(f'\n=== 识别结果数据结构 ===')
        print(f'顶级键: {list(data.keys())}')
        
        # 检查构件清单
        if 'components' in data:
            components = data['components']
            print(f'\n构件清单: {len(components)} 个')
            for i, comp in enumerate(components):
                print(f'  {i+1}. ID: {comp.get("component_id")}, 类型: {comp.get("component_type")}, 尺寸: {comp.get("dimensions")}')
        
        # 添加模拟的原始OCR文本数据到测试数据中
        print(f'\n需要添加原始OCR文本数据用于自然语言显示')
else:
    print('未找到图纸ID=1的数据')

conn.close() 