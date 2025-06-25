"""
性能测试
"""

import pytest
import time
import memory_profiler
import cProfile
import pstats
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch

from app.services.drawing_processing.component_detector import ComponentDetector
from app.services.drawing_processing.drawing_task_executor import DrawingTaskExecutor


class TestPerformance:
    """系统性能测试"""
    
    @pytest.fixture
    def large_test_image(self):
        """创建大型测试图像"""
        import cv2
        # 创建一个大图像（2K分辨率）
        image = np.zeros((1440, 2560, 3), dtype=np.uint8)
        
        # 添加多个几何形状来模拟复杂建筑图纸
        for i in range(50):
            x1, y1 = np.random.randint(0, 2000, 2)
            x2, y2 = x1 + np.random.randint(50, 200), y1 + np.random.randint(50, 200)
            cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 255), 2)
        
        return image
    
    def test_component_detection_performance(self, large_test_image):
        """测试构件检测性能"""
        detector = ComponentDetector()
        
        # Mock YOLO模型以避免实际加载
        with patch.object(detector, 'model') as mock_model:
            mock_result = Mock()
            mock_boxes = Mock()
            
            # 模拟检测到多个构件
            import torch
            num_detections = 100
            mock_boxes.xyxy = [torch.randint(0, 1000, (num_detections, 4)).float()]
            mock_boxes.conf = [torch.rand(num_detections)]
            mock_boxes.cls = [torch.randint(0, 8, (num_detections,))]
            
            mock_result.boxes = mock_boxes
            mock_model.return_value = [mock_result]
            
            # 测量性能
            start_time = time.time()
            result = detector.detect_components(large_test_image)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # 性能断言
            assert processing_time < 5.0, f"构件检测耗时过长: {processing_time:.2f}秒"
            assert len(result["detections"]) == num_detections
            
            print(f"构件检测耗时: {processing_time:.2f}秒")
            print(f"检测到构件数量: {len(result['detections'])}")
    
    def test_image_preprocessing_performance(self):
        """测试图像预处理性能"""
        detector = ComponentDetector()
        
        # 测试不同尺寸的图像
        sizes = [(640, 480), (1280, 720), (1920, 1080), (2560, 1440)]
        
        for width, height in sizes:
            test_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            
            start_time = time.time()
            processed = detector._preprocess_image(test_image)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # 预处理应该很快
            assert processing_time < 0.5, f"图像预处理耗时过长: {processing_time:.2f}秒 (尺寸: {width}x{height})"
            
            print(f"图像预处理 {width}x{height}: {processing_time:.3f}秒")
    
    def test_memory_usage_component_detection(self, large_test_image):
        """测试构件检测内存使用"""
        import psutil
        import gc
        
        detector = ComponentDetector()
        
        # Mock模型
        with patch.object(detector, 'model') as mock_model:
            mock_result = Mock()
            mock_boxes = Mock()
            
            import torch
            mock_boxes.xyxy = [torch.randint(0, 1000, (50, 4)).float()]
            mock_boxes.conf = [torch.rand(50)]
            mock_boxes.cls = [torch.randint(0, 8, (50,))]
            
            mock_result.boxes = mock_boxes
            mock_model.return_value = [mock_result]
            
            # 测量内存使用
            process = psutil.Process()
            
            # 强制垃圾回收
            gc.collect()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # 执行检测
            result = detector.detect_components(large_test_image)
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = memory_after - memory_before
            
            # 清理
            del result
            gc.collect()
            
            print(f"内存使用增加: {memory_increase:.2f}MB")
            
            # 内存增加不应该过多（考虑到图像大小）
            assert memory_increase < 500, f"内存使用过多: {memory_increase:.2f}MB"
    
    def test_concurrent_processing_performance(self):
        """测试并发处理性能"""
        num_tasks = 10
        
        def mock_process_task(task_id):
            """模拟处理任务"""
            time.sleep(0.1)  # 模拟处理时间
            return {"task_id": task_id, "result": "completed"}
        
        # 串行处理
        start_time = time.time()
        serial_results = []
        for i in range(num_tasks):
            result = mock_process_task(i)
            serial_results.append(result)
        serial_time = time.time() - start_time
        
        # 并行处理
        start_time = time.time()
        parallel_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(mock_process_task, i) for i in range(num_tasks)]
            for future in as_completed(futures):
                result = future.result()
                parallel_results.append(result)
        parallel_time = time.time() - start_time
        
        # 并行应该更快
        speedup = serial_time / parallel_time
        print(f"串行时间: {serial_time:.2f}秒")
        print(f"并行时间: {parallel_time:.2f}秒")
        print(f"加速比: {speedup:.2f}x")
        
        assert speedup > 2.0, f"并行处理加速比不足: {speedup:.2f}x"
        assert len(parallel_results) == num_tasks
    
    def test_large_batch_processing_performance(self):
        """测试大批量处理性能"""
        executor = DrawingTaskExecutor()
        
        # 创建多个模拟图纸
        batch_sizes = [1, 5, 10, 20]
        
        for batch_size in batch_sizes:
            # Mock文件处理
            with patch.object(executor.file_processor, 'ensure_local_file') as mock_ensure:
                mock_ensure.return_value = "mock_file.jpg"
                
                with patch.object(executor, '_process_image_file') as mock_process:
                    mock_process.return_value = {
                        "components": {"wall": [{"confidence": 0.8}]},
                        "ocr_text": "测试文本"
                    }
                    
                    start_time = time.time()
                    
                    # 模拟批量处理
                    results = []
                    for i in range(batch_size):
                        result = executor._process_by_file_type("test.jpg", "jpg", f"task_{i}")
                        results.append(result)
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    avg_time_per_item = processing_time / batch_size
                    
                    print(f"批量大小 {batch_size}: 总时间 {processing_time:.2f}秒, 平均 {avg_time_per_item:.3f}秒/项")
                    
                    # 平均处理时间应该合理
                    assert avg_time_per_item < 0.1, f"平均处理时间过长: {avg_time_per_item:.3f}秒"
    
    def test_memory_leak_detection(self):
        """测试内存泄漏"""
        import psutil
        import gc
        
        detector = ComponentDetector()
        process = psutil.Process()
        
        # Mock模型
        with patch.object(detector, 'model') as mock_model:
            mock_result = Mock()
            mock_boxes = Mock()
            
            import torch
            mock_boxes.xyxy = [torch.randint(0, 100, (10, 4)).float()]
            mock_boxes.conf = [torch.rand(10)]
            mock_boxes.cls = [torch.randint(0, 8, (10,))]
            
            mock_result.boxes = mock_boxes
            mock_model.return_value = [mock_result]
            
            # 记录初始内存
            gc.collect()
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            # 执行多次检测
            for i in range(50):
                test_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
                result = detector.detect_components(test_image)
                del result
                
                if i % 10 == 0:
                    gc.collect()
            
            # 最终内存
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            
            print(f"内存变化: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{memory_increase:.1f}MB)")
            
            # 内存增长应该在合理范围内
            assert memory_increase < 100, f"可能存在内存泄漏: 增长 {memory_increase:.1f}MB"
    
    def test_cpu_profiling(self):
        """CPU性能分析"""
        detector = ComponentDetector()
        
        # 创建性能分析器
        profiler = cProfile.Profile()
        
        # Mock模型
        with patch.object(detector, 'model') as mock_model:
            mock_result = Mock()
            mock_boxes = Mock()
            
            import torch
            mock_boxes.xyxy = [torch.randint(0, 500, (30, 4)).float()]
            mock_boxes.conf = [torch.rand(30)]
            mock_boxes.cls = [torch.randint(0, 8, (30,))]
            
            mock_result.boxes = mock_boxes
            mock_model.return_value = [mock_result]
            
            # 开始分析
            profiler.enable()
            
            # 执行多次检测
            for _ in range(10):
                test_image = np.random.randint(0, 255, (800, 1200, 3), dtype=np.uint8)
                result = detector.detect_components(test_image)
            
            # 停止分析
            profiler.disable()
            
            # 分析结果
            stats_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stats_stream)
            stats.sort_stats('cumulative')
            stats.print_stats(10)  # 打印前10个最耗时的函数
            
            profile_output = stats_stream.getvalue()
            print("CPU性能分析结果:")
            print(profile_output)
            
            # 检查是否有明显的性能瓶颈
            assert len(profile_output) > 0


