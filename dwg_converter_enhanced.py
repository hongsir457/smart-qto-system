#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版DWG文件检测和转换工具
支持在线转换服务和本地处理
"""

import os
import psycopg2
import requests
import tempfile
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

class EnhancedDWGConverter:
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
    
    def analyze_dwg_file(self, dwg_file_path):
        """分析DWG文件特征"""
        try:
            file_size = os.path.getsize(dwg_file_path)
            
            # 读取文件头信息
            with open(dwg_file_path, 'rb') as f:
                header = f.read(128)
            
            # 简单的DWG版本检测
            dwg_version = "Unknown"
            if header.startswith(b'AC1032'):
                dwg_version = "AutoCAD 2018/2019/2020/2021"
            elif header.startswith(b'AC1027'):
                dwg_version = "AutoCAD 2013/2014/2015/2016/2017"
            elif header.startswith(b'AC1024'):
                dwg_version = "AutoCAD 2010/2011/2012"
            elif header.startswith(b'AC1021'):
                dwg_version = "AutoCAD 2007/2008/2009"
            elif header.startswith(b'AC1018'):
                dwg_version = "AutoCAD 2004/2005/2006"
            elif header.startswith(b'AC1015'):
                dwg_version = "AutoCAD 2000/2000i/2002"
            
            # 基于文件大小估算复杂度和可能的图纸数
            if file_size < 1024 * 1024:  # < 1MB
                complexity = "简单"
                estimated_sheets = 1
            elif file_size < 5 * 1024 * 1024:  # < 5MB
                complexity = "中等"
                estimated_sheets = 1
            elif file_size < 20 * 1024 * 1024:  # < 20MB
                complexity = "复杂"
                estimated_sheets = 2
            else:  # >= 20MB
                complexity = "非常复杂"
                estimated_sheets = max(1, file_size // (10 * 1024 * 1024))
            
            return {
                'file_size_mb': file_size / (1024 * 1024),
                'dwg_version': dwg_version,
                'complexity': complexity,
                'estimated_sheets': int(estimated_sheets),
                'header_info': header[:32].hex(),
                'analysis_method': 'header_analysis'
            }
            
        except Exception as e:
            print(f"DWG文件分析失败: {e}")
            return {
                'file_size_mb': 0,
                'dwg_version': "Unknown",
                'complexity': "Unknown",
                'estimated_sheets': 1,
                'analysis_method': 'fallback'
            }
    
    def convert_with_cloudconvert_api(self, dwg_path, output_dir):
        """使用CloudConvert API转换DWG到DXF"""
        try:
            print("尝试使用CloudConvert API转换...")
            # 注意：这需要API密钥，这里提供框架
            
            # 实际使用时需要注册CloudConvert账户获取API密钥
            api_key = "YOUR_CLOUDCONVERT_API_KEY"
            
            if api_key == "YOUR_CLOUDCONVERT_API_KEY":
                return {
                    'success': False,
                    'error': 'CloudConvert API key not configured',
                    'suggestion': 'Configure CloudConvert API key for online conversion'
                }
            
            # CloudConvert API调用示例
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 这里应该实现完整的CloudConvert API调用
            # 由于需要API密钥，这里返回模拟结果
            
            return {
                'success': False,
                'error': 'CloudConvert API not implemented',
                'suggestion': 'Use local conversion tools or manual conversion'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def convert_with_local_tools(self, dwg_path, output_dir):
        """使用本地工具转换DWG"""
        try:
            print("尝试本地工具转换...")
            
            # 尝试使用FreeCAD命令行转换
            freecad_paths = [
                r"C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe",
                r"C:\Program Files (x86)\FreeCAD 0.21\bin\FreeCAD.exe",
                "freecad"
            ]
            
            for freecad_path in freecad_paths:
                if os.path.exists(freecad_path) or freecad_path == "freecad":
                    try:
                        output_file = os.path.join(output_dir, 
                                                 Path(dwg_path).stem + ".dxf")
                        
                        # FreeCAD命令行转换脚本
                        conversion_script = f"""
import sys
sys.path.append(r'C:\\Program Files\\FreeCAD 0.21\\lib')
import FreeCAD
import Import

