"""
图纸处理器配置模块
从原drawings.py中提取的配置类
"""

import logging

logger = logging.getLogger(__name__)

class LLMConfig:
    """大语言模型配置"""
    def __init__(self, provider="openai", model_name="gpt-4-vision-preview", max_tokens=4096, temperature=0.1, timeout=60):
        self.provider = provider
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

class ProcessingConfig:
    """图纸处理配置"""
    def __init__(self, enable_stage_two=True, store_intermediate_results=True, store_final_png=True, llm_config=None, max_image_size=2048):
        self.enable_stage_two = enable_stage_two
        self.store_intermediate_results = store_intermediate_results
        self.store_final_png = store_final_png
        self.llm_config = llm_config or LLMConfig()
        self.max_image_size = max_image_size

def get_default_processing_config() -> ProcessingConfig:
    """获取默认处理配置"""
    # 配置大模型参数
    llm_config = LLMConfig(
        provider="openai",
        model_name="gpt-4-vision-preview",
        max_tokens=4096,
        temperature=0.1,
        timeout=60
    )
    
    # 配置处理器
    return ProcessingConfig(
        enable_stage_two=True,
        store_intermediate_results=True,
        store_final_png=True,
        llm_config=llm_config,
        max_image_size=2048
    ) 