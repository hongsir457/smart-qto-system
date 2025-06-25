#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应处理器 - 负责处理AI响应的解析和后处理
"""
import logging
import json
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ResponseProcessor:
    """
    负责处理AI响应的解析、验证和后处理
    """
    
    def __init__(self, mock_detector):
        """初始化响应处理器"""
        self.mock_detector = mock_detector
        logger.info("✅ ResponseProcessor initialized")
    
    def process_qto_response(self, raw_response: str, task_id: str = None) -> Dict[str, Any]:
        """处理QTO生成响应"""
        try:
            # 1. 解析JSON响应
            if not raw_response:
                return {"error": "Empty response from LLM"}
            
            try:
                qto_data = json.loads(raw_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                return {
                    "error": "Invalid JSON response from LLM", 
                    "raw_response": raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
                }
            
            # 2. 验证响应结构
            validation_result = self._validate_qto_structure(qto_data)
            if not validation_result["valid"]:
                logger.warning(f"QTO结构验证失败: {validation_result['errors']}")
                return {
                    "error": "Invalid QTO structure",
                    "validation_errors": validation_result["errors"],
                    "qto_data": qto_data
                }
            
            # 3. 检测模拟数据
            mock_check = self.mock_detector.enhance_mock_data_detection(qto_data)
            if mock_check.get("is_mock_detected"):
                logger.warning("🚨 检测到模拟数据模式")
                qto_data["_warnings"] = ["检测到可能的模拟数据"]
            
            # 4. 后处理优化
            processed_data = self._post_process_qto_data(qto_data)
            
            logger.info("✅ QTO响应处理完成")
            return {
                "success": True,
                "qto_data": processed_data,
                "mock_detected": mock_check.get("is_mock_detected", False)
            }
            
        except Exception as e:
            logger.error(f"❌ QTO响应处理异常: {e}")
            return {"error": str(e)}
    
    def process_vision_response(self, raw_response: str, step_name: str) -> Dict[str, Any]:
        """处理Vision分析响应"""
        try:
            # 1. 解析响应
            if not raw_response:
                return {"error": f"{step_name} returned empty response"}
            
            try:
                parsed_data = json.loads(raw_response)
            except json.JSONDecodeError:
                # 如果不是有效JSON，尝试提取JSON片段
                parsed_data = self._extract_json_from_text(raw_response)
                if not parsed_data:
                    return {
                        "success": True, 
                        "response": raw_response, 
                        "raw": True,
                        "note": "Non-JSON response"
                    }
            
            # 2. 验证步骤特定的数据结构
            validation_result = self._validate_step_data(step_name, parsed_data)
            if not validation_result["valid"]:
                logger.warning(f"{step_name} 数据验证失败: {validation_result['errors']}")
            
            # 3. 清理和标准化数据
            cleaned_data = self._clean_step_data(step_name, parsed_data)
            
            return {
                "success": True,
                "response": cleaned_data,
                "validation": validation_result
            }
            
        except Exception as e:
            logger.error(f"❌ {step_name} 响应处理异常: {e}")
            return {"error": str(e)}
    
    def synthesize_qto_data(self, analysis_results: Dict) -> Dict[str, Any]:
        """综合多步分析结果生成最终QTO数据"""
        try:
            # 提取各步骤的数据
            drawing_info = self._extract_step_data(analysis_results, "step1_drawing_info")
            component_ids = self._extract_step_data(analysis_results, "step2_component_ids")
            component_counts = self._extract_step_data(analysis_results, "step3_component_counts")
            positions = self._extract_step_data(analysis_results, "step4_positions")
            attributes = self._extract_step_data(analysis_results, "step5_attributes")
            
            # 构建综合QTO数据
            qto_data = {
                "drawing_info": drawing_info or {},
                "components": self._build_component_list(component_ids, component_counts, positions, attributes),
                "summary": self._generate_quantity_summary(analysis_results),
                "metadata": {
                    "analysis_method": "5步分析法",
                    "steps_completed": len([r for r in analysis_results.values() if r.get("success")]),
                    "total_steps": 5
                }
            }
            
            # 验证最终数据
            validation_result = self._validate_qto_structure(qto_data)
            if validation_result["valid"]:
                logger.info("✅ QTO数据综合完成")
                return {"success": True, "qto_data": qto_data}
            else:
                logger.warning(f"⚠️ 综合数据验证失败: {validation_result['errors']}")
                return {
                    "success": True,
                    "qto_data": qto_data,
                    "warnings": validation_result["errors"]
                }
            
        except Exception as e:
            logger.error(f"❌ QTO数据综合失败: {e}")
            return {"error": str(e)}
    
    def _validate_qto_structure(self, qto_data: Dict) -> Dict[str, Any]:
        """验证QTO数据结构"""
        errors = []
        
        # 检查必需字段
        required_fields = ["drawing_info", "components"]
        for field in required_fields:
            if field not in qto_data:
                errors.append(f"缺少必需字段: {field}")
        
        # 验证drawing_info结构
        if "drawing_info" in qto_data:
            drawing_info = qto_data["drawing_info"]
            if not isinstance(drawing_info, dict):
                errors.append("drawing_info 必须是字典类型")
        
        # 验证components结构
        if "components" in qto_data:
            components = qto_data["components"]
            if not isinstance(components, list):
                errors.append("components 必须是列表类型")
            else:
                for i, comp in enumerate(components):
                    if not isinstance(comp, dict):
                        errors.append(f"构件{i+1} 必须是字典类型")
                        continue
                    
                    # 检查构件必需字段
                    required_comp_fields = ["component_id", "component_type"]
                    for field in required_comp_fields:
                        if field not in comp:
                            errors.append(f"构件{i+1} 缺少字段: {field}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _validate_step_data(self, step_name: str, data: Any) -> Dict[str, Any]:
        """验证特定步骤的数据结构"""
        errors = []
        
        if step_name == "Step1_图纸信息":
            if not isinstance(data, dict):
                errors.append("图纸信息必须是字典类型")
            elif not any(key in data for key in ["project_name", "title", "drawing_number"]):
                errors.append("缺少基本图纸信息")
        
        elif step_name == "Step2_构件编号":
            if not isinstance(data, dict):
                errors.append("构件编号必须是字典类型")
            elif not data:
                errors.append("未识别到任何构件编号")
        
        elif step_name == "Step3_构件统计":
            if not isinstance(data, dict):
                errors.append("构件统计必须是字典类型")
        
        elif step_name == "Step4_位置信息":
            if not isinstance(data, dict):
                errors.append("位置信息必须是字典类型")
        
        elif step_name == "Step5_属性信息":
            if not isinstance(data, dict):
                errors.append("属性信息必须是字典类型")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _clean_step_data(self, step_name: str, data: Any) -> Any:
        """清理和标准化步骤数据"""
        if not isinstance(data, dict):
            return data
        
        cleaned_data = {}
        
        for key, value in data.items():
            # 清理空值
            if value is None or value == "":
                continue
            
            # 标准化字符串
            if isinstance(value, str):
                value = value.strip()
                if value in ["信息不明确", "待确认", "无法识别", ""]:
                    continue
            
            cleaned_data[key] = value
        
        return cleaned_data
    
    def _extract_step_data(self, analysis_results: Dict, step_key: str) -> Dict:
        """从分析结果中提取步骤数据"""
        step_result = analysis_results.get(step_key, {})
        if step_result.get("success"):
            return step_result.get("response", {})
        return {}
    
    def _build_component_list(self, component_ids: Dict, component_counts: Dict, 
                            positions: Dict, attributes: Dict) -> List[Dict]:
        """构建构件清单"""
        components = []
        
        try:
            # 遍历识别的构件编号
            for comp_type, ids in component_ids.items():
                if isinstance(ids, list):
                    for comp_id in ids:
                        component = {
                            "component_id": comp_id,
                            "component_type": self._determine_component_type(comp_id),
                            "count": component_counts.get(comp_id, 1),
                            "position": positions.get(comp_id, {}),
                            "dimensions": attributes.get(comp_id, {}),
                            "source": "AI分析"
                        }
                        components.append(component)
                elif isinstance(ids, dict):
                    # 如果是字典格式，遍历键值对
                    for comp_id, details in ids.items():
                        component = {
                            "component_id": comp_id,
                            "component_type": self._determine_component_type(comp_id),
                            "count": component_counts.get(comp_id, 1),
                            "position": positions.get(comp_id, {}),
                            "dimensions": attributes.get(comp_id, {}),
                            "details": details if isinstance(details, dict) else {},
                            "source": "AI分析"
                        }
                        components.append(component)
        except Exception as e:
            logger.warning(f"⚠️ 构建构件清单异常: {e}")
        
        return components
    
    def _determine_component_type(self, component_id: str) -> str:
        """根据构件编号确定构件类型"""
        if not isinstance(component_id, str):
            return "未知构件"
            
        component_id = component_id.upper()
        
        if component_id.startswith("KZ"):
            return "框架柱"
        elif component_id.startswith("L"):
            return "梁"
        elif component_id.startswith("B"):
            return "板"
        elif component_id.startswith("Q"):
            return "墙"
        elif component_id.startswith("J"):
            return "基础"
        elif component_id.startswith("TL"):
            return "楼梯"
        else:
            return "其他构件"
    
    def _generate_quantity_summary(self, analysis_results: Dict) -> Dict[str, Any]:
        """生成工程量汇总"""
        summary = {
            "total_components": 0,
            "component_types": {},
            "analysis_quality": "good"
        }
        
        try:
            # 从第3步获取构件统计
            component_counts = self._extract_step_data(analysis_results, "step3_component_counts")
            
            total = 0
            type_counts = {}
            
            for comp_id, count in component_counts.items():
                if isinstance(count, (int, float)) and count > 0:
                    total += count
                    comp_type = self._determine_component_type(comp_id)
                    type_counts[comp_type] = type_counts.get(comp_type, 0) + count
                elif isinstance(count, str):
                    try:
                        count_num = float(count)
                        total += count_num
                        comp_type = self._determine_component_type(comp_id)
                        type_counts[comp_type] = type_counts.get(comp_type, 0) + count_num
                    except ValueError:
                        continue
            
            summary["total_components"] = total
            summary["component_types"] = type_counts
            
            # 评估分析质量
            steps_successful = sum(1 for result in analysis_results.values() if result.get("success"))
            if steps_successful >= 4:
                summary["analysis_quality"] = "good"
            elif steps_successful >= 3:
                summary["analysis_quality"] = "fair"
            else:
                summary["analysis_quality"] = "limited"
            
        except Exception as e:
            logger.warning(f"⚠️ 汇总生成异常: {e}")
            summary["analysis_quality"] = "error"
        
        return summary
    
    def _post_process_qto_data(self, qto_data: Dict) -> Dict:
        """对QTO数据进行后处理优化"""
        try:
            # 1. 清理空字段
            cleaned_data = self._remove_empty_fields(qto_data)
            
            # 2. 标准化构件类型
            if "components" in cleaned_data:
                for component in cleaned_data["components"]:
                    if "component_type" in component:
                        component["component_type"] = self._standardize_component_type(
                            component["component_type"]
                        )
            
            # 3. 添加元数据
            cleaned_data["_metadata"] = {
                "processed_at": time.time(),
                "processing_version": "1.0"
            }
            
            return cleaned_data
        except Exception as e:
            logger.warning(f"⚠️ QTO数据后处理异常: {e}")
            return qto_data
    
    def _remove_empty_fields(self, data: Any) -> Any:
        """递归移除空字段"""
        if isinstance(data, dict):
            return {k: self._remove_empty_fields(v) for k, v in data.items() 
                   if v is not None and v != "" and v != {}}
        elif isinstance(data, list):
            return [self._remove_empty_fields(item) for item in data 
                   if item is not None and item != ""]
        else:
            return data
    
    def _standardize_component_type(self, comp_type: str) -> str:
        """标准化构件类型名称"""
        type_mapping = {
            "柱": "框架柱",
            "梁": "梁",
            "板": "板",
            "墙": "墙",
            "基础": "基础",
            "楼梯": "楼梯"
        }
        
        for key, value in type_mapping.items():
            if key in comp_type:
                return value
        
        return comp_type
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict]:
        """从文本中提取JSON片段"""
        try:
            # 尝试找到JSON开始和结束标记
            start_markers = ['{', '[']
            end_markers = ['}', ']']
            
            for start_marker, end_marker in zip(start_markers, end_markers):
                start_idx = text.find(start_marker)
                if start_idx != -1:
                    end_idx = text.rfind(end_marker)
                    if end_idx > start_idx:
                        json_text = text[start_idx:end_idx + 1]
                        try:
                            return json.loads(json_text)
                        except json.JSONDecodeError:
                            continue
            
            return None
        except Exception:
            return None 