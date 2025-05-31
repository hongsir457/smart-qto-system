import psycopg2
import json

def analyze_drawing_47():
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host="dbconn.sealoshzh.site",
            port=48982,
            database="postgres",
            user="postgres",
            password="2xn59xgm"
        )
        cursor = conn.cursor()
        
        # 获取图纸47的识别结果
        cursor.execute('SELECT id, filename, status, recognition_results FROM drawings WHERE id = 47')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        print(f"图纸ID: {row[0]}")
        print(f"文件名: {row[1]}")
        print(f"状态: {row[2]}")
        
        if row[3]:
            results = row[3]
            
            # 分析识别结果
            print("\n=== 识别结果分析 ===")
            
            # 统计各类构件数量
            if 'walls' in results:
                print(f"墙体数量: {len(results['walls'])}")
                if results['walls']:
                    print("墙体示例:")
                    for i, wall in enumerate(results['walls'][:3]):  # 显示前3个
                        print(f"  墙体{i+1}: bbox={wall.get('bbox')}, 置信度={wall.get('confidence')}")
            
            if 'columns' in results:
                print(f"柱子数量: {len(results['columns'])}")
                if results['columns']:
                    print("柱子示例:")
                    for i, col in enumerate(results['columns'][:3]):
                        print(f"  柱子{i+1}: bbox={col.get('bbox')}, 置信度={col.get('confidence')}")
            
            if 'beams' in results:
                print(f"梁数量: {len(results['beams'])}")
                if results['beams']:
                    print("梁示例:")
                    for i, beam in enumerate(results['beams'][:3]):
                        print(f"  梁{i+1}: bbox={beam.get('bbox')}, 置信度={beam.get('confidence')}")
            
            if 'slabs' in results:
                print(f"板数量: {len(results['slabs'])}")
            
            if 'foundations' in results:
                print(f"基础数量: {len(results['foundations'])}")
                if results['foundations']:
                    print("基础示例:")
                    for i, found in enumerate(results['foundations'][:3]):
                        print(f"  基础{i+1}: bbox={found.get('bbox')}, 置信度={found.get('confidence')}")
            
            # 检查是否有工程量计算结果
            if 'quantities' in results:
                print("\n=== 工程量计算结果 ===")
                quantities = results['quantities']
                for key, value in quantities.items():
                    if isinstance(value, list):
                        print(f"{key}: {len(value)} 项")
                    else:
                        print(f"{key}: {value}")
            
            # 检查OCR结果
            if 'ocr_results' in results:
                print("\n=== OCR识别结果 ===")
                ocr_results = results['ocr_results']
                if isinstance(ocr_results, list):
                    print(f"识别到 {len(ocr_results)} 个文本区域")
                    for i, ocr in enumerate(ocr_results[:5]):  # 显示前5个
                        if isinstance(ocr, dict) and 'text' in ocr:
                            print(f"  文本{i+1}: {ocr['text']}")
                        elif isinstance(ocr, list) and len(ocr) >= 2:
                            print(f"  文本{i+1}: {ocr[1]}")
            
            # 检查图纸信息
            if 'drawing_info' in results:
                print("\n=== 图纸信息 ===")
                drawing_info = results['drawing_info']
                for key, value in drawing_info.items():
                    print(f"{key}: {value}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    analyze_drawing_47() 