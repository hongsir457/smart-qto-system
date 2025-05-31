import os
import sys
from pathlib import Path
from app.core.celery_app import celery_app

def setup_python_path():
    """设置Python路径以确保可以正确导入模块"""
    # 获取当前文件所在目录的父目录（项目根目录）
    current_dir = Path(__file__).resolve().parent
    
    # 将项目根目录添加到Python路径
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # 打印当前Python路径以便调试
    print("Python path:", sys.path)
    
    # 打印当前工作目录
    print("Working directory:", os.getcwd())

def init_windows_env():
    """初始化Windows特定的环境设置"""
    if os.name == 'nt':
        os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

def main():
    """主函数"""
    # 设置Python路径
    setup_python_path()
    
    # 初始化Windows环境
    init_windows_env()
    
    try:
        # 尝试导入celery_app
        print("Successfully imported celery_app")
        
        # 设置Celery Worker参数
        argv = [
            'worker',
            '--loglevel=INFO',
            '--pool=solo',
            '--max-tasks-per-child=10',
            '--broker-connection-retry',
            '--broker-connection-max-retries=10'
        ]
        
        # 启动Celery Worker
        celery_app.worker_main(argv)
        
    except ImportError as e:
        print(f"Error importing celery_app: {e}")
        print("Current directory structure:")
        for root, dirs, files in os.walk(current_dir):
            print(f"\nDirectory: {root}")
            print("Files:", files)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

# 导出celery应用实例
celery = celery_app

if __name__ == '__main__':
    main() 