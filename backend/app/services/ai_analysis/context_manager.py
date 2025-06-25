#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文管理器 - 管理多轮对话的上下文和会话状态
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ContextManager:
    """
    负责管理AI分析过程中的上下文和会话状态
    """
    
    def __init__(self):
        """初始化上下文管理器"""
        self.sessions = {}  # 存储会话数据
        logger.info("✅ ContextManager initialized")
    
    def start_session(self, session_id: str, initial_data: Dict = None) -> Dict[str, Any]:
        """开始新会话"""
        try:
            session_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "messages": [],
                "context": initial_data or {},
                "step_results": {},
                "metadata": {
                    "total_steps": 0,
                    "completed_steps": 0,
                    "current_step": None
                }
            }
            
            self.sessions[session_id] = session_data
            logger.info(f"✅ 会话已启动: {session_id}")
            return {"success": True, "session_id": session_id}
            
        except Exception as e:
            logger.error(f"❌ 会话启动失败: {e}")
            return {"error": str(e)}
    
    def add_message(self, session_id: str, role: str, content: Any, step_name: str = None) -> bool:
        """向会话添加消息"""
        try:
            if session_id not in self.sessions:
                logger.warning(f"⚠️ 会话不存在: {session_id}")
                return False
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "step_name": step_name
            }
            
            self.sessions[session_id]["messages"].append(message)
            
            if step_name:
                self.sessions[session_id]["metadata"]["current_step"] = step_name
            
            logger.debug(f"📝 消息已添加到会话 {session_id}: {role}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加消息失败: {e}")
            return False
    
    def update_step_result(self, session_id: str, step_name: str, result: Dict) -> bool:
        """更新步骤结果"""
        try:
            if session_id not in self.sessions:
                logger.warning(f"⚠️ 会话不存在: {session_id}")
                return False
            
            self.sessions[session_id]["step_results"][step_name] = {
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "success": result.get("success", False)
            }
            
            # 更新元数据
            metadata = self.sessions[session_id]["metadata"]
            metadata["completed_steps"] = len(self.sessions[session_id]["step_results"])
            
            if result.get("success"):
                logger.info(f"✅ 步骤结果已更新: {session_id} - {step_name}")
            else:
                logger.warning(f"⚠️ 步骤失败: {session_id} - {step_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新步骤结果失败: {e}")
            return False
    
    def get_context_for_step(self, session_id: str, step_name: str) -> Dict[str, Any]:
        """获取特定步骤的上下文信息"""
        try:
            if session_id not in self.sessions:
                return {}
            
            session = self.sessions[session_id]
            context = {
                "session_id": session_id,
                "current_step": step_name,
                "previous_results": {},
                "conversation_history": []
            }
            
            # 获取之前步骤的结果
            for prev_step, step_data in session["step_results"].items():
                if step_data.get("success"):
                    context["previous_results"][prev_step] = step_data["result"]
            
            # 获取相关的对话历史（最近的几条消息）
            recent_messages = session["messages"][-6:]  # 最近6条消息
            context["conversation_history"] = recent_messages
            
            return context
            
        except Exception as e:
            logger.error(f"❌ 获取上下文失败: {e}")
            return {}
    
    def build_conversation_messages(self, session_id: str, max_messages: int = 10) -> List[Dict]:
        """构建用于API调用的对话消息列表"""
        try:
            if session_id not in self.sessions:
                return []
            
            messages = self.sessions[session_id]["messages"]
            
            # 取最近的消息，但确保包含系统消息
            recent_messages = []
            system_message = None
            
            # 找到最近的系统消息
            for msg in reversed(messages):
                if msg["role"] == "system":
                    system_message = msg
                    break
            
            if system_message:
                recent_messages.append(system_message)
            
            # 添加最近的用户和助手消息
            user_assistant_messages = [
                msg for msg in messages[-max_messages:] 
                if msg["role"] in ["user", "assistant"]
            ]
            recent_messages.extend(user_assistant_messages)
            
            # 转换为API格式
            api_messages = []
            for msg in recent_messages:
                api_message = {
                    "role": msg["role"],
                    "content": msg["content"]
                }
                api_messages.append(api_message)
            
            return api_messages
            
        except Exception as e:
            logger.error(f"❌ 构建对话消息失败: {e}")
            return []
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """获取会话摘要"""
        try:
            if session_id not in self.sessions:
                return {"error": "Session not found"}
            
            session = self.sessions[session_id]
            metadata = session["metadata"]
            
            summary = {
                "session_id": session_id,
                "status": session["status"],
                "created_at": session["created_at"],
                "total_messages": len(session["messages"]),
                "completed_steps": metadata["completed_steps"],
                "current_step": metadata.get("current_step"),
                "step_success_rate": self._calculate_success_rate(session["step_results"]),
                "last_activity": self._get_last_activity(session)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 获取会话摘要失败: {e}")
            return {"error": str(e)}
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """结束会话并保存结果"""
        try:
            if session_id not in self.sessions:
                return {"error": "Session not found"}
            
            session = self.sessions[session_id]
            session["status"] = "completed"
            session["ended_at"] = datetime.now().isoformat()
            
            # 生成最终摘要
            final_summary = {
                "session_id": session_id,
                "duration": self._calculate_duration(session),
                "total_steps": len(session["step_results"]),
                "successful_steps": len([
                    r for r in session["step_results"].values() 
                    if r.get("success")
                ]),
                "final_results": self._extract_final_results(session)
            }
            
            logger.info(f"✅ 会话已结束: {session_id}")
            return {"success": True, "summary": final_summary}
            
        except Exception as e:
            logger.error(f"❌ 结束会话失败: {e}")
            return {"error": str(e)}
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """清理过期会话"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            expired_sessions = []
            
            for session_id, session_data in self.sessions.items():
                created_at = datetime.fromisoformat(session_data["created_at"])
                if created_at < cutoff_time:
                    expired_sessions.append(session_id)
            
            # 删除过期会话
            for session_id in expired_sessions:
                del self.sessions[session_id]
            
            if expired_sessions:
                logger.info(f"🧹 已清理 {len(expired_sessions)} 个过期会话")
            
            return len(expired_sessions)
            
        except Exception as e:
            logger.error(f"❌ 清理过期会话失败: {e}")
            return 0
    
    def _calculate_success_rate(self, step_results: Dict) -> float:
        """计算步骤成功率"""
        if not step_results:
            return 0.0
        
        successful = len([r for r in step_results.values() if r.get("success")])
        total = len(step_results)
        
        return successful / total if total > 0 else 0.0
    
    def _get_last_activity(self, session: Dict) -> str:
        """获取最后活动时间"""
        if session["messages"]:
            return session["messages"][-1]["timestamp"]
        return session["created_at"]
    
    def _calculate_duration(self, session: Dict) -> str:
        """计算会话持续时间"""
        try:
            start_time = datetime.fromisoformat(session["created_at"])
            end_time = datetime.fromisoformat(session.get("ended_at", datetime.now().isoformat()))
            duration = end_time - start_time
            
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
                
        except Exception:
            return "未知"
    
    def _extract_final_results(self, session: Dict) -> Dict:
        """提取最终结果"""
        final_results = {}
        
        for step_name, step_data in session["step_results"].items():
            if step_data.get("success"):
                final_results[step_name] = step_data["result"]
        
        return final_results 