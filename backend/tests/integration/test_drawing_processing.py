"""
图纸处理集成测试
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
import numpy as np

from app.services.drawing_processing.drawing_task_executor import DrawingTaskExecutor
from app.models.drawing import Drawing


class TestDrawingProcessingIntegration:
    """图纸处理集成测试类"""
    
    @pytest.fixture
    def drawing_executor(self):
        """创建图纸任务执行器"""
        return DrawingTaskExecutor()
    
    @pytest.fixture
    def mock_drawing(self, test_drawing_data):
        """创建模拟图纸对象"""
        drawing = Mock(spec=Drawing)
        drawing.id = 1
        drawing.filename = test_drawing_data["filename"]
        drawing.file_type = test_drawing_data["file_type"]
        drawing.file_path = "test_path.pdf"
        drawing.status = "uploaded"
        return drawing
    
    def test_execute_drawing_task_pdf(self, drawing_executor, mock_drawing, temp_dir):
        """测试PDF图纸处理任务"""
        # 创建测试PDF文件
        import fitz
        pdf_path = os.path.join(temp_dir, "test.pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "测试文档", fontsize=20)
        doc.save(pdf_path)
        doc.close()
        
        mock_drawing.file_path = pdf_path
        mock_drawing.file_type = "pdf"
        
        # Mock任务管理器
        with patch.object(drawing_executor.task_manager, 'execute_with_retry') as mock_retry:
            mock_retry.return_value = {"status": "success"}
            
            result = drawing_executor.execute_drawing_task(1, "test_task_id")
            
            mock_retry.assert_called_once()
            assert result["status"] == "success"
    
    @patch('app.services.drawing_processing.drawing_task_executor.DWGProcessor')
    def test_execute_drawing_task_dwg(self, mock_dwg_processor, drawing_executor, mock_drawing):
        """测试DWG图纸处理任务"""
        mock_drawing.file_type = "dwg"
        
        # Mock DWG处理器
        mock_processor_instance = Mock()
        mock_processor_instance.process_multi_sheets.return_value = {
            "drawings": [
                {
                    "drawing_number": "A001",
                    "components": [{"type": "wall", "count": 5}],
                    "texts": ["墙体", "标注"]
                }
            ]
        }
        mock_dwg_processor.return_value = mock_processor_instance
        
        with patch.object(drawing_executor.task_manager, 'execute_with_retry') as mock_retry:
            mock_retry.return_value = {"status": "success"}
            
            result = drawing_executor.execute_drawing_task(1, "test_task_id")
            
            mock_retry.assert_called_once()
    
    def test_process_pdf_file(self, drawing_executor, temp_dir):
        """测试PDF文件处理"""
        # 创建测试PDF
        import fitz
        pdf_path = os.path.join(temp_dir, "test.pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "测试内容", fontsize=12)
        page.draw_rect(fitz.Rect(100, 100, 200, 200))
        doc.save(pdf_path)
        doc.close()
        
        # Mock文件处理器
        with patch.object(drawing_executor.file_processor, 'process_pdf_file') as mock_process:
            mock_process.return_value = {
                "status": "success",
                "images": [os.path.join(temp_dir, "page_1.png")]
            }
            
            # Mock OCR和构件检测
            with patch.object(drawing_executor.ocr_engine, 'extract_text') as mock_ocr:
                mock_ocr.return_value = {"text": "测试文本内容"}
                
                with patch.object(drawing_executor.component_detector, 'detect_components') as mock_detect:
                    mock_detect.return_value = {
                        "components": {
                            "wall": [{"bbox": [10, 10, 50, 50], "confidence": 0.8}]
                        }
                    }
                    
                    result = drawing_executor._process_pdf_file(pdf_path, "test_task")
                    
                    assert "components" in result
                    assert "ocr_text" in result
                    assert "wall" in result["components"]
    
    def test_process_image_file(self, drawing_executor, temp_dir):
        """测试图像文件处理"""
        # 创建测试图像
        import cv2
        image_path = os.path.join(temp_dir, "test.jpg")
        test_image = np.zeros((400, 600, 3), dtype=np.uint8)
        cv2.rectangle(test_image, (50, 50), (250, 150), (255, 255, 255), 2)
        cv2.imwrite(image_path, test_image)
        
        # Mock文件处理器
        with patch.object(drawing_executor.file_processor, 'process_image_file') as mock_process:
            mock_process.return_value = {
                "status": "success",
                "metadata": {"width": 600, "height": 400}
            }
            
            # Mock OCR和构件检测
            with patch.object(drawing_executor.ocr_engine, 'extract_text') as mock_ocr:
                mock_ocr.return_value = {"text": "图像中的文本"}
                
                with patch.object(drawing_executor.component_detector, 'detect_components') as mock_detect:
                    mock_detect.return_value = {
                        "components": {
                            "column": [{"bbox": [100, 100, 150, 200], "confidence": 0.9}]
                        }
                    }
                    
                    result = drawing_executor._process_image_file(image_path, "test_task")
                    
                    assert "components" in result
                    assert "ocr_text" in result
                    assert "metadata" in result
                    assert result["ocr_text"] == "图像中的文本"
    
    def test_execute_ocr_task(self, drawing_executor, mock_drawing):
        """测试纯OCR任务"""
        # Mock文件处理器和OCR引擎
        with patch.object(drawing_executor.file_processor, 'ensure_local_file') as mock_ensure:
            mock_ensure.return_value = "local_file_path"
            
            with patch.object(drawing_executor.ocr_engine, 'extract_text') as mock_ocr:
                mock_ocr.return_value = {"text": "OCR识别的文本内容"}
                
                with patch.object(drawing_executor.task_manager, 'execute_with_retry') as mock_retry:
                    mock_retry.return_value = {"ocr_only": True, "text": "OCR识别的文本内容"}
                    
                    result = drawing_executor.execute_ocr_task(1, "ocr_task_id")
                    
                    assert result["ocr_only"] is True
                    assert "text" in result
    
    def test_process_by_file_type_pdf(self, drawing_executor):
        """测试根据文件类型处理PDF"""
        with patch.object(drawing_executor, '_process_pdf_file') as mock_process:
            mock_process.return_value = {"components": {}, "ocr_text": "PDF内容"}
            
            result = drawing_executor._process_by_file_type("test.pdf", "pdf", "task_id")
            
            mock_process.assert_called_once()
            assert "components" in result
    
    def test_process_by_file_type_dwg(self, drawing_executor):
        """测试根据文件类型处理DWG"""
        with patch.object(drawing_executor, '_process_dwg_file') as mock_process:
            mock_process.return_value = {"components": {}, "ocr_text": "DWG内容"}
            
            result = drawing_executor._process_by_file_type("test.dwg", "dwg", "task_id")
            
            mock_process.assert_called_once()
            assert "components" in result
    
    def test_process_by_file_type_image(self, drawing_executor):
        """测试根据文件类型处理图像"""
        with patch.object(drawing_executor, '_process_image_file') as mock_process:
            mock_process.return_value = {"components": {}, "ocr_text": "图像内容"}
            
            result = drawing_executor._process_by_file_type("test.jpg", "jpg", "task_id")
            
            mock_process.assert_called_once()
            assert "components" in result
    
    def test_process_by_file_type_error(self, drawing_executor):
        """测试文件类型处理错误"""
        with patch.object(drawing_executor, '_process_pdf_file') as mock_process:
            mock_process.side_effect = Exception("处理错误")
            
            result = drawing_executor._process_by_file_type("test.pdf", "pdf", "task_id")
            
            assert "error" in result
            assert "处理pdf文件失败" in result["error"]


class TestComponentIntegration:
    """构件相关集成测试"""
    
    def test_component_detection_pipeline(self, temp_dir):
        """测试构件检测流水线"""
        from app.services.drawing_processing.component_detector import ComponentDetector
        
        # 创建测试图像
        import cv2
        image_path = os.path.join(temp_dir, "test_component.jpg")
        test_image = np.zeros((500, 800, 3), dtype=np.uint8)
        
        # 绘制一些简单的形状作为构件
        cv2.rectangle(test_image, (100, 100), (200, 400), (255, 255, 255), 2)  # 柱子
        cv2.rectangle(test_image, (50, 50), (750, 80), (255, 255, 255), 2)     # 梁
        cv2.imwrite(image_path, test_image)
        
        detector = ComponentDetector()
        
        # Mock YOLO模型
        with patch.object(detector, 'model') as mock_model:
            mock_result = Mock()
            mock_boxes = Mock()
            
            # 模拟检测到2个构件
            import torch
            mock_boxes.xyxy = [torch.tensor([[100.0, 100.0, 200.0, 400.0], [50.0, 50.0, 750.0, 80.0]])]
            mock_boxes.conf = [torch.tensor([0.8, 0.9])]
            mock_boxes.cls = [torch.tensor([0, 1])]  # 柱和梁
            
            mock_result.boxes = mock_boxes
            mock_model.return_value = [mock_result]
            
            result = detector.detect_from_file(image_path)
            
            assert len(result["detections"]) == 2
            assert result["summary"]["total_count"] == 2


class TestTaskManagerIntegration:
    """任务管理器集成测试"""
    
    def test_task_execution_with_retry(self):
        """测试带重试的任务执行"""
        from app.services.drawing_processing.task_manager import TaskManager
        
        task_manager = TaskManager()
        
        # Mock数据库和图纸
        with patch('app.services.drawing_processing.task_manager.SafeDBSession') as mock_db:
            mock_session = Mock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            mock_drawing = Mock()
            mock_drawing.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_drawing
            
            # 定义测试函数
            def test_function(drawing, db, task_id):
                return {"result": "success", "drawing_id": drawing.id}
            
            result = task_manager.execute_with_retry(test_function, 1, "test_task")
            
            assert result["result"] == "success"
            assert result["drawing_id"] == 1
    
    def test_progress_tracking(self):
        """测试进度跟踪"""
        from app.services.drawing_processing.task_manager import TaskManager
        
        task_manager = TaskManager()
        
        # 测试同步进度推送
        with patch.object(task_manager, 'websocket_manager') as mock_ws:
            progress_data = {
                "stage": "processing",
                "progress": 50,
                "message": "处理中...",
                "task_id": "test_task"
            }
            
            task_manager.sync_push_progress("test_task", progress_data)
            
            # 验证WebSocket管理器被调用
            mock_ws.send_progress_update.assert_called_once() 