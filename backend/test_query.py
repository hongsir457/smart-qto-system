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
    print(f'recognition_results类型: {type(recognition_results)}')
    
    if recognition_results:
        try:
            # 解析JSON数据
            data = json.loads(recognition_results)
            print(f'\n=== recognition_results 结构 ===')
            print(f'顶级键: {list(data.keys())}')
            
            if 'analysis_summary' in data:
                summary = data['analysis_summary']
                print(f'\nanalysis_summary: {summary}')
            
            if 'components' in data:
                components = data['components']
                print(f'\ncomponents数量: {len(components)}')
                print(f'构件清单:')
                for i, comp in enumerate(components):
                    print(f'  {i+1}. {comp}')
                    
        except Exception as e:
            print(f'解析recognition_results失败: {e}')
            print(f'尝试直接解析JSON...')
            try:
                data = json.loads(recognition_results)
                print(f'JSON解析成功!')
                print(f'顶级键: {list(data.keys())}')
                if 'components' in data:
                    components = data['components']
                    print(f'构件数量: {len(components)}')
                    for i, comp in enumerate(components):
                        print(f'  {i+1}. ID: {comp.get("component_id")}, 类型: {comp.get("component_type")}, 尺寸: {comp.get("dimensions")}')
            except Exception as e2:
                print(f'JSON解析也失败: {e2}')
else:
    print('未找到图纸ID=1的数据')

conn.close() 