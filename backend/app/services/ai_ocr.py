import os
import base64
import requests
import json
import time
from typing import Dict, Any, Optional
from PIL import Image
import io
from ..config.model_config import ModelConfig

class AIVisionOCR:
    """
    大模型视觉OCR服务
    支持多个AI视觉API进行建筑图纸文字识别
    """
    
    def __init__(self):
        # API配置（从环境变量读取）
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.claude_api_key = os.getenv("CLAUDE_API_KEY") 
        self.baidu_api_key = os.getenv("BAIDU_API_KEY")
        self.baidu_secret_key = os.getenv("BAIDU_SECRET_KEY")
        self.qwen_api_key = os.getenv("QWEN_API_KEY")
        
    def extract_text_with_ai(self, image_path: str, provider: str = "auto") -> Dict[str, Any]:
        """
        使用AI大模型提取图像中的文字
        
        Args:
            image_path: 图像文件路径
            provider: AI服务提供商 ("openai", "claude", "baidu", "qwen", "auto")
            
        Returns:
            识别结果字典
        """
        try:
            print(f"[AI OCR] 开始使用{provider}模型识别: {image_path}")
            
            # 预处理图像
            processed_image = self._preprocess_image(image_path)
            
            # 根据provider选择服务
            if provider == "auto":
                # 自动选择可用的服务
                return self._auto_select_provider(processed_image)
            elif provider == "openai":
                return self._openai_vision(processed_image)
            elif provider == "claude":
                return self._claude_vision(processed_image)
            elif provider == "baidu":
                return self._baidu_vision(processed_image)
            elif provider == "qwen":
                return self._qwen_vision(processed_image)
            else:
                return {"error": f"不支持的AI服务提供商: {provider}"}
                
        except Exception as e:
            print(f"[AI OCR] 处理失败: {str(e)}")
            return {"error": str(e)}
    
    def _preprocess_image(self, image_path: str) -> str:
        """预处理图像并转换为base64"""
        try:
            # 打开图像
            with Image.open(image_path) as img:
                # 转换为RGB模式
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 如果图像太大，适当缩放以节省API成本
                max_size = 2048
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # 转换为base64
                buffer = io.BytesIO()
                img.save(buffer, format='PNG', quality=95)
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                return img_base64
                
        except Exception as e:
            raise ValueError(f"图像预处理失败: {str(e)}")
    
    def _auto_select_provider(self, image_base64: str) -> Dict[str, Any]:
        """自动选择可用的AI服务提供商"""
        providers = []
        
        if self.openai_api_key:
            providers.append("openai")
        if self.claude_api_key:
            providers.append("claude")
        if self.baidu_api_key and self.baidu_secret_key:
            providers.append("baidu")
        if self.qwen_api_key:
            providers.append("qwen")
        
        if not providers:
            return {"error": "没有配置可用的AI服务API密钥"}
        
        # 按优先级尝试
        for provider in providers:
            try:
                if provider == "openai":
                    result = self._openai_vision(image_base64)
                elif provider == "claude":
                    result = self._claude_vision(image_base64)
                elif provider == "baidu":
                    result = self._baidu_vision(image_base64)
                elif provider == "qwen":
                    result = self._qwen_vision(image_base64)
                
                if "error" not in result:
                    result["provider"] = provider
                    return result
                    
            except Exception as e:
                print(f"[AI OCR] {provider}服务失败: {str(e)}")
                continue
        
        return {"error": "所有AI服务都不可用"}
    
    def _openai_vision(self, image_base64: str) -> Dict[str, Any]:
        """OpenAI GPT-4V识别"""
        if not self.openai_api_key:
            return {"error": "未配置OpenAI API密钥"}
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            payload = {
                "model": ModelConfig.get_vision_model(),  # 使用配置文件中的视觉模型
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """请仔细识别这张建筑图纸中的所有文字信息，包括：
1. 尺寸标注（如 4500、200x300 等）
2. 构件名称（如 Wall A-1、Column C1 等）  
3. 房间名称（如 Living Room、Kitchen 等）
4. 技术说明和备注
5. 图纸标题和比例

请以结构化的方式输出识别结果，保持原有的格式和层次。
请确保数字和尺寸的准确性，这对工程量计算很重要。"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1  # 低温度确保准确性
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]
                return {
                    "text": text,
                    "provider": "openai",
                    "model": ModelConfig.get_vision_model(),
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0)
                }
            else:
                return {"error": f"OpenAI API错误: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"OpenAI Vision调用失败: {str(e)}"}
    
    def _claude_vision(self, image_base64: str) -> Dict[str, Any]:
        """Claude-3 Vision识别"""
        if not self.claude_api_key:
            return {"error": "未配置Claude API密钥"}
        
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.claude_api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 2000,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """请仔细识别这张建筑图纸中的所有文字信息，包括：
1. 尺寸标注（如 4500、200x300 等）
2. 构件名称（如 Wall A-1、Column C1 等）  
3. 房间名称（如 Living Room、Kitchen 等）
4. 技术说明和备注
5. 图纸标题和比例

请以结构化的方式输出识别结果，保持原有的格式和层次。
请确保数字和尺寸的准确性，这对工程量计算很重要。"""
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["content"][0]["text"]
                return {
                    "text": text,
                    "provider": "claude",
                    "model": "claude-3-sonnet",
                    "tokens_used": result.get("usage", {}).get("input_tokens", 0) + result.get("usage", {}).get("output_tokens", 0)
                }
            else:
                return {"error": f"Claude API错误: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"Claude Vision调用失败: {str(e)}"}
    
    def _baidu_vision(self, image_base64: str) -> Dict[str, Any]:
        """百度文心一言视觉识别"""
        if not self.baidu_api_key or not self.baidu_secret_key:
            return {"error": "未配置百度API密钥"}
        
        try:
            # 获取access_token
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            token_params = {
                "grant_type": "client_credentials",
                "client_id": self.baidu_api_key,
                "client_secret": self.baidu_secret_key
            }
            
            token_response = requests.post(token_url, params=token_params, timeout=30)
            if token_response.status_code != 200:
                return {"error": f"获取百度access_token失败: {token_response.text}"}
            
            access_token = token_response.json().get("access_token")
            if not access_token:
                return {"error": "百度access_token获取失败"}
            
            # 调用视觉理解API
            api_url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/yi_34b_chat?access_token={access_token}"
            
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """请仔细识别这张建筑图纸中的所有文字信息，包括尺寸标注、构件名称、房间名称、技术说明等。请以结构化的方式输出，确保数字和尺寸的准确性。"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.1,
                "top_p": 0.8,
                "penalty_score": 1.0
            }
            
            response = requests.post(api_url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("result", "")
                return {
                    "text": text,
                    "provider": "baidu",
                    "model": "wenxin",
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0)
                }
            else:
                return {"error": f"百度API错误: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"百度Vision调用失败: {str(e)}"}
    
    def _qwen_vision(self, image_base64: str) -> Dict[str, Any]:
        """通义千问视觉识别"""
        if not self.qwen_api_key:
            return {"error": "未配置通义千问API密钥"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.qwen_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "qwen-vl-plus",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": "请仔细识别这张建筑图纸中的所有文字信息，包括尺寸标注、构件名称、房间名称、技术说明等。请以结构化的方式输出，确保数字和尺寸的准确性。"
                                },
                                {
                                    "image": f"data:image/png;base64,{image_base64}"
                                }
                            ]
                        }
                    ]
                },
                "parameters": {
                    "result_format": "message",
                    "max_tokens": 2000,
                    "temperature": 0.1
                }
            }
            
            response = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["output"]["choices"][0]["message"]["content"]
                return {
                    "text": text,
                    "provider": "qwen",
                    "model": "qwen-vl-plus",
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0)
                }
            else:
                return {"error": f"通义千问API错误: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"通义千问Vision调用失败: {str(e)}"}

# 全局实例
ai_ocr = AIVisionOCR()

def extract_text_with_ai(image_path: str, provider: str = "auto") -> Dict[str, Any]:
    """
    便捷函数：使用AI大模型提取图像文字
    
    Args:
        image_path: 图像文件路径
        provider: AI服务提供商
        
    Returns:
        识别结果
    """
    return ai_ocr.extract_text_with_ai(image_path, provider) 