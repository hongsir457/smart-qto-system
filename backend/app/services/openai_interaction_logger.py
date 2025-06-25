#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI交互记录服务
记录所有OpenAI API调用的详细信息并存储到Sealos
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import io

from .s3_service import S3Service
from app.services.dual_storage_service import DualStorageService

logger = logging.getLogger(__name__)

class OpenAIInteractionLogger:
    """OpenAI交互记录器"""
    
    def __init__(self, storage_service: DualStorageService):
        """
        初始化交互记录器
        Args:
            storage_service: 已初始化的双重存储服务实例
        """
        if storage_service and storage_service.is_available():
            self.storage_service = storage_service
            logger.info("✅ OpenAIInteractionLogger initialized with provided storage service.")
        else:
            self.storage_service = None
            logger.error("❌ OpenAIInteractionLogger initialization failed: Invalid or unavailable storage service provided.")
    
    async def save_interaction_async(self, 
                                   interaction_record: Dict[str, Any], 
                                   drawing_id: str = "unknown") -> Dict[str, Any]:
        """
        异步保存AI交互记录
        
        Args:
            interaction_record: 交互记录数据
            drawing_id: 图纸ID
            
        Returns:
            保存结果
        """
        if not self.storage_service:
            logger.warning("存储服务不可用，跳过交互记录保存")
            return {"success": False, "error": "Storage service not available"}
        
        try:
            # 生成唯一的交互记录ID
            interaction_id = str(uuid.uuid4())
            
            # 添加元数据
            enhanced_record = {
                **interaction_record,
                "interaction_id": interaction_id,
                "saved_timestamp": time.time(),
                "format_version": "1.0",
                "logger_type": "OpenAIInteractionLogger"
            }
            
            # 构建存储键
            s3_key = f"ai_interactions/{drawing_id}/{interaction_id}.json"
            
            # 保存到存储
            save_result = self.storage_service.upload_content_sync(
                content=json.dumps(enhanced_record, ensure_ascii=False, indent=2),
                s3_key=s3_key,
                content_type="application/json"
            )
            
            if save_result.get("success"):
                logger.info(f"✅ AI交互记录已保存: {s3_key}")
                return {
                    "success": True,
                    "s3_url": save_result.get("final_url"),
                    "s3_key": s3_key,
                    "interaction_id": interaction_id
                }
            else:
                logger.error(f"❌ AI交互记录保存失败: {save_result.get('error')}")
                return {"success": False, "error": save_result.get('error')}
                
        except Exception as e:
            logger.error(f"❌ 保存AI交互记录异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def save_interaction_sync(self, 
                            interaction_record: Dict[str, Any], 
                            drawing_id: str = "unknown") -> Dict[str, Any]:
        """
        同步保存AI交互记录
        
        Args:
            interaction_record: 交互记录数据
            drawing_id: 图纸ID
            
        Returns:
            保存结果
        """
        # 这是同步版本，主要用于不支持async的场景
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.save_interaction_async(interaction_record, drawing_id)
            )
        except Exception as e:
            logger.error(f"❌ 同步保存AI交互记录异常: {e}")
            return {"success": False, "error": str(e)}
    
    def log_api_call_start(self, model: str, messages: list, parameters: dict) -> str:
        """记录API调用开始"""
        call_id = str(uuid.uuid4())
        logger.info(f"🌐 API调用开始: {call_id} (模型: {model})")
        return call_id
    
    def log_api_call_success(self, call_id: str, response_content: str, usage_info: dict = None):
        """记录API调用成功"""
        logger.info(f"✅ API调用成功: {call_id}")
    
    def log_api_call_error(self, call_id: str, error_message: str, error_type: str = None):
        """记录API调用错误"""
        logger.error(f"❌ API调用失败: {call_id} - {error_message}")
    
    def start_session(self, 
                     task_id: str, 
                     drawing_id: int, 
                     session_type: str = "vision_analysis") -> str:
        """
        开始一个新的交互会话
        Args:
            task_id: 任务ID
            drawing_id: 图纸ID  
            session_type: 会话类型 (vision_analysis, text_analysis, etc.)
        Returns:
            session_id: 会话唯一标识
        """
        self.session_id = f"{session_type}_{task_id}_{int(time.time())}"
        
        self.interaction_data = {
            "session_info": {
                "session_id": self.session_id,
                "task_id": task_id,
                "drawing_id": drawing_id,
                "session_type": session_type,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "status": "started"
            },
            "api_calls": [],
            "metadata": {
                "total_api_calls": 0,
                "success_calls": 0,
                "failed_calls": 0,
                "total_cost_estimate": 0.0,
                "total_tokens_used": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0
            },
            "images": [],
            "results": {}
        }
        
        logger.info(f"🔄 OpenAI交互会话开始: {self.session_id}")
        return self.session_id
    
    def log_image_processing(self, image_paths: List[str], encoded_sizes: List[int]):
        """记录图像处理信息"""
        if not self.session_id:
            logger.warning("⚠️ 会话未开始，无法记录图像信息")
            return
            
        for i, (path, size) in enumerate(zip(image_paths, encoded_sizes)):
            image_info = {
                "index": i + 1,
                "original_path": path,
                "filename": Path(path).name,
                "encoded_size_bytes": size,
                "processed_time": datetime.now().isoformat()
            }
            self.interaction_data["images"].append(image_info)
            
        self.interaction_data["metadata"]["images_processed"] = len(image_paths)
        logger.info(f"📸 记录图像处理: {len(image_paths)} 张图片")
    
    def log_final_result(self, 
                        success: bool,
                        qto_data: Optional[Dict] = None,
                        error_info: Optional[Dict] = None):
        """
        记录最终分析结果
        Args:
            success: 是否成功
            qto_data: QTO分析结果
            error_info: 错误信息
        """
        if not self.session_id:
            return
            
        self.interaction_data["results"] = {
            "success": success,
            "qto_data": qto_data,
            "error_info": error_info,
            "result_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"📊 记录最终结果: {'成功' if success else '失败'}")
    
    def end_session_and_save(self) -> Optional[str]:
        """
        结束会话并保存到Sealos
        Returns:
            保存的文件URL
        """
        if not self.session_id:
            logger.warning("⚠️ 没有活跃的会话")
            return None
            
        # 更新会话信息
        self.interaction_data["session_info"]["end_time"] = datetime.now().isoformat()
        self.interaction_data["session_info"]["status"] = "completed"
        
        # 计算总时长
        start_time = datetime.fromisoformat(self.interaction_data["session_info"]["start_time"])
        end_time = datetime.fromisoformat(self.interaction_data["session_info"]["end_time"])
        total_duration = (end_time - start_time).total_seconds()
        self.interaction_data["session_info"]["total_duration_seconds"] = total_duration
        
        # 生成完整记录JSON
        interaction_json = json.dumps(self.interaction_data, ensure_ascii=False, indent=2)
        
        try:
            # 保存到Sealos
            filename = f"openai_interaction_{self.session_id}.json"
            folder = f"openai_logs/{self.interaction_data['session_info']['drawing_id']}"
            
            result = self.storage_service.upload_txt_content(
                content=interaction_json,
                file_name=filename,
                folder=folder
            )
            
            logger.info(f"💾 OpenAI交互记录已保存到Sealos: {result.get('s3_url')}")
            
            # 生成摘要日志
            self._log_session_summary()
            
            # 清理会话数据
            saved_url = result.get('s3_url')
            self.session_id = None
            self.interaction_data = {}
            
            return saved_url
            
        except Exception as e:
            logger.error(f"❌ 保存OpenAI交互记录失败: {e}")
            return None
    
    def _safe_process_messages(self, messages: List[Dict]) -> List[Dict]:
        """安全处理消息内容，避免图片数据过大"""
        safe_messages = []
        
        for msg in messages:
            safe_msg = {
                "role": msg.get("role"),
                "content": []
            }
            
            content = msg.get("content", [])
            if isinstance(content, str):
                safe_msg["content"] = content
            elif isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        safe_msg["content"].append(item)
                    elif item.get("type") == "image_url":
                        # 只记录图片元信息，不保存完整base64数据
                        image_url = item.get("image_url", {})
                        url = image_url.get("url", "")
                        safe_msg["content"].append({
                            "type": "image_url",
                            "image_url": {
                                "detail": image_url.get("detail"),
                                "url_type": "base64_image" if url.startswith("data:image") else "url",
                                "estimated_size_kb": len(url) // 1024 if url else 0
                            }
                        })
            
            safe_messages.append(safe_msg)
        
        return safe_messages
    
    def _find_call_record(self, call_id: str) -> Optional[Dict]:
        """
        查找API调用记录
        
        增强版本：支持批次任务的API调用记录查找
        - 优先精确匹配call_id
        - 如果找不到，尝试按调用顺序匹配（用于批次任务）
        """
        # 1. 优先精确匹配
        for call in self.interaction_data.get("api_calls", []):
            if call.get("call_id") == call_id:
                return call
        
        # 2. 🔧 修复：对于批次任务，尝试按时间戳匹配
        if "_batch_" in call_id:
            # 提取call_id中的时间戳部分
            try:
                # call_id格式: call_{attempt}_{timestamp}
                parts = call_id.split("_")
                if len(parts) >= 3:
                    attempt_num = int(parts[1])
                    target_timestamp = parts[2]
                    
                    # 查找相近时间戳的调用记录
                    for call in self.interaction_data.get("api_calls", []):
                        existing_call_id = call.get("call_id", "")
                        if existing_call_id:
                            existing_parts = existing_call_id.split("_")
                            if len(existing_parts) >= 3:
                                existing_attempt = int(existing_parts[1])
                                existing_timestamp = existing_parts[2]
                                
                                # 尝试时间戳范围匹配（允许±2秒的误差）
                                if (attempt_num == existing_attempt and 
                                    abs(int(target_timestamp) - int(existing_timestamp)) <= 2):
                                    logger.info(f"🔄 批次任务API调用记录匹配: {call_id} -> {existing_call_id}")
                                    return call
                                    
            except (ValueError, IndexError) as e:
                logger.debug(f"解析call_id时间戳失败: {call_id}, 错误: {e}")
        
        # 3. 🔧 修复：如果仍然找不到，尝试按调用顺序匹配
        api_calls = self.interaction_data.get("api_calls", [])
        if api_calls:
            try:
                # 提取call_id中的尝试次数
                parts = call_id.split("_")
                if len(parts) >= 2:
                    attempt_num = int(parts[1])
                    
                    # 如果尝试次数在合理范围内，返回对应索引的调用记录
                    if 1 <= attempt_num <= len(api_calls):
                        matched_call = api_calls[attempt_num - 1]
                        logger.info(f"🔄 按调用顺序匹配API记录: {call_id} -> 第{attempt_num}次调用")
                        return matched_call
                        
            except (ValueError, IndexError):
                pass
        
        # 4. 最后尝试：找到最近的未完成调用记录
        for call in reversed(self.interaction_data.get("api_calls", [])):
            if call.get("status") == "started":
                logger.info(f"🔄 匹配最近的未完成调用: {call_id} -> {call.get('call_id')}")
                return call
        
        logger.warning(f"⚠️ 未找到API调用记录: {call_id} (尝试了多种匹配策略)")
        return None
    
    def _log_session_summary(self):
        """记录会话摘要信息"""
        metadata = self.interaction_data["metadata"]
        session_info = self.interaction_data["session_info"]
        
        logger.info("📋 OpenAI交互会话摘要:")
        logger.info(f"   会话ID: {self.session_id}")
        logger.info(f"   持续时间: {session_info.get('total_duration_seconds', 0):.2f} 秒")
        logger.info(f"   API调用总数: {metadata.get('total_api_calls', 0)}")
        logger.info(f"   成功调用: {metadata.get('success_calls', 0)}")
        logger.info(f"   失败调用: {metadata.get('failed_calls', 0)}")
        logger.info(f"   处理图片: {metadata.get('images_processed', 0)} 张")
        logger.info(f"   使用Token: {metadata.get('total_tokens_used', 0)}")
        logger.info(f"   估算费用: ${metadata.get('total_cost_estimate', 0.0):.6f}")
        
        # 最终结果
        results = self.interaction_data.get("results", {})
        if results.get("success"):
            logger.info("   分析结果: ✅ 成功")
        else:
            logger.info("   分析结果: ❌ 失败")
            if results.get("error_info"):
                logger.info(f"   错误信息: {results['error_info'].get('message', '未知错误')}")

        summary = {
            "session_id": self.session_id,
            "duration": self.interaction_data["session_info"].get("total_duration_seconds"),
            "total_calls": self.interaction_data["metadata"].get("total_api_calls"),
            "successful_calls": self.interaction_data["metadata"].get("success_calls"),
            "total_tokens": self.interaction_data["metadata"].get("total_tokens_used")
        }
        logger.info(f"📝 会话摘要: {summary}")

class DummyInteractionLogger:
    """一个备用的、空操作的交互记录器，在主记录器初始化失败时使用"""

    def __init__(self, *args, **kwargs):
        logger.warning("⚠️ 使用备用DummyInteractionLogger，所有交互记录将不会被保存。")

    def start_session(self, *args, **kwargs) -> str:
        logger.debug("DummyInteractionLogger: start_session called")
        # 返回一个唯一的会话ID，以防调用代码需要它
        return f"dummy_session_{uuid.uuid4()}"

    def log_api_call(self, *args, **kwargs):
        logger.debug("DummyInteractionLogger: log_api_call called")
        pass

    def log_image_processing(self, *args, **kwargs):
        logger.debug("DummyInteractionLogger: log_image_processing called")
        pass

    def log_final_result(self, *args, **kwargs):
        logger.debug("DummyInteractionLogger: log_final_result called")
        pass

    def end_session_and_save(self, *args, **kwargs) -> Optional[str]:
        logger.debug("DummyInteractionLogger: end_session_and_save called")
        return None

    def __getattr__(self, name):
        """捕获所有其他未实现的方法调用，以防止AttributeError"""
        def method(*args, **kwargs):
            logger.debug(f"DummyInteractionLogger: called non-existent method '{name}'")
            return None
        return method 