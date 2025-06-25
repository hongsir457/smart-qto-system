#!/usr/bin/env python3
"""检查S3存储状态"""

from app.database import get_db
from app.models.drawing import Drawing
import json
import requests

def check_s3_storage():
    print("🔍 检查S3存储状态")
    print("=" * 60)
    
    session = next(get_db())
    try:
        drawing = session.query(Drawing).filter(Drawing.id == 1).first()
        
        if not drawing:
            print("❌ 图纸不存在")
            return
            
        if not drawing.processing_result:
            print("❌ processing_result为空")
            return
            
        # 解析processing_result
        if isinstance(drawing.processing_result, str):
            pr = json.loads(drawing.processing_result)
        else:
            pr = drawing.processing_result
            
        print(f"📊 图纸信息: {drawing.filename}")
        
        if 'human_readable_txt' in pr:
            hrt = pr['human_readable_txt']
            print('\n=== 数据库中的S3存储信息 ===')
            print(f'S3 URL: {hrt.get("s3_url", "未找到")}')
            print(f'文件名: {hrt.get("filename", "未找到")}')
            print(f'是否已保存: {hrt.get("is_human_readable", "未知")}')
            print(f'总OCR文本数: {hrt.get("total_ocr_texts", "未知")}')
            print(f'保存时间: {hrt.get("save_time", "未知")}')
            
            # 测试S3链接是否可访问
            s3_url = hrt.get('s3_url')
            if s3_url:
                print(f'\n=== 测试S3链接可访问性 ===')
                print(f'完整URL: {s3_url}')
                
                try:
                    response = requests.head(s3_url, timeout=10)
                    print(f'S3响应状态码: {response.status_code}')
                    if response.status_code == 200:
                        print('✅ S3文件存在且可访问')
                        
                        # 获取文件内容检查
                        try:
                            content_response = requests.get(s3_url, timeout=10)
                            if content_response.status_code == 200:
                                content = content_response.text
                                print(f'✅ 文件内容长度: {len(content)} 字符')
                                print(f'✅ 内容预览: {content[:200]}...')
                            else:
                                print(f'⚠️ 获取内容失败: {content_response.status_code}')
                        except Exception as e:
                            print(f'⚠️ 获取内容异常: {e}')
                            
                    elif response.status_code == 404:
                        print('❌ S3文件不存在 (404) - 上传可能失败')
                    elif response.status_code == 403:
                        print('⚠️ S3文件存在但权限不足 (403)')
                    else:
                        print(f'⚠️ S3访问异常: {response.status_code}')
                except Exception as e:
                    print(f'❌ S3访问失败: {e}')
                    
                # 解析S3 URL结构
                print(f'\n=== S3 URL结构分析 ===')
                if s3_url.startswith('https://'):
                    parts = s3_url.replace('https://', '').split('/')
                    if len(parts) >= 2:
                        domain = parts[0]
                        bucket_path = '/'.join(parts[1:])
                        print(f'S3域名: {domain}')
                        print(f'存储桶路径: {bucket_path}')
                        
                        # 提取存储桶名称
                        if 'sealos.run' in domain:
                            bucket_name = domain.split('.')[0]
                            print(f'存储桶名称: {bucket_name}')
                            print(f'文件路径: {bucket_path}')
            else:
                print('❌ 数据库中没有S3 URL')
        else:
            print('❌ 数据库中没有human_readable_txt字段')
            
        # 检查其他可能的存储字段
        print(f'\n=== processing_result所有字段 ===')
        for key in pr.keys():
            print(f'- {key}')
            
    except Exception as e:
        print(f'❌ 检查失败: {e}')
    finally:
        session.close()

if __name__ == "__main__":
    check_s3_storage() 