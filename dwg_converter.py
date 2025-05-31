#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWG文件检测和转换工具
"""

import os
import psycopg2
import requests
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

class DWGConverter:
    def __init__(self, db_config):
        self.db_config = db_config
        self.temp_dir = tempfile.mkdtemp(prefix="dwg_converter_")
        
    def connect_db(self):
        """连接数据库"""
        return psycopg2.connect(**self.db_config)
    
    def detect_file_type(self, filename):
        """检测文件类型"""
        file_extension = Path(filename).suffix.lower()
        
        file_types = {
            '.dwg': 'AutoCAD DWG',
            '.dxf': 'AutoCAD DXF', 
            '.pdf': 'PDF',
            '.jpg': 'JPEG Image',
            '.jpeg': 'JPEG Image',
            '.png': 'PNG Image',
            '.tiff': 'TIFF Image',
            '.tif': 'TIFF Image'
        }
        
        return {
            'extension': file_extension,
            'type': file_types.get(file_extension, 'Unknown'),
            'is_cad': file_extension in ['.dwg', '.dxf'],
            'is_dwg': file_extension == '.dwg',
            'is_dxf': file_extension == '.dxf',
            'needs_conversion': file_extension == '.dwg'
        }
    
    def download_file(self, url, local_path):
        """下载文件到本地"""
        try:
            print(f"正在下载文件: {url}")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(local_path)
            print(f"文件下载完成: {file_size} 字节")
            return True
            
        except Exception as e:
            print(f"文件下载失败: {e}")
            return False
    
    def detect_dwg_layouts(self, dwg_file_path):
        """检测DWG文件中的布局数量"""
        try:
            # 尝试使用ezdxf检测布局（如果可用）
            try:
                import ezdxf
                # 注意：ezdxf主要用于DXF文件，对DWG支持有限
                # 这里提供一个框架，实际可能需要其他工具
                print("尝试使用ezdxf检测布局...")
                return {'layouts': ['Model'], 'count': 1, 'method': 'ezdxf_fallback'}
                
            except ImportError:
                print("ezdxf不可用，使用文件大小估算")
                
            # 基于文件大小的简单估算
            file_size = os.path.getsize(dwg_file_path)
            
            # 简单的启发式方法：根据文件大小估算可能的图纸数量
            if file_size < 1024 * 1024:  # < 1MB
                estimated_layouts = 1
            elif file_size < 5 * 1024 * 1024:  # < 5MB
                estimated_layouts = 1
            elif file_size < 20 * 1024 * 1024:  # < 20MB
                estimated_layouts = 2
            else:  # >= 20MB
                estimated_layouts = max(1, file_size // (10 * 1024 * 1024))  # 每10MB估算1张图
            
            return {
                'layouts': [f'Layout_{i+1}' for i in range(int(estimated_layouts))],
                'count': int(estimated_layouts),
                'method': 'size_estimation',
                'file_size_mb': file_size / (1024 * 1024)
            }
            
        except Exception as e:
            print(f"布局检测失败: {e}")
            return {'layouts': ['Default'], 'count': 1, 'method': 'fallback'}
    
    def convert_dwg_to_dxf_with_oda(self, dwg_path, output_dir):
        """使用ODA File Converter转换DWG到DXF"""
        try:
            # 检查ODA File Converter是否可用
            oda_paths = [
                r"C:\Program Files\ODA\ODAFileConverter_25.4.0\ODAFileConverter.exe",
                r"C:\Program Files (x86)\ODA\ODAFileConverter_25.4.0\ODAFileConverter.exe",
                "ODAFileConverter.exe"  # 如果在PATH中
            ]
            
            oda_exe = None
            for path in oda_paths:
                if os.path.exists(path):
                    oda_exe = path
                    break
            
            if not oda_exe:
                # 尝试在PATH中查找
                try:
                    subprocess.run(["ODAFileConverter.exe"], 
                                 capture_output=True, timeout=5)
                    oda_exe = "ODAFileConverter.exe"
                except:
                    pass
            
            if not oda_exe:
                return {
                    'success': False,
                    'error': 'ODA File Converter not found',
                    'suggestion': 'Please install ODA File Converter from https://www.opendesign.com/guestfiles'
                }
            
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 构建转换命令
            cmd = [
                oda_exe,
                str(dwg_path),
                str(output_dir),
                "ACAD2018",  # 输出版本
                "DXF",       # 输出格式
                "0",         # 递归处理子目录
                "1",         # 审计和修复
                "*"          # 文件过滤器
            ]
            
            print(f"执行转换命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 查找生成的DXF文件
                dxf_files = list(Path(output_dir).glob("*.dxf"))
                return {
                    'success': True,
                    'dxf_files': [str(f) for f in dxf_files],
                    'count': len(dxf_files),
                    'output_dir': output_dir
                }
            else:
                return {
                    'success': False,
                    'error': f'Conversion failed with code {result.returncode}',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Conversion timeout (>5 minutes)'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def convert_dwg_with_python_libs(self, dwg_path, output_dir):
        """尝试使用Python库转换DWG"""
        try:
            # 尝试使用dwg2dxf（如果可用）
            try:
                import dwg2dxf
                output_file = os.path.join(output_dir, 
                                         Path(dwg_path).stem + ".dxf")
                dwg2dxf.convert(dwg_path, output_file)
                
                if os.path.exists(output_file):
                    return {
                        'success': True,
                        'dxf_files': [output_file],
                        'count': 1,
                        'method': 'dwg2dxf'
                    }
                    
            except ImportError:
                print("dwg2dxf库不可用")
            except Exception as e:
                print(f"dwg2dxf转换失败: {e}")
            
            # 其他Python转换方法可以在这里添加
            
            return {
                'success': False,
                'error': 'No Python DWG conversion library available'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_drawing_file(self, drawing_id):
        """处理指定的图纸文件"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        try:
            # 获取图纸信息
            cursor.execute('''
                SELECT id, filename, file_path, status
                FROM drawings WHERE id = %s
            ''', (drawing_id,))
            
            row = cursor.fetchone()
            if not row:
                return {'error': f'Drawing {drawing_id} not found'}
            
            drawing_id, filename, file_url, status = row
            
            print(f"=" * 80)
            print(f"处理图纸 {drawing_id}: {filename}")
            print(f"=" * 80)
            
            # 检测文件类型
            file_info = self.detect_file_type(filename)
            print(f"文件类型检测:")
            print(f"  扩展名: {file_info['extension']}")
            print(f"  类型: {file_info['type']}")
            print(f"  是否CAD文件: {file_info['is_cad']}")
            print(f"  是否需要转换: {file_info['needs_conversion']}")
            print()
            
            if not file_info['needs_conversion']:
                print(f"文件无需转换，类型: {file_info['type']}")
                return {
                    'success': True,
                    'message': 'No conversion needed',
                    'file_type': file_info['type']
                }
            
            # 下载DWG文件
            local_dwg_path = os.path.join(self.temp_dir, filename)
            if not self.download_file(file_url, local_dwg_path):
                return {'error': 'Failed to download file'}
            
            # 检测布局
            layout_info = self.detect_dwg_layouts(local_dwg_path)
            print(f"布局检测结果:")
            print(f"  检测方法: {layout_info['method']}")
            print(f"  布局数量: {layout_info['count']}")
            print(f"  布局列表: {layout_info['layouts']}")
            if 'file_size_mb' in layout_info:
                print(f"  文件大小: {layout_info['file_size_mb']:.2f} MB")
            print()
            
            # 创建转换输出目录
            output_dir = os.path.join(self.temp_dir, f"converted_{drawing_id}")
            os.makedirs(output_dir, exist_ok=True)
            
            # 尝试转换
            print("开始DWG到DXF转换...")
            
            # 首先尝试ODA File Converter
            conversion_result = self.convert_dwg_to_dxf_with_oda(local_dwg_path, output_dir)
            
            if not conversion_result['success']:
                print(f"ODA转换失败: {conversion_result.get('error', 'Unknown error')}")
                print("尝试Python库转换...")
                
                # 尝试Python库转换
                conversion_result = self.convert_dwg_with_python_libs(local_dwg_path, output_dir)
            
            if conversion_result['success']:
                print(f"✅ 转换成功!")
                print(f"生成的DXF文件:")
                for dxf_file in conversion_result['dxf_files']:
                    file_size = os.path.getsize(dxf_file)
                    print(f"  - {os.path.basename(dxf_file)} ({file_size} 字节)")
                
                return {
                    'success': True,
                    'original_file': filename,
                    'layout_info': layout_info,
                    'conversion_result': conversion_result,
                    'temp_dir': self.temp_dir
                }
            else:
                print(f"❌ 转换失败: {conversion_result.get('error', 'Unknown error')}")
                
                # 提供手动转换建议
                print(f"\n💡 手动转换建议:")
                print(f"1. 下载文件: {file_url}")
                print(f"2. 使用AutoCAD或其他CAD软件打开")
                print(f"3. 另存为DXF格式")
                print(f"4. 重新上传DXF文件")
                
                return {
                    'success': False,
                    'error': conversion_result.get('error', 'Conversion failed'),
                    'suggestion': conversion_result.get('suggestion', ''),
                    'layout_info': layout_info
                }
                
        except Exception as e:
            return {'error': str(e)}
        finally:
            conn.close()
    
    def cleanup(self):
        """清理临时文件"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"临时目录已清理: {self.temp_dir}")
        except Exception as e:
            print(f"清理临时文件失败: {e}")

def main():
    """主函数"""
    # 数据库配置
    db_config = {
        'host': "dbconn.sealoshzh.site",
        'port': 48982,
        'database': "postgres",
        'user': "postgres",
        'password': "2xn59xgm"
    }
    
    # 创建转换器
    converter = DWGConverter(db_config)
    
    try:
        # 处理图纸46
        result = converter.process_drawing_file(46)
        
        print(f"\n" + "=" * 80)
        print(f"处理结果:")
        print(f"=" * 80)
        
        if result.get('success'):
            print("✅ 处理成功")
            if 'conversion_result' in result:
                conv_result = result['conversion_result']
                print(f"转换生成的文件数: {conv_result.get('count', 0)}")
                print(f"文件列表: {conv_result.get('dxf_files', [])}")
        else:
            print("❌ 处理失败")
            print(f"错误: {result.get('error', 'Unknown error')}")
            if 'suggestion' in result and result['suggestion']:
                print(f"建议: {result['suggestion']}")
        
    except Exception as e:
        print(f"程序执行错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        converter.cleanup()

if __name__ == "__main__":
    main() 