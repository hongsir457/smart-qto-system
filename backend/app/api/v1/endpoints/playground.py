from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional, Dict
from openai import AsyncOpenAI
import json
from datetime import datetime
import asyncio
from pydantic import BaseModel, Field

from ....api import deps
from ....core.config import settings
from ....models.user import User
from ....database import get_db
from ....config.model_config import ModelConfig

router = APIRouter()

# Pydantic 模型
class PlaygroundMessage(BaseModel):
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息内容")

class PlaygroundRequest(BaseModel):
    messages: List[PlaygroundMessage] = Field(..., description="对话消息列表")
    model: str = Field(default=ModelConfig.get_default_model(), description="使用的模型")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=1000, ge=1, le=4000, description="最大令牌数")
    top_p: float = Field(default=1.0, ge=0, le=1, description="Top P 参数")
    frequency_penalty: float = Field(default=0.0, ge=-2, le=2, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, ge=-2, le=2, description="存在惩罚")
    stream: bool = Field(default=False, description="是否启用流式响应")

class PlaygroundResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, Any]
    finish_reason: Optional[str] = None

class PlaygroundPreset(BaseModel):
    name: str = Field(..., description="预设名称")
    description: str = Field(..., description="预设描述")
    system_message: str = Field(..., description="系统消息")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=1000, description="最大令牌数")

class PlaygroundPresetCreate(PlaygroundPreset):
    pass

class PlaygroundPresetResponse(PlaygroundPreset):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

# 预设的系统消息模板
PRESET_TEMPLATES = [
    {
        "name": "智能助手",
        "description": "通用的智能助手，可以回答各种问题",
        "system_message": "你是一个有用的AI助手，请用中文回答用户的问题。回答要准确、简洁、有帮助。",
        "temperature": 0.7,
        "max_tokens": 1000
    },
    {
        "name": "工程量计算专家",
        "description": "专门用于工程量计算和建筑图纸分析",
        "system_message": "你是一个专业的工程量计算专家，擅长分析建筑图纸和计算工程量。请提供准确的专业建议。",
        "temperature": 0.3,
        "max_tokens": 1500
    },
    {
        "name": "代码生成器",
        "description": "专门用于生成和解释代码",
        "system_message": "你是一个专业的程序员，可以生成高质量的代码并提供详细的解释。请使用最佳实践。",
        "temperature": 0.2,
        "max_tokens": 2000
    },
    {
        "name": "创意写作助手",
        "description": "用于创意写作和内容生成",
        "system_message": "你是一个富有创意的写作助手，可以帮助用户创作各种类型的文本内容。",
        "temperature": 0.9,
        "max_tokens": 1500
    }
]

@router.post("/chat")
async def playground_chat(
    *,
    request: PlaygroundRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Playground 聊天接口
    """
    try:
        # 检查API密钥是否配置
        if not settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API 密钥未配置，请联系管理员"
            )
        
        # 创建 OpenAI 客户端
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # 准备消息
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # 调用 OpenAI API
        response = await client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stream=request.stream,
            user=str(current_user.id)
        )
        
        # 转换响应格式以匹配前端期望
        return {
            "id": response.id,
            "object": response.object,
            "created": response.created,
            "model": response.model,
            "choices": [
                {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content
                    },
                    "finish_reason": choice.finish_reason
                }
                for choice in response.choices
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OpenAI API 认证失败，请检查 API 密钥配置"
            )
        elif "rate limit" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API 请求频率超限，请稍后再试"
            )
        elif "invalid request" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"请求参数错误: {error_msg}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"服务器错误: {error_msg}"
            )

@router.get("/models")
async def get_available_models(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取可用的模型列表
    """
    try:
        if not settings.OPENAI_API_KEY:
            # 如果没有API密钥，返回配置文件中的模型列表
            return {
                "models": [
                    {"id": model, "object": "model"} 
                    for model in ModelConfig.get_supported_models()
                ],
                "recommended": ModelConfig.get_recommended_models()
            }
        
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        models_response = await client.models.list()
        
        # 过滤出聊天模型
        chat_models = [
            {"id": model.id, "object": model.object}
            for model in models_response.data
            if any(name in model.id for name in ['gpt', 'chatgpt'])
        ]
        
        return {
            "models": sorted(chat_models, key=lambda x: x["id"]),
            "recommended": ModelConfig.get_recommended_models()
        }
        
    except Exception as e:
        # 如果无法获取模型列表，返回配置文件中的默认列表
        return {
            "models": [
                {"id": model, "object": "model"} 
                for model in ModelConfig.get_supported_models()
            ],
            "recommended": ModelConfig.get_recommended_models()
        }

@router.get("/presets")
async def get_presets(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取预设模板列表
    """
    return {
        "presets": PRESET_TEMPLATES,
        "message": "预设模板列表"
    }

@router.post("/validate")
async def validate_api_key(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    验证 OpenAI API 密钥是否有效
    """
    try:
        if not settings.OPENAI_API_KEY:
            return {
                "valid": False,
                "message": "API 密钥未配置",
                "model_accessible": False
            }
        
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # 发送一个简单的请求来验证 API 密钥
        response = await client.chat.completions.create(
            model=ModelConfig.get_default_model(),
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        
        return {
            "valid": True,
            "message": "API 密钥验证成功",
            "model_accessible": True
        }
        
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            return {
                "valid": False,
                "message": "API 密钥无效或未配置",
                "model_accessible": False
            }
        elif "permission" in error_msg.lower():
            return {
                "valid": True,
                "message": "API 密钥有效，但没有访问此模型的权限",
                "model_accessible": False
            }
        else:
            return {
                "valid": False,
                "message": f"验证失败: {error_msg}",
                "model_accessible": False
            }

@router.get("/usage")
async def get_usage_stats(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取 API 使用统计（这需要根据实际的计费 API 来实现）
    """
    # 这里返回模拟数据，实际项目中需要集成 OpenAI 的计费 API
    return {
        "current_month": {
            "requests": 1250,
            "tokens": 45000,
            "cost": 12.50
        },
        "limits": {
            "max_requests_per_month": 10000,
            "max_tokens_per_month": 500000,
            "max_cost_per_month": 100.00
        },
        "message": "使用统计数据（模拟数据）"
    }

@router.post("/stream")
async def playground_stream_chat(
    *,
    request: PlaygroundRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    流式聊天接口
    """
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate_stream():
        try:
            if not settings.OPENAI_API_KEY:
                error_data = {
                    "error": {
                        "message": "OpenAI API 密钥未配置",
                        "type": "configuration_error"
                    }
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                return
            
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            
            stream = await client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
                user=str(current_user.id)
            )
            
            async for chunk in stream:
                yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                
        except Exception as e:
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "server_error"
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    ) 