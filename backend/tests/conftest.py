"""
pytest配置文件
定义通用的测试fixtures和配置
"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock

# 测试数据库配置
@pytest.fixture
def test_db():
    """创建测试数据库"""
    from app.database import engine, Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # 创建内存数据库
    test_engine = create_engine("sqlite:///test.db", echo=False)
    Base.metadata.create_all(test_engine)
    
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # 清理测试数据库
        if os.path.exists("test.db"):
            os.remove("test.db")

@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def sample_image():
    """创建测试图像"""
    import numpy as np
    import cv2
    
    # 创建一个简单的测试图像
    image = np.zeros((400, 600, 3), dtype=np.uint8)
    # 添加一些几何形状
    cv2.rectangle(image, (50, 50), (250, 150), (255, 255, 255), 2)
    cv2.rectangle(image, (350, 200), (550, 350), (255, 255, 255), 2)
    cv2.putText(image, "Test Drawing", (100, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return image

@pytest.fixture
def sample_pdf(temp_dir):
    """创建测试PDF文件"""
    import fitz  # PyMuPDF
    
    pdf_path = os.path.join(temp_dir, "test.pdf")
    doc = fitz.open()
    page = doc.new_page()
    
    # 添加文本和图形
    page.insert_text((50, 50), "测试图纸", fontsize=20)
    page.draw_rect(fitz.Rect(100, 100, 300, 200))
    page.draw_rect(fitz.Rect(350, 150, 500, 300))
    
    doc.save(pdf_path)
    doc.close()
    
    return pdf_path

@pytest.fixture
def sample_dwg(temp_dir):
    """创建测试DXF文件（模拟DWG）"""
    import ezdxf
    
    dxf_path = os.path.join(temp_dir, "test.dxf")
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # 添加一些实体
    msp.add_line((0, 0), (100, 0))
    msp.add_line((100, 0), (100, 100))
    msp.add_line((100, 100), (0, 100))
    msp.add_line((0, 100), (0, 0))
    
    msp.add_text("测试图框", dxfattribs={'height': 5}).set_pos((10, 10))
    
    doc.saveas(dxf_path)
    return dxf_path

@pytest.fixture
def mock_yolo_model():
    """模拟YOLO模型"""
    mock_model = Mock()
    mock_results = Mock()
    mock_boxes = Mock()
    
    # 模拟检测结果
    mock_boxes.xyxy = [[[10, 10, 50, 50], [60, 60, 100, 100]]]
    mock_boxes.conf = [[0.8, 0.9]]
    mock_boxes.cls = [[0, 1]]
    
    mock_results.boxes = mock_boxes
    mock_model.return_value = [mock_results]
    
    return mock_model

@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    from unittest.mock import Mock
    
    mock_redis = Mock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    
    return mock_redis

@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "is_active": True
    }

@pytest.fixture
def test_drawing_data():
    """测试图纸数据"""
    return {
        "filename": "test_drawing.pdf",
        "file_type": "pdf",
        "file_size": 1024000,
        "description": "测试图纸",
        "status": "uploaded"
    }

# 测试配置
@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URL": "sqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/1",
        "SECRET_KEY": "test-secret-key",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30
    }

# 异步测试支持
@pytest.fixture
def event_loop():
    """创建事件循环"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# API测试客户端
@pytest.fixture
def test_client():
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    with TestClient(app) as client:
        yield client

# 清理函数
def pytest_configure(config):
    """pytest配置"""
    # 创建测试目录
    test_dirs = ["test_files", "test_output", "temp"]
    for dir_name in test_dirs:
        os.makedirs(f"tests/{dir_name}", exist_ok=True)

def pytest_unconfigure(config):
    """pytest清理"""
    # 清理测试文件
    test_files = ["test.db", "test.log"]
    for file_name in test_files:
        if os.path.exists(file_name):
            os.remove(file_name) 