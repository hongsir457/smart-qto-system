"""
构件检测器单元测试
"""

import pytest
import numpy as np
import cv2
from unittest.mock import Mock, patch
import torch

from app.services.drawing_processing.component_detector import ComponentDetector


class TestComponentDetector:
    """构件检测器测试类"""
    
    def test_init(self):
        """测试初始化"""
        detector = ComponentDetector()
        
        assert detector.confidence_threshold == 0.25
        assert detector.iou_threshold == 0.45
        assert len(detector.component_types) > 0
        assert "柱" in detector.component_types.values()
    
    def test_get_device(self):
        """测试设备选择"""
        detector = ComponentDetector()
        device = detector._get_device()
        
        assert device in ["cuda", "mps", "cpu"]
    
    @patch('app.services.drawing_processing.component_detector.YOLO')
    def test_load_model_success(self, mock_yolo):
        """测试成功加载模型"""
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        detector = ComponentDetector()
        with patch.object(detector, 'model_path', "test_model.pt"):
            with patch('os.path.exists', return_value=True):
                result = detector._load_model()
        
        assert result is True
        assert detector.model == mock_model
    
    def test_load_model_file_not_exists(self):
        """测试模型文件不存在"""
        detector = ComponentDetector()
        with patch.object(detector, 'model_path', "nonexistent.pt"):
            result = detector._load_model()
        
        assert result is False
        assert detector.model is None
    
    def test_is_model_loaded(self):
        """测试模型是否加载检查"""
        detector = ComponentDetector()
        
        # 未加载模型
        detector.model = None
        assert detector.is_model_loaded() is False
        
        # 已加载模型
        detector.model = Mock()
        assert detector.is_model_loaded() is True
    
    def test_preprocess_image(self):
        """测试图像预处理"""
        detector = ComponentDetector()
        
        # 创建测试图像
        test_image = np.zeros((100, 150, 3), dtype=np.uint8)
        
        processed = detector._preprocess_image(test_image)
        
        assert processed is not None
        assert len(processed.shape) == 3
        assert processed.shape[2] == 3
    
    def test_preprocess_large_image(self):
        """测试大图像预处理"""
        detector = ComponentDetector()
        
        # 创建大图像
        large_image = np.zeros((2000, 3000, 3), dtype=np.uint8)
        
        processed = detector._preprocess_image(large_image)
        
        assert processed is not None
        assert max(processed.shape[:2]) <= 1280
    
    def test_detect_components_no_model(self):
        """测试未加载模型时的检测"""
        detector = ComponentDetector()
        detector.model = None
        
        test_image = np.zeros((100, 150, 3), dtype=np.uint8)
        result = detector.detect_components(test_image)
        
        assert "error" in result
        assert result["detections"] == []
        assert result["summary"] == {}
    
    @patch('app.services.drawing_processing.component_detector.YOLO')
    def test_detect_components_success(self, mock_yolo):
        """测试成功检测构件"""
        # 创建模拟模型和结果
        mock_model = Mock()
        mock_result = Mock()
        mock_boxes = Mock()
        
        # 模拟检测结果
        mock_boxes.xyxy = [torch.tensor([[10.0, 10.0, 50.0, 50.0]])]
        mock_boxes.conf = [torch.tensor([0.8])]
        mock_boxes.cls = [torch.tensor([0])]
        
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]
        mock_yolo.return_value = mock_model
        
        detector = ComponentDetector()
        with patch.object(detector, 'model_path', "test.pt"):
            with patch('os.path.exists', return_value=True):
                detector._load_model()
        
        test_image = np.zeros((100, 150, 3), dtype=np.uint8)
        result = detector.detect_components(test_image)
        
        assert "error" not in result
        assert len(result["detections"]) > 0
        assert "summary" in result
        assert result["total_count"] > 0
    
    def test_parse_results_empty(self):
        """测试解析空结果"""
        detector = ComponentDetector()
        
        empty_results = []
        image_shape = (100, 150, 3)
        
        detections = detector._parse_results(empty_results, image_shape)
        
        assert detections == []
    
    def test_generate_summary_empty(self):
        """测试生成空摘要"""
        detector = ComponentDetector()
        
        summary = detector._generate_summary([])
        
        assert summary["total_count"] == 0
        assert summary["by_type"] == {}
        assert summary["confidence_stats"]["min"] == 0.0
    
    def test_generate_summary_with_detections(self):
        """测试生成包含检测结果的摘要"""
        detector = ComponentDetector()
        
        detections = [
            {
                "class_name": "柱",
                "confidence": 0.8
            },
            {
                "class_name": "梁",
                "confidence": 0.9
            },
            {
                "class_name": "柱",
                "confidence": 0.7
            }
        ]
        
        summary = detector._generate_summary(detections)
        
        assert summary["total_count"] == 3
        assert summary["by_type"]["柱"] == 2
        assert summary["by_type"]["梁"] == 1
        assert summary["confidence_stats"]["min"] == 0.7
        assert summary["confidence_stats"]["max"] == 0.9
    
    def test_detect_from_file_not_exists(self):
        """测试检测不存在的文件"""
        detector = ComponentDetector()
        
        result = detector.detect_from_file("nonexistent.jpg")
        
        assert "error" in result
        assert "文件不存在" in result["error"]
    
    @patch('cv2.imread')
    def test_detect_from_file_invalid_image(self, mock_imread):
        """测试检测无效图像文件"""
        mock_imread.return_value = None
        
        detector = ComponentDetector()
        
        with patch('os.path.exists', return_value=True):
            result = detector.detect_from_file("invalid.jpg")
        
        assert "error" in result
        assert "无法读取" in result["error"]
    
    def test_set_confidence_threshold(self):
        """测试设置置信度阈值"""
        detector = ComponentDetector()
        
        # 正常值
        detector.set_confidence_threshold(0.6)
        assert detector.confidence_threshold == 0.6
        
        # 边界值
        detector.set_confidence_threshold(-0.1)
        assert detector.confidence_threshold == 0.0
        
        detector.set_confidence_threshold(1.1)
        assert detector.confidence_threshold == 1.0
    
    def test_set_iou_threshold(self):
        """测试设置IoU阈值"""
        detector = ComponentDetector()
        
        # 正常值
        detector.set_iou_threshold(0.5)
        assert detector.iou_threshold == 0.5
        
        # 边界值
        detector.set_iou_threshold(-0.1)
        assert detector.iou_threshold == 0.0
        
        detector.set_iou_threshold(1.1)
        assert detector.iou_threshold == 1.0
    
    def test_get_model_info(self):
        """测试获取模型信息"""
        detector = ComponentDetector()
        
        info = detector.get_model_info()
        
        assert "model_path" in info
        assert "device" in info
        assert "is_loaded" in info
        assert "confidence_threshold" in info
        assert "iou_threshold" in info
        assert "component_types" in info
    
    def test_filter_components_by_confidence(self):
        """测试按置信度过滤构件"""
        detector = ComponentDetector()
        
        components = {
            "柱": [
                {"confidence": 0.8},
                {"confidence": 0.4},
                {"confidence": 0.6}
            ],
            "梁": [
                {"confidence": 0.3},
                {"confidence": 0.7}
            ]
        }
        
        filtered = detector.filter_components_by_confidence(components, 0.5)
        
        assert len(filtered["柱"]) == 2
        assert len(filtered["梁"]) == 1
        assert all(comp["confidence"] >= 0.5 for comp_list in filtered.values() for comp in comp_list)
    
    def test_group_components_by_area(self):
        """测试按面积分组构件"""
        detector = ComponentDetector()
        
        components = {
            "柱": [
                {"area": 100},
                {"area": 200},
                {"area": 300},
                {"area": 500}
            ]
        }
        
        grouped = detector.group_components_by_area(components)
        
        assert "柱" in grouped
        assert "small" in grouped["柱"]
        assert "medium" in grouped["柱"]
        assert "large" in grouped["柱"]
        assert "all" in grouped["柱"]
    
    def test_calculate_detection_statistics(self):
        """测试计算检测统计信息"""
        detector = ComponentDetector()
        
        components = {
            "柱": [
                {"confidence": 0.8, "area": 100},
                {"confidence": 0.9, "area": 150}
            ],
            "梁": [
                {"confidence": 0.7, "area": 200}
            ]
        }
        
        stats = detector.calculate_detection_statistics(components)
        
        assert stats["total_components"] == 3
        assert stats["class_counts"]["柱"] == 2
        assert stats["class_counts"]["梁"] == 1
        assert "confidence_stats" in stats
        assert "area_stats" in stats
        assert "overall_confidence" in stats
        assert "overall_area" in stats 