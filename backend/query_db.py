import sqlite3
import json

# 连接数据库
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# 首先查看所有图纸
cursor.execute('SELECT id, filename, status, components_count FROM drawings')
all_drawings = cursor.fetchall()

print(f'数据库中共有 {len(all_drawings)} 个图纸:')
for drawing in all_drawings:
    print(f'  ID: {drawing[0]}, 文件名: {drawing[1]}, 状态: {drawing[2]}, 构件数量: {drawing[3]}')

if all_drawings:
    # 查询第一个图纸的详细数据
    first_drawing_id = all_drawings[0][0]
    cursor.execute('SELECT id, filename, recognition_results, components_count FROM drawings WHERE id = ?', (first_drawing_id,))
    result = cursor.fetchone()
    
    if result:
        drawing_id, filename, recognition_results, components_count = result
        print(f'\n=== 图纸 {drawing_id} 详细信息 ===')
        print(f'文件名: {filename}')
        print(f'构件数量: {components_count}')
        
        if recognition_results:
            try:
                # 如果是字符串，先解析为JSON
                if isinstance(recognition_results, str):
                    data = json.loads(recognition_results)
                else:
                    data = recognition_results
                    
                print(f'\nrecognition_results 结构:')
                print(f'顶级键: {list(data.keys())}')
                
                if 'analysis_summary' in data:
                    summary = data['analysis_summary']
                    print(f'\nanalysis_summary: {summary}')
                
                if 'components' in data:
                    components = data['components']
                    print(f'\ncomponents数量: {len(components)}')
                    if components:
                        print(f'前3个构件: {components[:3]}')
                        
            except Exception as e:
                print(f'解析recognition_results失败: {e}')
                print(f'原始数据长度: {len(recognition_results)}')
                print(f'前200字符: {recognition_results[:200]}')
        else:
            print('recognition_results为空')

conn.close() 