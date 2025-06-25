"""
测试包

包含系统的各种测试模块：
- 单元测试
- 集成测试  
- 性能测试
- API测试
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 测试配置
TEST_CONFIG = {
    "database_url": "sqlite:///test.db",
    "redis_url": "redis://localhost:6379/1",
    "test_files_dir": os.path.join(os.path.dirname(__file__), "test_files"),
    "output_dir": os.path.join(os.path.dirname(__file__), "test_output")
}

# 创建测试输出目录
os.makedirs(TEST_CONFIG["output_dir"], exist_ok=True) 