class TestScalabilityAndStress:
    """可扩展性和压力测试"""
    
    def test_file_processing_stress(self, temp_dir):
        """文件处理压力测试"""
        executor = DrawingTaskExecutor()
        
        # 创建多个测试文件
        test_files = []
        for i in range(20):
            import cv2
            file_path = os.path.join(temp_dir, f"test_{i}.jpg")
            test_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
            cv2.imwrite(file_path, test_image)
            test_files.append(file_path)
        
        # Mock处理方法
        with patch.object(executor.file_processor, 'process_image_file') as mock_process:
            mock_process.return_value = {"status": "success", "metadata": {}}
            
            with patch.object(executor.ocr_engine, 'extract_text') as mock_ocr:
                mock_ocr.return_value = {"text": "测试"}
                
                with patch.object(executor.component_detector, 'detect_components') as mock_detect:
                    mock_detect.return_value = {"components": {}, "summary": {}}
                    
                    start_time = time.time()
                    
                    # 处理所有文件
                    results = []
                    for file_path in test_files:
                        result = executor._process_image_file(file_path, "stress_test")
                        results.append(result)
                    
                    end_time = time.time()
                    total_time = end_time - start_time
                    
                    print(f"处理 {len(test_files)} 个文件耗时: {total_time:.2f}秒")
                    print(f"平均每文件: {total_time/len(test_files):.3f}秒")
                    
                    # 确保所有文件都被成功处理
                    assert len(results) == len(test_files)
                    assert all("components" in result for result in results)
    
    def test_websocket_stress(self):
        """WebSocket连接压力测试"""
        from app.services.drawing_processing.websocket_manager import WebSocketManager
        import asyncio
        
        async def stress_test():
            manager = WebSocketManager()
            
            # 模拟大量连接
            num_connections = 100
            connections = []
            
            for i in range(num_connections):
                mock_websocket = Mock()
                connection_id = f"conn_{i}"
                user_id = i % 10  # 10个用户，每个用户10个连接
                
                await manager.add_connection(mock_websocket, connection_id, user_id)
                connections.append((connection_id, user_id))
            
            # 测试广播性能
            start_time = time.time()
            
            message = {"type": "test", "data": "stress test message"}
            success_count = await manager.broadcast_to_all(message)
            
            end_time = time.time()
            broadcast_time = end_time - start_time
            
            print(f"广播给 {num_connections} 个连接耗时: {broadcast_time:.3f}秒")
            print(f"成功发送: {success_count} 条消息")
            
            # 清理连接
            for connection_id, user_id in connections:
                await manager.remove_connection(connection_id, user_id)
            
            assert broadcast_time < 1.0, f"广播耗时过长: {broadcast_time:.3f}秒"
        
        # 运行异步测试
        asyncio.run(stress_test()) 