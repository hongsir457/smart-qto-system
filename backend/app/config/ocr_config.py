"""
OCR配置文件
配置AI OCR为优先选择
"""

import os

class OCRConfig:
    """OCR服务配置"""
    
    # 默认OCR模式
    DEFAULT_USE_AI = True  # 优先使用AI OCR
    DEFAULT_AI_PROVIDER = "auto"  # 自动选择最佳AI服务商
    
    # AI服务商优先级（按性能排序）
    AI_PROVIDER_PRIORITY = [
        "openai",      # GPT-4o - 最高准确率
        "claude",      # Claude-3 - 结构化理解好  
        "qwen",        # 通义千问 - 响应快，中文支持好
        "baidu"        # 百度文心 - 成本低，中文识别好
    ]
    
    # AI OCR配置
    AI_OCR_CONFIG = {
        "max_retries": 3,           # 最大重试次数
        "timeout": 30,              # 超时时间（秒）
        "fallback_to_traditional": True,  # AI失败时降级到传统OCR
    }
    
    # 传统OCR配置
    TRADITIONAL_OCR_CONFIG = {
        "language": "chi_sim+eng",   # 中英文混合
        "oem": 3,                    # OCR引擎模式
        "psm": 6,                    # 页面分割模式
        "preserve_interword_spaces": True,
    }
    
    # 质量阈值
    QUALITY_THRESHOLDS = {
        "min_text_length": 10,       # 最小文本长度
        "min_confidence": 60,        # 最小置信度
        "keyword_coverage": 0.7,     # 关键词覆盖率
    }
    
    @classmethod
    def get_ai_provider(cls):
        """获取当前可用的AI服务商"""
        for provider in cls.AI_PROVIDER_PRIORITY:
            if cls._is_provider_available(provider):
                return provider
        return None
    
    @classmethod
    def _is_provider_available(cls, provider: str) -> bool:
        """检查AI服务商是否可用"""
        api_keys = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "claude": os.getenv("CLAUDE_API_KEY"),
            "baidu": os.getenv("BAIDU_API_KEY"),
            "qwen": os.getenv("QWEN_API_KEY"),
        }
        
        if provider == "baidu":
            # 百度需要两个密钥
            return bool(api_keys["baidu"] and os.getenv("BAIDU_SECRET_KEY"))
        
        return bool(api_keys.get(provider))
    
    @classmethod
    def get_ocr_strategy(cls):
        """获取当前OCR策略"""
        available_provider = cls.get_ai_provider()
        
        if available_provider and cls.DEFAULT_USE_AI:
            return {
                "mode": "ai_first",
                "ai_provider": available_provider,
                "fallback": "traditional" if cls.AI_OCR_CONFIG["fallback_to_traditional"] else None
            }
        else:
            return {
                "mode": "traditional_only",
                "ai_provider": None,
                "fallback": None
            }
    
    @classmethod
    def print_current_config(cls):
        """打印当前配置状态"""
        strategy = cls.get_ocr_strategy()
        
        print("🔧 当前OCR配置:")
        print(f"   - 模式: {strategy['mode']}")
        print(f"   - AI服务商: {strategy['ai_provider'] or 'None'}")
        print(f"   - 降级策略: {strategy['fallback'] or 'None'}")
        
        print("\n📋 可用的AI服务:")
        for provider in cls.AI_PROVIDER_PRIORITY:
            status = "✅" if cls._is_provider_available(provider) else "❌"
            print(f"   - {provider}: {status}") 