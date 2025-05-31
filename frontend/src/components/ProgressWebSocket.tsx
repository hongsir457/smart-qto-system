'use client';

import { useEffect, useRef, useState } from 'react';

interface ProgressData {
  stage: string;
  progress: number;
  message: string;
  drawing_id?: number;
  error?: boolean;
  results?: any;
  warning?: string;
  compressed?: boolean;
}

interface ProgressWebSocketProps {
  taskId: string;
  onProgress?: (data: ProgressData) => void;
  onComplete?: (data: ProgressData) => void;
  onError?: (data: ProgressData) => void;
  autoConnect?: boolean;
}

export default function ProgressWebSocket({
  taskId,
  onProgress,
  onComplete,
  onError,
  autoConnect = true
}: ProgressWebSocketProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    
    try {
      // 获取token
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('No token found for WebSocket connection');
        setConnectionStatus('error');
        return;
      }

      // 建立WebSocket连接
      const wsUrl = `ws://localhost:8000/api/v1/websocket/ws?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket连接已建立');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;

        // 订阅任务进度
        if (taskId) {
          ws.send(JSON.stringify({
            action: 'subscribe',
            task_id: taskId
          }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('收到WebSocket消息:', data);

          if (data.type === 'task_progress' && data.task_id === taskId) {
            const progressData: ProgressData = data.data;
            
            // 调用相应的回调函数
            if (progressData.error && onError) {
              onError(progressData);
            } else if (progressData.stage === 'completed' && onComplete) {
              onComplete(progressData);
            } else if (onProgress) {
              onProgress(progressData);
            }
          } else if (data.type === 'subscription_confirmed') {
            console.log('任务订阅确认:', data.task_id);
          } else if (data.type === 'error') {
            console.error('WebSocket错误:', data.message);
            if (onError) {
              onError({
                stage: 'error',
                progress: 0,
                message: data.message,
                error: true
              });
            }
          }
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket连接已关闭:', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        wsRef.current = null;

        // 如果不是正常关闭，尝试重连
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`${delay}ms后尝试重连... (尝试 ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        setConnectionStatus('error');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
      setConnectionStatus('error');
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      // 取消订阅
      if (taskId && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          action: 'unsubscribe',
          task_id: taskId
        }));
      }

      wsRef.current.close(1000, 'Normal closure');
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
    reconnectAttempts.current = 0;
  };

  const subscribeToTask = (newTaskId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        task_id: newTaskId
      }));
    }
  };

  const unsubscribeFromTask = (oldTaskId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'unsubscribe',
        task_id: oldTaskId
      }));
    }
  };

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect]);

  useEffect(() => {
    // 当taskId变化时，重新订阅
    if (taskId && isConnected) {
      subscribeToTask(taskId);
    }
  }, [taskId, isConnected]);

  return (
    <div className="progress-websocket-status">
      {connectionStatus === 'connecting' && (
        <div className="text-sm text-gray-500">
          正在连接实时进度服务...
        </div>
      )}
      {connectionStatus === 'connected' && (
        <div className="text-sm text-green-600">
          ✓ 实时进度连接已建立
        </div>
      )}
      {connectionStatus === 'error' && (
        <div className="text-sm text-red-600">
          ✗ 实时进度连接失败
          <button 
            onClick={connect}
            className="ml-2 text-blue-600 hover:text-blue-800"
          >
            重试
          </button>
        </div>
      )}
      {connectionStatus === 'disconnected' && reconnectAttempts.current > 0 && (
        <div className="text-sm text-yellow-600">
          正在重连实时进度服务... ({reconnectAttempts.current}/{maxReconnectAttempts})
        </div>
      )}
    </div>
  );
} 