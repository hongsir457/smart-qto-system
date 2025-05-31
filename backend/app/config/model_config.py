"""
AI 模型配置文件
集中管理所有 AI 模型的配置
"""

import os
from typing import Dict, List

class ModelConfig:
    """AI 模型配置类"""
    
    # OpenAI 模型配置
    OPENAI_DEFAULT_MODEL = "gpt-4o-2024-11-20"
    OPENAI_VISION_MODEL = "gpt-4o-2024-11-20"
    OPENAI_FALLBACK_MODEL = "chatgpt-4o-latest"
    
    # 支持的 OpenAI 模型列表（按优先级排序）
    OPENAI_SUPPORTED_MODELS = [
        "gpt-4o-2024-11-20",
        "chatgpt-4o-latest", 
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-05-13",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4"
    ]
    
    # 推荐模型列表
    RECOMMENDED_MODELS = [
        "gpt-4o-2024-11-20",
        "chatgpt-4o-latest"
    ]
    
    # 模型参数配置
    MODEL_PARAMS = {
        "gpt-4o-2024-11-20": {
            "max_tokens": 4096,
            "temperature": 0.1,
            "top_p": 1.0,
            "supports_vision": True,
            "context_window": 128000
        },
        "chatgpt-4o-latest": {
            "max_tokens": 4096,
            "temperature": 0.1,
            "top_p": 1.0,
            "supports_vision": True,
            "context_window": 128000
        },
        "gpt-4o-mini": {
            "max_tokens": 16384,
            "temperature": 0.1,
            "top_p": 1.0,
            "supports_vision": True,
            "context_window": 128000
        }
    }
    
    @classmethod
    def get_default_model(cls) -> str:
        """获取默认模型"""
        return os.getenv("OPENAI_DEFAULT_MODEL", cls.OPENAI_DEFAULT_MODEL)
    
    @classmethod
    def get_vision_model(cls) -> str:
        """获取视觉模型"""
        return os.getenv("OPENAI_VISION_MODEL", cls.OPENAI_VISION_MODEL)
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """获取支持的模型列表"""
        return cls.OPENAI_SUPPORTED_MODELS
    
    @classmethod
    def get_recommended_models(cls) -> List[str]:
        """获取推荐模型列表"""
        return cls.RECOMMENDED_MODELS
    
    @classmethod
    def get_model_params(cls, model: str) -> Dict:
        """获取模型参数"""
        return cls.MODEL_PARAMS.get(model, cls.MODEL_PARAMS[cls.OPENAI_DEFAULT_MODEL])
    
    @classmethod
    def is_vision_supported(cls, model: str) -> bool:
        """检查模型是否支持视觉功能"""
        params = cls.get_model_params(model)
        return params.get("supports_vision", False)
    
    @classmethod
    def print_current_config(cls):
        """打印当前模型配置"""
        print("🤖 当前 AI 模型配置:")
        print(f"   - 默认模型: {cls.get_default_model()}")
        print(f"   - 视觉模型: {cls.get_vision_model()}")
        print(f"   - 推荐模型: {', '.join(cls.get_recommended_models())}")
        print(f"   - 支持的模型数量: {len(cls.get_supported_models())}") 