doc = FreeCAD.newDocument()
Import.insert(r'{dwg_path}', doc.Name)
Import.export(doc.Objects, r'{output_file}')
FreeCAD.closeDocument(doc.Name)
"""
                        
                        script_path = os.path.join(self.temp_dir, "convert.py")
                        with open(script_path, 'w', encoding='utf-8') as f:
                            f.write(conversion_script)
                        
                        # 这里提供框架，实际执行可能需要调整
                        print(f"FreeCAD转换脚本已准备: {script_path}")
                        
                        return {
                            'success': False,
                            'error': 'FreeCAD conversion requires manual setup',
                            'script_path': script_path,
                            'suggestion': 'Run the conversion script manually with FreeCAD'
                        }
                        
                    except Exception as e:
                        print(f"FreeCAD转换失败: {e}")
                        continue
            
            return {
                'success': False,
                'error': 'No local conversion tools available'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def suggest_conversion_solutions(self, dwg_path, analysis_result):
        """提供转换解决方案建议"""
        solutions = []
        
        file_size_mb = analysis_result.get('file_size_mb', 0)
        complexity = analysis_result.get('complexity', 'Unknown')
        
        solutions.append({
            'method': 'manual_autocad',
            'priority': 1,
            'description': '使用AutoCAD手动转换',
            'steps': [
                '1. 使用AutoCAD打开DWG文件',
                '2. 选择 "另存为" -> "AutoCAD DXF"',
                '3. 选择适当的DXF版本（推荐R2018）',
                '4. 保存并重新上传DXF文件'
            ],
            'pros': ['质量最高', '兼容性最好', '保留所有信息'],
            'cons': ['需要AutoCAD软件', '手动操作']
        })
        
        if file_size_mb < 50:  # 小于50MB的文件适合在线转换
            solutions.append({
                'method': 'online_converter',
                'priority': 2,
                'description': '使用在线转换工具',
                'tools': [
                    'https://convertio.co/dwg-dxf/',
                    'https://www.zamzar.com/convert/dwg-to-dxf/',
                    'https://cloudconvert.com/dwg-to-dxf'
                ],
                'steps': [
                    '1. 访问在线转换网站',
                    '2. 上传DWG文件',
                    '3. 选择DXF作为输出格式',
                    '4. 下载转换后的文件'
                ],
                'pros': ['免费', '无需软件', '快速'],
                'cons': ['文件大小限制', '安全性考虑', '需要网络']
            })
        
        solutions.append({
            'method': 'freecad',
            'priority': 3,
            'description': '使用FreeCAD（免费CAD软件）',
            'steps': [
                '1. 下载安装FreeCAD (https://www.freecadweb.org/)',
                '2. 打开FreeCAD',
                '3. File -> Import -> 选择DWG文件',
                '4. File -> Export -> 选择DXF格式'
            ],
            'pros': ['免费软件', '开源', '功能较全'],
            'cons': ['转换质量可能不如AutoCAD', '学习成本']
        })
        
        solutions.append({
            'method': 'librecad',
            'priority': 4,
            'description': '使用LibreCAD',
            'steps': [
                '1. 下载安装LibreCAD (https://librecad.org/)',
                '2. 尝试打开DWG文件（支持有限）',
                '3. 另存为DXF格式'
            ],
            'pros': ['免费', '轻量级'],
            'cons': ['DWG支持有限', '可能无法打开复杂文件']
        })
        
        if complexity in ['非常复杂'] or file_size_mb > 100:
            solutions.insert(0, {
                'method': 'professional_service',
                'priority': 0,
                'description': '专业转换服务',
                'note': f'文件较大({file_size_mb:.1f}MB)且复杂，建议使用专业服务',
                'options': [
                    '联系CAD专业人员协助转换',
                    '使用企业级转换工具',
                    '考虑将文件分解为多个较小的部分'
                ]
            })
        
        return solutions
    
    def create_conversion_report(self, drawing_info, analysis_result, solutions):
        """创建转换报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'drawing_info': drawing_info,
            'analysis_result': analysis_result,
            'conversion_solutions': solutions,
            'summary': {
                'file_type': 'AutoCAD DWG',
                'conversion_needed': True,
                'recommended_method': solutions[0]['method'] if solutions else 'manual',
                'estimated_difficulty': analysis_result.get('complexity', 'Unknown')
            }
        }
        
        # 保存报告到文件
        report_file = os.path.join(self.temp_dir, f"conversion_report_{drawing_info['id']}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report, report_file
    
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
            drawing_info = {
                'id': drawing_id,
                'filename': filename,
                'file_url': file_url,
                'status': status
            }
            
            print(f"=" * 80)
            print(f"增强版DWG文件分析报告")
            print(f"图纸 {drawing_id}: {filename}")
            print(f"=" * 80)
            
            # 检测文件类型
            file_info = self.detect_file_type(filename)
            print(f"📁 文件类型检测:")
            print(f"  扩展名: {file_info['extension']}")
            print(f"  类型: {file_info['type']}")
            print(f"  是否CAD文件: {file_info['is_cad']}")
            print(f"  是否需要转换: {file_info['needs_conversion']}")
            print()
            
            if not file_info['needs_conversion']:
                print(f"✅ 文件无需转换，类型: {file_info['type']}")
                return {
                    'success': True,
                    'message': 'No conversion needed',
                    'file_type': file_info['type']
                }
            
            # 下载DWG文件
            local_dwg_path = os.path.join(self.temp_dir, filename)
            if not self.download_file(file_url, local_dwg_path):
                return {'error': 'Failed to download file'}
            
            # 分析DWG文件
            analysis_result = self.analyze_dwg_file(local_dwg_path)
            print(f"🔍 DWG文件分析:")
            print(f"  文件大小: {analysis_result['file_size_mb']:.2f} MB")
            print(f"  DWG版本: {analysis_result['dwg_version']}")
            print(f"  复杂度: {analysis_result['complexity']}")
            print(f"  估算图纸数: {analysis_result['estimated_sheets']}")
            print(f"  分析方法: {analysis_result['analysis_method']}")
            print()
            
            # 获取转换解决方案
            solutions = self.suggest_conversion_solutions(local_dwg_path, analysis_result)
            
            print(f"💡 推荐转换解决方案:")
            print(f"-" * 50)
            for i, solution in enumerate(solutions, 1):
                print(f"{i}. {solution['description']} (优先级: {solution.get('priority', 'N/A')})")
                if 'steps' in solution:
                    for step in solution['steps']:
                        print(f"   {step}")
                if 'pros' in solution:
                    print(f"   优点: {', '.join(solution['pros'])}")
                if 'cons' in solution:
                    print(f"   缺点: {', '.join(solution['cons'])}")
                if 'tools' in solution:
                    print(f"   工具: {', '.join(solution['tools'])}")
                print()
            
            # 创建详细报告
            report, report_file = self.create_conversion_report(
                drawing_info, analysis_result, solutions)
            
            print(f"📋 详细报告已生成: {report_file}")
            
            return {
                'success': True,
                'analysis_result': analysis_result,
                'solutions': solutions,
                'report_file': report_file,
                'temp_dir': self.temp_dir,
                'file_downloaded': local_dwg_path
            }
                
        except Exception as e:
            return {'error': str(e)}
        finally:
            conn.close()
    
    def cleanup(self, keep_report=True):
        """清理临时文件"""
        try:
            if keep_report:
                # 保留报告文件，只删除其他临时文件
                import shutil
                for item in os.listdir(self.temp_dir):
                    item_path = os.path.join(self.temp_dir, item)
                    if not item.endswith('.json'):  # 保留JSON报告
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                print(f"临时文件已清理，报告保留在: {self.temp_dir}")
            else:
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                print(f"所有临时文件已清理")
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
    
    # 创建增强版转换器
    converter = EnhancedDWGConverter(db_config)
    
    try:
        # 处理图纸46
        result = converter.process_drawing_file(46)
        
        print(f"\n" + "=" * 80)
        print(f"处理结果总结:")
        print(f"=" * 80)
        
        if result.get('success'):
            print("✅ 分析完成")
            analysis = result.get('analysis_result', {})
            solutions = result.get('solutions', [])
            
            print(f"文件信息:")
            print(f"  大小: {analysis.get('file_size_mb', 0):.2f} MB")
            print(f"  复杂度: {analysis.get('complexity', 'Unknown')}")
            print(f"  版本: {analysis.get('dwg_version', 'Unknown')}")
            
            print(f"\n推荐方案: {solutions[0]['description'] if solutions else '无'}")
            
            if 'report_file' in result:
                print(f"详细报告: {result['report_file']}")
                
        else:
            print("❌ 处理失败")
            print(f"错误: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"程序执行错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源（保留报告）
        converter.cleanup(keep_report=True)

if __name__ == "__main__":
    main() 