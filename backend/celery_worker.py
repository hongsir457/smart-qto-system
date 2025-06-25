import os
import sys
import signal
import threading
import time
from pathlib import Path
from app.core.celery_app import celery_app

# 全局标志用于优雅关闭
shutdown_flag = threading.Event()

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
        # Windows下使用solo pool以避免多进程问题
        os.environ.setdefault('CELERY_POOL', 'solo')

def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭"""
    print(f"\n🛑 接收到信号 {signum}，准备关闭Celery Worker...")
    shutdown_flag.set()
    
    # 给worker一些时间完成当前任务
    print("⏳ 等待当前任务完成...")
    time.sleep(2)
    
    try:
        if hasattr(celery_app, 'control'):
            print("📤 发送关闭指令到worker...")
            celery_app.control.shutdown(destination=['celery@localhost'])
    except Exception as e:
        print(f"⚠️  发送关闭指令失败: {e}")
    
    print("✅ Celery Worker已关闭")
    sys.exit(0)

def setup_signal_handlers():
    """设置信号处理器"""
    try:
        # 处理常见的终止信号
        signal.signal(signal.SIGINT, signal_handler)    # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)   # 终止信号
        
        if os.name == 'nt':  # Windows
            # Windows下Ctrl+Break的处理
            signal.signal(signal.SIGBREAK, signal_handler)
            print("💡 Windows系统下，建议使用 Ctrl+Break 或关闭窗口来停止worker")
        
        print("✅ 信号处理器已设置")
        
    except Exception as e:
        print(f"⚠️  设置信号处理器失败: {e}")

def monitor_shutdown():
    """监控关闭标志的线程"""
    while not shutdown_flag.is_set():
        time.sleep(1)
    
    print("🔄 监控线程检测到关闭信号，正在关闭...")
    try:
        if hasattr(celery_app, 'control'):
            celery_app.control.shutdown(destination=['celery@localhost'])
    except:
        pass
    os._exit(0)

def main():
    """主函数"""
    # 设置Python路径
    setup_python_path()
    
    # 初始化Windows环境
    init_windows_env()
    
    # 设置信号处理器
    setup_signal_handlers()
    
    # 启动监控线程
    monitor_thread = threading.Thread(target=monitor_shutdown, daemon=True)
    monitor_thread.start()
    
    try:
        # 尝试导入celery_app
        print("Successfully imported celery_app")
        
        # 设置Celery Worker参数
        argv = [
            'worker',
            '--loglevel=INFO',
            '--pool=solo',                    # Windows下使用solo pool
            '--concurrency=1',                # 单进程
            '--max-tasks-per-child=10',       # 限制每个子进程的任务数
            '--broker-connection-retry',      # 启用连接重试
            '--broker-connection-max-retries=10',
            '--worker-disable-rate-limits',   # 禁用速率限制
            '--without-heartbeat',            # 禁用心跳（Windows下可能有问题）
            '--without-gossip',               # 禁用gossip
            '--without-mingle'                # 禁用mingle
        ]
        
        print("🚀 启动Celery Worker...")
        print("💡 提示: 使用 Ctrl+Break 或运行 stop_celery.ps1 来停止")
        
        # 启动Celery Worker
        celery_app.worker_main(argv)
        
    except ImportError as e:
        print(f"Error importing celery_app: {e}")
        print("Current directory structure:")
        for root, dirs, files in os.walk(current_dir):
            print(f"\nDirectory: {root}")
            print("Files:", files)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 接收到键盘中断信号")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

# 导出celery应用实例
celery = celery_app

if __name__ == '__main__':
    main() 