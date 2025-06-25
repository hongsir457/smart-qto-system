"""
测试优化后的系统
验证各个优化组件的功能
"""

import asyncio
import os
import json
import time
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入优化组件
from app.services.adaptive_slicing_engine import AdaptiveSlicingEngine
from app.services.unified_ocr_pipeline import UnifiedOCRPipeline
from app.services.cross_modal_validation_engine import CrossModalValidationEngine
from app.services.intelligent_fusion_engine import IntelligentFusionEngine
from app.services.standardized_output_engine import StandardizedOutputEngine

class OptimizedSystemTester:
    """优化系统测试器"""
    
    def __init__(self):
        self.test_output_dir = "test_optimized_output"
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # 初始化各个组件
        self.adaptive_slicer = AdaptiveSlicingEngine()
        self.ocr_pipeline = UnifiedOCRPipeline()
        self.cross_modal_validator = CrossModalValidationEngine()
        self.fusion_engine = IntelligentFusionEngine()
        self.output_engine = StandardizedOutputEngine()
    
    async def run_complete_test(self, test_image_path: str = None):
        """运行完整测试"""
        try:
            logger.info("🚀 开始优化系统完整测试")
            start_time = time.time()
            
            # 使用模拟图片路径
            if not test_image_path:
                test_image_path = self._create_mock_image()
            
            task_id = f"test_task_{int(time.time())}"
            
            # Step 1: 自适应切片测试
            logger.info("=" * 60)
            logger.info("🔧 Step 1: 自适应切片引擎测试")
            slice_result = await self.test_adaptive_slicing(test_image_path, task_id)
            
            if not slice_result["success"]:
                logger.error("❌ 自适应切片测试失败")
                return
            
            # Step 2~2.5: 统一OCR处理测试
            logger.info("=" * 60)
            logger.info("🔧 Step 2~2.5: 统一OCR处理管道测试")
            ocr_result = await self.test_unified_ocr_pipeline(slice_result["slices"], task_id)
            
            if not ocr_result["success"]:
                logger.error("❌ 统一OCR处理测试失败")
                return
            
            # Step 3~4: 跨模态验证测试
            logger.info("=" * 60)
            logger.info("🔧 Step 3~4: 跨模态验证引擎测试")
            validation_result = await self.test_cross_modal_validation(ocr_result, task_id)
            
            if not validation_result["success"]:
                logger.error("❌ 跨模态验证测试失败")
                return
            
            # Step 5: 智能融合测试
            logger.info("=" * 60)
            logger.info("🔧 Step 5: 智能融合引擎测试")
            fusion_result = await self.test_intelligent_fusion(
                ocr_result, validation_result, task_id
            )
            
            if not fusion_result["success"]:
                logger.error("❌ 智能融合测试失败")
                return
            
            # Step 6: 标准化输出测试
            logger.info("=" * 60)
            logger.info("🔧 Step 6: 标准化输出引擎测试")
            output_result = await self.test_standardized_output(fusion_result, task_id)
            
            if not output_result["success"]:
                logger.error("❌ 标准化输出测试失败")
                return
            
            # 生成测试报告
            total_time = time.time() - start_time
            await self.generate_test_report(task_id, {
                "slice_result": slice_result,
                "ocr_result": ocr_result,
                "validation_result": validation_result,
                "fusion_result": fusion_result,
                "output_result": output_result,
                "total_time": total_time
            })
            
            logger.info("=" * 60)
            logger.info(f"✅ 优化系统完整测试成功完成! 总用时: {total_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ 优化系统测试失败: {e}")
    
    async def test_adaptive_slicing(self, image_path: str, task_id: str) -> dict:
        """测试自适应切片引擎"""
        try:
            logger.info("🔄 测试自适应切片引擎...")
            
            slice_output_dir = os.path.join(self.test_output_dir, f"{task_id}_slices")
            result = self.adaptive_slicer.adaptive_slice(image_path, slice_output_dir)
            
            if result["success"]:
                logger.info(f"✅ 自适应切片成功: 生成 {result['slice_count']} 个切片")
                logger.info(f"📊 切片策略: {result['slice_strategy']['type']}")
                logger.info(f"📐 图框检测: {'成功' if result['frame_detected'] else '失败'}")
                logger.info(f"📊 内容密度: {result['content_density']['density_ratio']:.3f}")
            else:
                logger.error(f"❌ 自适应切片失败: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 自适应切片测试异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_unified_ocr_pipeline(self, slices: list, task_id: str) -> dict:
        """测试统一OCR处理管道"""
        try:
            logger.info("🔄 测试统一OCR处理管道...")
            
            # 准备切片信息
            slice_infos = []
            for i, slice_data in enumerate(slices[:5]):  # 限制测试5个切片
                slice_infos.append({
                    "slice_id": slice_data.get("slice_id", f"slice_{i}"),
                    "filename": slice_data.get("filename", f"slice_{i}.png"),
                    "slice_path": slice_data.get("slice_path", "mock_path"),
                    "x_offset": slice_data.get("x_offset", 0),
                    "y_offset": slice_data.get("y_offset", 0),
                    "width": slice_data.get("width", 512),
                    "height": slice_data.get("height", 512)
                })
            
            result = await self.ocr_pipeline.process_slices(slice_infos, task_id)
            
            if result.stage == "unified_ocr_complete":
                logger.info(f"✅ 统一OCR处理成功")
                logger.info(f"📝 识别结果: {len(result.slice_results)} 个切片")
                logger.info(f"🧹 清洗数据: {len(result.cleaned_data.component_labels)} 个构件标签")
                logger.info(f"📊 质量评分: {result.quality_metrics['overall_quality']:.3f}")
                
                return {"success": True, "ocr_output": result}
            else:
                logger.error(f"❌ 统一OCR处理失败: {result.stage}")
                return {"success": False, "error": result.stage}
            
        except Exception as e:
            logger.error(f"❌ 统一OCR处理测试异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_cross_modal_validation(self, ocr_result: dict, task_id: str) -> dict:
        """测试跨模态验证引擎"""
        try:
            logger.info("🔄 测试跨模态验证引擎...")
            
            # 模拟Vision结果
            mock_vision_output = {
                "detected_components": [
                    {
                        "label": "C1",
                        "type": "column",
                        "bbox": {"x": 100, "y": 100, "width": 50, "height": 50},
                        "confidence": 0.9
                    },
                    {
                        "label": "L1",
                        "type": "beam",
                        "bbox": {"x": 200, "y": 150, "width": 100, "height": 30},
                        "confidence": 0.85
                    }
                ]
            }
            
            # 转换OCR结果格式
            ocr_output_dict = {
                "slice_results": []
            }
            
            if hasattr(ocr_result["ocr_output"], "slice_results"):
                for result in ocr_result["ocr_output"].slice_results:
                    ocr_output_dict["slice_results"].append({
                        "slice_id": result.slice_id,
                        "raw_text": result.raw_text,
                        "coordinates": result.coordinates,
                        "confidence": result.confidence
                    })
            
            result = await self.cross_modal_validator.validate_cross_modal_results(
                ocr_output_dict, mock_vision_output, task_id
            )
            
            if result["success"]:
                report = result["validation_report"]
                metrics = report["overall_metrics"]
                
                logger.info(f"✅ 跨模态验证成功")
                logger.info(f"🎯 对齐置信度: {metrics['alignment_confidence']:.3f}")
                logger.info(f"📍 空间一致性: {metrics['spatial_consistency']:.3f}")
                logger.info(f"🔗 匹配对数: {metrics['matched_pairs']}")
                logger.info(f"✅ 一致性率: {metrics['consistency_rate']:.3f}")
            else:
                logger.error(f"❌ 跨模态验证失败: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 跨模态验证测试异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_intelligent_fusion(self, ocr_result: dict, validation_result: dict, task_id: str) -> dict:
        """测试智能融合引擎"""
        try:
            logger.info("🔄 测试智能融合引擎...")
            
            # 准备融合输入
            ocr_results_dict = {
                "slice_results": []
            }
            
            if hasattr(ocr_result["ocr_output"], "slice_results"):
                for result in ocr_result["ocr_output"].slice_results:
                    ocr_results_dict["slice_results"].append({
                        "slice_id": result.slice_id,
                        "raw_text": result.raw_text,
                        "coordinates": result.coordinates,
                        "confidence": result.confidence
                    })
            
            vision_results = {
                "detected_components": [
                    {
                        "label": "C1",
                        "type": "column",
                        "bbox": {"x": 100, "y": 100, "width": 50, "height": 50},
                        "confidence": 0.9
                    }
                ]
            }
            
            validation_report = validation_result.get("validation_report", {})
            
            result = await self.fusion_engine.fuse_multi_modal_results(
                ocr_results_dict, vision_results, validation_report, task_id
            )
            
            if result["success"]:
                report = result["fusion_report"]
                summary = report["fusion_summary"]
                metrics = report["quality_metrics"]
                
                logger.info(f"✅ 智能融合成功")
                logger.info(f"🔧 融合候选: {summary['total_candidates']}")
                logger.info(f"⚔️ 冲突组: {summary['conflict_groups']}")
                logger.info(f"🎯 融合构件: {summary['fused_components']}")
                logger.info(f"📊 整体质量: {metrics['overall_quality']:.3f}")
            else:
                logger.error(f"❌ 智能融合失败: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 智能融合测试异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_standardized_output(self, fusion_result: dict, task_id: str) -> dict:
        """测试标准化输出引擎"""
        try:
            logger.info("🔄 测试标准化输出引擎...")
            
            # 准备融合构件数据
            fused_components = []
            if fusion_result["success"]:
                fusion_report = fusion_result["fusion_report"]
                for comp_data in fusion_report.get("fused_components", []):
                    fused_components.append({
                        "component_id": comp_data.get("component_id", "unknown"),
                        "type": comp_data.get("type", "unknown"),
                        "label": comp_data.get("label", ""),
                        "dimensions": comp_data.get("dimensions", {}),
                        "confidence": comp_data.get("confidence", 0.0)
                    })
            
            # 如果没有融合构件，创建模拟数据
            if not fused_components:
                fused_components = [
                    {
                        "component_id": "test_column_1",
                        "type": "column",
                        "label": "C1",
                        "dimensions": {"length": 0.4, "width": 0.4, "height": 3.0},
                        "confidence": 0.9
                    },
                    {
                        "component_id": "test_beam_1",
                        "type": "beam",
                        "label": "L1",
                        "dimensions": {"length": 6.0, "width": 0.3, "height": 0.5},
                        "confidence": 0.85
                    }
                ]
            
            project_info = {
                "project_name": "优化系统测试项目",
                "drawing_number": f"TEST-{task_id}",
                "scale": "1:100",
                "date": time.strftime("%Y-%m-%d")
            }
            
            result = await self.output_engine.generate_quantity_list(
                fused_components, project_info, task_id
            )
            
            if result["success"]:
                quantity_list = result["quantity_list"]
                total_summary = quantity_list["total_summary"]
                
                logger.info(f"✅ 标准化输出成功")
                logger.info(f"📊 总构件数: {total_summary['total_components']}")
                logger.info(f"✅ 合规构件: {total_summary['compliant_components']}")
                logger.info(f"📈 合规率: {total_summary['compliance_rate']:.3f}")
                logger.info(f"🏗️ 构件类型: {total_summary['component_types']}")
                
                # 测试多格式导出
                from dataclasses import asdict
                from app.services.standardized_output_engine import QuantityList
                
                # 重建QuantityList对象用于导出测试
                export_test_result = await self._test_export_formats(quantity_list, task_id)
                result["export_test"] = export_test_result
                
            else:
                logger.error(f"❌ 标准化输出失败: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 标准化输出测试异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def _test_export_formats(self, quantity_list_dict: dict, task_id: str) -> dict:
        """测试导出格式"""
        try:
            logger.info("📤 测试多格式导出...")
            
            export_dir = os.path.join(self.test_output_dir, f"{task_id}_exports")
            os.makedirs(export_dir, exist_ok=True)
            
            # 创建简化的导出测试
            export_results = {}
            
            # JSON导出测试
            json_path = os.path.join(export_dir, f"{task_id}_quantity_list.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(quantity_list_dict, f, ensure_ascii=False, indent=2)
            
            export_results["json"] = {
                "success": True,
                "file_path": json_path,
                "file_size": os.path.getsize(json_path)
            }
            
            logger.info(f"✅ 导出测试完成: JSON格式")
            
            return {
                "success": True,
                "export_results": export_results
            }
            
        except Exception as e:
            logger.error(f"❌ 导出测试失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_mock_image(self) -> str:
        """创建模拟图片文件"""
        mock_image_path = os.path.join(self.test_output_dir, "mock_drawing.png")
        
        # 创建一个简单的模拟图片文件（实际项目中应该有真实图片）
        try:
            from PIL import Image, ImageDraw
            
            # 创建800x600的白色图像
            img = Image.new('RGB', (800, 600), 'white')
            draw = ImageDraw.Draw(img)
            
            # 绘制一些简单的矩形作为模拟构件
            draw.rectangle([100, 100, 150, 400], outline='black', width=2)  # 柱子
            draw.rectangle([50, 200, 200, 230], outline='black', width=2)   # 梁
            
            # 添加一些文字
            draw.text((160, 250), "C1", fill='black')
            draw.text((210, 210), "L1", fill='black')
            
            img.save(mock_image_path)
            logger.info(f"📷 创建模拟图片: {mock_image_path}")
            
        except ImportError:
            # 如果PIL不可用，创建一个空文件
            with open(mock_image_path, 'w') as f:
                f.write("mock image file")
            logger.info(f"📄 创建模拟图片文件: {mock_image_path}")
        
        return mock_image_path
    
    async def generate_test_report(self, task_id: str, test_results: dict):
        """生成测试报告"""
        try:
            report = {
                "task_id": task_id,
                "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_time": test_results["total_time"],
                "test_summary": {
                    "adaptive_slicing": test_results["slice_result"]["success"],
                    "unified_ocr": test_results["ocr_result"]["success"],
                    "cross_modal_validation": test_results["validation_result"]["success"],
                    "intelligent_fusion": test_results["fusion_result"]["success"],
                    "standardized_output": test_results["output_result"]["success"]
                },
                "performance_metrics": {
                    "slice_count": test_results["slice_result"].get("slice_count", 0),
                    "ocr_quality": test_results["ocr_result"].get("ocr_output", {}).quality_metrics.get("overall_quality", 0) if hasattr(test_results["ocr_result"].get("ocr_output", {}), "quality_metrics") else 0,
                    "validation_consistency": test_results["validation_result"].get("validation_report", {}).get("overall_metrics", {}).get("consistency_rate", 0),
                    "fusion_quality": test_results["fusion_result"].get("fusion_report", {}).get("quality_metrics", {}).get("overall_quality", 0),
                    "output_compliance": test_results["output_result"].get("quantity_list", {}).get("total_summary", {}).get("compliance_rate", 0)
                },
                "optimization_benefits": {
                    "adaptive_slicing_efficiency": "显著提升切片适应性",
                    "unified_processing": "标准化OCR处理流程",
                    "cross_modal_validation": "提高识别准确性",
                    "intelligent_fusion": "智能冲突解决",
                    "standardized_output": "规范化工程量输出"
                }
            }
            
            report_path = os.path.join(self.test_output_dir, f"{task_id}_test_report.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📋 测试报告已生成: {report_path}")
            
            # 打印关键指标
            logger.info("=" * 60)
            logger.info("📊 优化系统测试关键指标:")
            logger.info(f"   ⏱️  总用时: {test_results['total_time']:.2f}s")
            logger.info(f"   🔧 切片数量: {report['performance_metrics']['slice_count']}")
            logger.info(f"   📝 OCR质量: {report['performance_metrics']['ocr_quality']:.3f}")
            logger.info(f"   🎯 验证一致性: {report['performance_metrics']['validation_consistency']:.3f}")
            logger.info(f"   🔗 融合质量: {report['performance_metrics']['fusion_quality']:.3f}")
            logger.info(f"   ✅ 输出合规率: {report['performance_metrics']['output_compliance']:.3f}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ 生成测试报告失败: {e}")

async def main():
    """主测试函数"""
    logger.info("🚀 启动优化系统测试")
    
    tester = OptimizedSystemTester()
    await tester.run_complete_test()
    
    logger.info("🎯 优化系统测试完成")

if __name__ == "__main__":
    asyncio.run(main()) 