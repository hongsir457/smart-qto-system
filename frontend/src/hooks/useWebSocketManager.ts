/**
 * WebSocket 管理器 React Hook
 * 提供便捷的 WebSocket 连接管理
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { webSocketManager, ConnectionState, ConnectionConfig, MessageHandler } from '../utils/WebSocketManager';

interface UseWebSocketManagerOptions {
  connectionId: string;
  config: ConnectionConfig;
  autoConnect?: boolean;
  onMessage?: MessageHandler;
  onStateChange?: (state: ConnectionState) => void;
}

interface WebSocketHookReturn {
  state: ConnectionState;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  send: (message: any) => boolean;
  connectionInfo: any;
  stats: any;
}

export function useWebSocketManager({
  connectionId,
  config,
  autoConnect = true,
  onMessage,
  onStateChange
}: UseWebSocketManagerOptions): WebSocketHookReturn {
  const [state, setState] = useState<ConnectionState>(ConnectionState.DISCONNECTED);
  const [connectionInfo, setConnectionInfo] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  
  const messageHandlerRef = useRef<MessageHandler | undefined>(onMessage);
  const stateChangeHandlerRef = useRef<typeof onStateChange>(onStateChange);
  
  // 更新 refs
  useEffect(() => {
    messageHandlerRef.current = onMessage;
  }, [onMessage]);
  
  useEffect(() => {
    stateChangeHandlerRef.current = onStateChange;
  }, [onStateChange]);

  const connect = useCallback(async () => {
    try {
      await webSocketManager.connect(connectionId, config);
    } catch (error) {
      console.error('连接失败:', error);
      throw error;
    }
  }, [connectionId, config]);

  const disconnect = useCallback(async () => {
    await webSocketManager.disconnect(connectionId);
  }, [connectionId]);

  const send = useCallback((message: any) => {
    return webSocketManager.send(connectionId, message);
  }, [connectionId]);

  // 状态更新函数
  const updateState = useCallback(() => {
    const newState = webSocketManager.getState(connectionId) || ConnectionState.DISCONNECTED;
    setState(newState);
    
    const info = webSocketManager.getConnection(connectionId);
    setConnectionInfo(info ? {
      id: info.id,
      state: info.state,
      connectedAt: info.connectedAt,
      lastActivity: info.lastActivity,
      messageCount: info.messageCount,
      errorCount: info.errorCount,
      reconnectAttempts: info.reconnectAttempts
    } : null);
    
    setStats(webSocketManager.getStats());
  }, [connectionId]);

  // 注册事件处理器
  useEffect(() => {
    // 注册全局消息处理器
    const globalMessageHandler: MessageHandler = (message, connId) => {
      if (connId === connectionId && messageHandlerRef.current) {
        messageHandlerRef.current(message, connId);
      }
    };

    const stateChangeHandler = (newState: ConnectionState, connId: string) => {
      if (connId === connectionId) {
        setState(newState);
        updateState();
        
        if (stateChangeHandlerRef.current) {
          stateChangeHandlerRef.current(newState);
        }
      }
    };

    webSocketManager.onAnyMessage(globalMessageHandler);
    webSocketManager.onStateChange(stateChangeHandler);

    return () => {
      // 清理处理器（注意：这里需要改进 WebSocketManager 的 API 来支持移除特定处理器）
    };
  }, [connectionId, updateState]);

  // 自动连接
  useEffect(() => {
    if (autoConnect) {
      connect().catch(error => {
        console.error('自动连接失败:', error);
      });
    }

    // 组件卸载时断开连接
    return () => {
      if (autoConnect) {
        disconnect();
      }
    };
  }, [autoConnect, connect, disconnect]);

  // 定期更新状态和统计信息
  useEffect(() => {
    const interval = setInterval(updateState, 5000); // 每5秒更新一次
    
    return () => clearInterval(interval);
  }, [updateState]);

  return {
    state,
    connect,
    disconnect,
    send,
    connectionInfo,
    stats
  };
}

/**
 * 简化的任务状态 WebSocket Hook
 */
export function useTaskWebSocket(userId?: number) {
  const [messages, setMessages] = useState<any[]>([]);
  
  const handleMessage = useCallback((message: any) => {
    if (message.type === 'task_update' || message.type === 'user_tasks') {
      setMessages(prev => [...prev, message]);
    }
  }, []);

  const { state, send, connectionInfo } = useWebSocketManager({
    connectionId: `task_status_${userId}`,
    config: {
      endpoint: `tasks/${userId}`,
      userId
    },
    onMessage: handleMessage
  });

  const sendTaskCommand = useCallback((command: string, data?: any) => {
    return send({
      type: command,
      ...data,
      timestamp: new Date().toISOString()
    });
  }, [send]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    sendTaskCommand('clear_tasks');
  }, [sendTaskCommand]);

  const loadHistory = useCallback(() => {
    sendTaskCommand('load_history_tasks');
  }, [sendTaskCommand]);

  return {
    state,
    messages,
    connectionInfo,
    sendTaskCommand,
    clearMessages,
    loadHistory
  };
}

/**
 * 管理员监控 WebSocket Hook
 */
export function useAdminWebSocket() {
  const [systemStats, setSystemStats] = useState<any>(null);
  const [connectionEvents, setConnectionEvents] = useState<any[]>([]);
  
  const handleMessage = useCallback((message: any) => {
    if (message.type === 'system_stats') {
      setSystemStats(message.data);
    } else if (message.type === 'connection_event') {
      setConnectionEvents(prev => [...prev.slice(-50), message]); // 保留最近50个事件
    }
  }, []);

  const { state, send, stats } = useWebSocketManager({
    connectionId: 'admin_monitor',
    config: {
      endpoint: 'admin/monitor',
      userId: -1 // 特殊用户ID表示管理员
    },
    onMessage: handleMessage
  });

  const requestStats = useCallback(() => {
    return send({
      type: 'get_system_stats',
      timestamp: new Date().toISOString()
    });
  }, [send]);

  return {
    state,
    systemStats,
    connectionEvents,
    stats,
    requestStats
  };
} 