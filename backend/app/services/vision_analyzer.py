#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision分析器 - 直接使用大模型Vision能力分析图纸
用于与PaddleOCR结果对比
"""

import os
import json
import base64
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from pathlib import Path

from app.core.config import settings
from app.services.s3_service import S3Service
from app.services.ai_analyzer import AIAnalyzerService
from app.services.dual_storage_service import DualStorageService

logger = logging.getLogger(__name__)

class VisionAnalyzer:
    """Vision分析器 - 使用双重存储服务"""
    
    def __init__(self):
        """初始化Vision分析器"""
        self.ai_service = AIAnalyzerService()
        
        # 使用双重存储服务
        try:
            self.storage_service = DualStorageService()
            logger.info("✅ VisionAnalyzer 使用双重存储服务")
        except Exception as e:
            logger.error(f"双重存储服务初始化失败: {e}")
            self.storage_service = None
        
        self.s3_service = S3Service()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
    def encode_image_to_base64(self, image_path: str) -> str:
        """将图片编码为base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"图片编码失败: {e}")
            raise
    
    def _get_structured_prompt(self) -> str:
        """获取结构化分析的系统提示词和JSON schema约束"""
        return """
你是一个专业的建筑工程造价师，你的任务是分析上传的建筑结构图纸图片。
请仔细识别图中的所有信息，并严格按照以下JSON格式输出你的分析结果。

JSON格式定义:
{
  "drawing_info": {
    "title": "图纸标题，如果找不到则为 'Unknown'",
    "scale": "比例尺，如果找不到则为 'Unknown'",
    "drawing_number": "图号，如果找不到则为 'Unknown'",
    "floor_info": "楼层信息，如果找不到则为 'Unknown'"
  },
  "components": [
    {
      "component_id": "构件的唯一编号, 例如 'K-JKZ-5'",
      "component_type": "构件类型, 例如 '框架柱', '梁', '板', '墙'",
      "dimensions": {
        "raw_text": "原始尺寸文本，例如 '300x500', 'Φ8@200'",
        "length_m": "长度（米）",
        "width_m": "宽度（米）",
        "height_m": "高度（米）",
        "thickness_m": "厚度（米）",
        "diameter_m": "直径（米）"
      },
      "reinforcement": {
        "main": "主筋信息, 例如 '8Φ25'",
        "stirrup": "箍筋信息, 例如 'Φ8@200'"
      },
      "quantity": "数量, 默认为 1",
      "notes": "其他备注信息"
    }
  ],
  "raw_text_summary": "图中识别出的所有文本摘要"
}

请确保所有尺寸都已转换为米（m）为单位。如果原始单位是毫米（mm），请进行换算。
如果某些字段无法识别，请使用 null 或者合理的默认值。
不要在JSON之外添加任何说明或注释。
"""
    
    def analyze_with_gpt4v(self, image_path: str) -> Dict[str, Any]:
        """使用GPT-4V分析图纸，并强制使用JSON模式"""
        try:
            base64_image = self.encode_image_to_base64(image_path)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            system_prompt = self._get_structured_prompt()
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请根据系统提示词中的JSON格式要求，分析这张图纸。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 4000,
                "temperature": 0.1
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[DEBUG] GPT-4o 原始响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                content = result['choices'][0]['message']['content']
                
                # 尝试解析JSON
                try:
                    analysis_result = json.loads(content)
                    analysis_result['analysis_method'] = 'gpt4v_direct_vision_json_mode'
                    analysis_result['timestamp'] = datetime.now().isoformat()
                    analysis_result['model_used'] = 'gpt-4o'
                    
                    return {
                        'status': 'success',
                        'data': analysis_result,
                        'raw_response': content
                    }
                    
                except json.JSONDecodeError as e:
                    logger.error(f"GPT-4V返回内容JSON解析失败: {e}. Raw content: {content}")
                    return {
                        'status': 'partial_success',
                        'data': {
                            'analysis_method': 'gpt4v_direct_vision_json_mode',
                            'timestamp': datetime.now().isoformat(),
                            'error': 'JSON解析失败',
                            'raw_content': content
                        },
                        'raw_response': content
                    }
            else:
                logger.error(f"GPT-4V API调用失败: {response.status_code}, {response.text}")
                return {
                    'status': 'error',
                    'error': f"API调用失败: {response.status_code}",
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"GPT-4V分析失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def analyze_with_claude(self, image_path: str) -> Dict[str, Any]:
        """使用Claude-3.5-Sonnet分析图纸，并使用Tool Use强制JSON输出"""
        try:
            base64_image = self.encode_image_to_base64(image_path)
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.anthropic_api_key,
                "anthropic-version": "2023-06-01"
            }
            
            tool_schema = {
                "name": "extract_drawing_data",
                "description": "从建筑结构图纸中提取结构化的构件和图纸信息。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "drawing_info": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "图纸标题"},
                                "scale": {"type": "string", "description": "比例尺"},
                                "drawing_number": {"type": "string", "description": "图号"},
                                "floor_info": {"type": "string", "description": "楼层信息"}
                            },
                            "required": ["title", "scale", "drawing_number", "floor_info"]
                        },
                        "components": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "component_id": {"type": "string", "description": "构件的唯一编号, 例如 'K-JKZ-5'"},
                                    "component_type": {"type": "string", "description": "构件类型, 例如 '框架柱', '梁'"},
                                    "dimensions": {
                                        "type": "object",
                                        "properties": {
                                            "raw_text": {"type": "string", "description": "原始尺寸文本，例如 '300x500'"},
                                            "length_m": {"type": "number", "description": "长度（米）"},
                                            "width_m": {"type": "number", "description": "宽度（米）"},
                                            "height_m": {"type": "number", "description": "高度（米）"},
                                            "thickness_m": {"type": "number", "description": "厚度（米）"},
                                            "diameter_m": {"type": "number", "description": "直径（米）"}
                                        }
                                    },
                                    "reinforcement": {
                                        "type": "object",
                                        "properties": {
                                            "main": {"type": "string", "description": "主筋信息, 例如 '8Φ25'"},
                                            "stirrup": {"type": "string", "description": "箍筋信息, 例如 'Φ8@200'"}
                                        }
                                    },
                                    "quantity": {"type": "integer", "description": "数量, 默认为 1"},
                                    "notes": {"type": "string", "description": "其他备注信息"}
                                },
                                "required": ["component_id", "component_type"]
                            }
                        },
                        "raw_text_summary": {"type": "string", "description": "图中识别出的所有文本摘要"}
                    },
                    "required": ["drawing_info", "components"]
                }
            }

            payload = {
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 4000,
                "temperature": 0.1,
                "system": "你是一个专业的建筑工程造价师，请使用提供的工具 `extract_drawing_data` 来分析图纸图片并提取信息。所有尺寸单位需转换为米。",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": "请分析这张图纸，并使用 `extract_drawing_data` 工具返回结果。"
                            }
                        ],
                    }
                ],
                "tools": [tool_schema],
                "tool_choice": {"type": "tool", "name": "extract_drawing_data"}
            }

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[DEBUG] Claude 原始响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                analysis_result = None
                raw_content = ""

                for block in result.get('content', []):
                    if block['type'] == 'tool_use' and block['name'] == 'extract_drawing_data':
                        analysis_result = block['input']
                        raw_content = json.dumps(analysis_result, ensure_ascii=False)
                        break
                
                if analysis_result:
                    analysis_result['analysis_method'] = 'claude_direct_vision_tool_use'
                    analysis_result['timestamp'] = datetime.now().isoformat()
                    analysis_result['model_used'] = result.get('model', 'claude-3-5-sonnet')

                    return {
                        'status': 'success',
                        'data': analysis_result,
                        'raw_response': raw_content
                    }
                else:
                    raw_text_response = result.get('content', [{}])[0].get('text', '')
                    logger.warning(f"Claude 未能按预期使用工具。Raw Response: {raw_text_response}")
                    return {
                        'status': 'partial_success',
                        'data': {
                           'analysis_method': 'claude_direct_vision_tool_use',
                           'timestamp': datetime.now().isoformat(),
                           'error': '模型未能使用指定的工具返回结果',
                           'raw_content': raw_text_response
                        },
                        'raw_response': json.dumps(result, ensure_ascii=False)
                    }

            else:
                logger.error(f"Claude API 调用失败: {response.status_code}, {response.text}")
                return {
                    'status': 'error',
                    'error': f"API 调用失败: {response.status_code}",
                    'details': response.text
                }

        except Exception as e:
            logger.error(f"Claude 分析失败: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def analyze_image(self, image_path: str, task_id: str, model_preference: str = "both") -> Dict[str, Any]:
        """分析图纸并保存结果到S3"""
        try:
            logger.info(f"开始Vision分析: {image_path}, 任务ID: {task_id}")
            
            results = {}
            
            # 根据偏好选择模型
            if model_preference in ["gpt4v", "both"] and self.openai_api_key:
                logger.info("使用GPT-4V分析...")
                results['gpt4v'] = self.analyze_with_gpt4v(image_path)
            
            if model_preference in ["claude", "both"] and self.anthropic_api_key:
                logger.info("使用Claude分析...")
                results['claude'] = self.analyze_with_claude(image_path)
            
            if not results:
                return {
                    'status': 'error',
                    'error': '没有可用的Vision模型API密钥'
                }
            
            # 合并结果
            combined_result = {
                'task_id': task_id,
                'image_path': image_path,
                'analysis_timestamp': datetime.now().isoformat(),
                'models_used': list(results.keys()),
                'results': results
            }
            
            # 保存到S3
            s3_key = f"vision_analysis/{task_id}/vision_result.json"
            s3_url = self.save_result_to_storage(combined_result, s3_key)
            
            combined_result['s3_storage'] = {
                'key': s3_key,
                'url': s3_url
            }
            
            logger.info(f"Vision分析完成，结果已保存到S3: {s3_key}")
            
            return {
                'status': 'success',
                'data': combined_result,
                's3_url': s3_url
            }
            
        except Exception as e:
            logger.error(f"Vision分析失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def save_result_to_storage(self, result_data: Dict[str, Any], s3_key: str) -> str:
        """保存分析结果到双重存储"""
        try:
            if not self.storage_service:
                raise Exception("存储服务不可用")
            
            # 使用双重存储上传
            upload_result = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=s3_key,
                content_type='application/json'
            )
            
            if upload_result.get("success"):
                logger.info(f"✅ Vision分析结果保存成功: {upload_result.get('final_url')}")
                return upload_result.get("final_url")
            else:
                raise Exception(f"存储上传失败: {upload_result.get('error')}")
                
        except Exception as e:
            logger.error(f"保存结果到存储失败: {e}")
            raise
    
    def compare_with_ocr_result(self, vision_result: Dict[str, Any], ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """对比Vision分析结果与OCR结果"""
        try:
            comparison = {
                'comparison_timestamp': datetime.now().isoformat(),
                'vision_summary': self._extract_summary(vision_result),
                'ocr_summary': self._extract_summary(ocr_result),
                'differences': self._find_differences(vision_result, ocr_result),
                'accuracy_assessment': self._assess_accuracy(vision_result, ocr_result)
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"结果对比失败: {e}")
            return {
                'error': str(e),
                'comparison_timestamp': datetime.now().isoformat()
            }
    
    def _extract_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """提取结果摘要"""
        summary = {
            'total_components': 0,
            'component_types': [],
            'method': 'unknown'
        }
        
        try:
            if 'results' in result:  # Vision结果
                # 取第一个成功的模型结果
                for model_name, model_result in result['results'].items():
                    if model_result.get('status') == 'success':
                        data = model_result.get('data', {})
                        components = data.get('components', [])
                        summary['total_components'] = len(components)
                        summary['component_types'] = list(set([c.get('component_type', '') for c in components]))
                        summary['method'] = data.get('analysis_method', model_name)
                        break
            elif 'qto_analysis' in result:  # OCR结果
                components = result['qto_analysis'].get('qto_data', {}).get('components', [])
                summary['total_components'] = len(components)
                summary['component_types'] = list(set([c.get('component_type', '') for c in components]))
                summary['method'] = 'paddleocr_ai_analysis'
            
        except Exception as e:
            logger.error(f"提取摘要失败: {e}")
            
        return summary
    
    def _find_differences(self, vision_result: Dict[str, Any], ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """找出两个结果的差异"""
        differences = {
            'component_count_diff': 0,
            'missing_in_vision': [],
            'missing_in_ocr': [],
            'dimension_differences': []
        }
        
        try:
            # 提取构件列表
            vision_components = self._get_components_from_result(vision_result)
            ocr_components = self._get_components_from_result(ocr_result)
            
            differences['component_count_diff'] = len(vision_components) - len(ocr_components)
            
            # 找出Vision中有但OCR中没有的构件
            vision_ids = set([c.get('component_id', '') for c in vision_components])
            ocr_ids = set([c.get('component_id', '') for c in ocr_components])
            
            differences['missing_in_ocr'] = list(vision_ids - ocr_ids)
            differences['missing_in_vision'] = list(ocr_ids - vision_ids)
            
        except Exception as e:
            logger.error(f"查找差异失败: {e}")
            
        return differences
    
    def _get_components_from_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从结果中提取构件列表"""
        try:
            if 'results' in result:  # Vision结果
                for model_name, model_result in result['results'].items():
                    if model_result.get('status') == 'success':
                        return model_result.get('data', {}).get('components', [])
            elif 'qto_analysis' in result:  # OCR结果
                return result['qto_analysis'].get('qto_data', {}).get('components', [])
        except Exception as e:
            logger.error(f"提取构件列表失败: {e}")
            
        return []
    
    def _assess_accuracy(self, vision_result: Dict[str, Any], ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """评估准确性"""
        assessment = {
            'vision_confidence': 'unknown',
            'ocr_confidence': 'unknown',
            'consistency_score': 0.0,
            'recommendation': 'unknown'
        }
        
        try:
            vision_components = self._get_components_from_result(vision_result)
            ocr_components = self._get_components_from_result(ocr_result)
            
            # 计算一致性分数（基于构件数量和ID匹配）
            if vision_components and ocr_components:
                vision_ids = set([c.get('component_id', '') for c in vision_components])
                ocr_ids = set([c.get('component_id', '') for c in ocr_components])
                
                common_ids = vision_ids & ocr_ids
                total_unique_ids = vision_ids | ocr_ids
                
                if total_unique_ids:
                    assessment['consistency_score'] = len(common_ids) / len(total_unique_ids)
                
                # 生成建议
                if assessment['consistency_score'] > 0.8:
                    assessment['recommendation'] = '两种方法结果高度一致，可信度高'
                elif assessment['consistency_score'] > 0.6:
                    assessment['recommendation'] = '两种方法结果基本一致，建议人工核查差异部分'
                else:
                    assessment['recommendation'] = '两种方法结果差异较大，建议详细核查'
            
        except Exception as e:
            logger.error(f"准确性评估失败: {e}")
            
        return assessment 