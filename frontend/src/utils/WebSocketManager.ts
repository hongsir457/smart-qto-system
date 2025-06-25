/**
 * WebSocket 连接池管理器
 * 提供统一的 WebSocket 连接管理、心跳保活、自动重连等功能
 */

import { jwtDecode } from 'jwt-decode';

export enum ConnectionState {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTING = 'disconnecting',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
  RECONNECTING = 'reconnecting'
}

export interface ConnectionConfig {
  endpoint: string;
  userId?: number;
  token?: string;
  autoReconnect?: boolean;
  heartbeatInterval?: number;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

export interface ConnectionInfo {
  id: string;
  config: ConnectionConfig;
  state: ConnectionState;
  websocket?: WebSocket;
  connectedAt?: Date;
  lastActivity?: Date;
  reconnectAttempts: number;
  heartbeatTimer?: NodeJS.Timeout;
  reconnectTimer?: NodeJS.Timeout;
  messageCount: number;
  errorCount: number;
}

export type MessageHandler = (message: any, connectionId: string) => void;
export type StateChangeHandler = (state: ConnectionState, connectionId: string) => void;

export class WebSocketManager {
  private connections: Map<string, ConnectionInfo> = new Map();
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private stateChangeHandlers: StateChangeHandler[] = [];
  private globalMessageHandlers: MessageHandler[] = [];
  
  // 默认配置
  private defaultConfig: Partial<ConnectionConfig> = {
    autoReconnect: true,
    heartbeatInterval: 30000, // 30秒
    maxReconnectAttempts: 5,
    reconnectDelay: 1000 // 1秒基础延迟
  };

  /**
   * 创建新的 WebSocket 连接
   */
  async connect(connectionId: string, config: ConnectionConfig): Promise<string> {
    // 如果连接已存在，先断开
    if (this.connections.has(connectionId)) {
      await this.disconnect(connectionId);
    }

    const fullConfig = { ...this.defaultConfig, ...config };
    
    // 从 localStorage 获取 token（如果未提供）
    if (!fullConfig.token) {
      fullConfig.token = localStorage.getItem('token') || undefined;
    }

    // 从 token 获取用户ID（如果未提供）
    if (!fullConfig.userId && fullConfig.token) {
      try {
        const decoded: any = jwtDecode(fullConfig.token);
        fullConfig.userId = parseInt(decoded.sub, 10);
      } catch (error) {
        console.error('解析token失败:', error);
      }
    }

    const connectionInfo: ConnectionInfo = {
      id: connectionId,
      config: fullConfig as ConnectionConfig,
      state: ConnectionState.CONNECTING,
      reconnectAttempts: 0,
      messageCount: 0,
      errorCount: 0
    };

    this.connections.set(connectionId, connectionInfo);
    this._updateConnectionState(connectionId, ConnectionState.CONNECTING);
    
    try {
      await this._createWebSocketConnection(connectionInfo);
      return connectionId;
    } catch (error) {
      this._updateConnectionState(connectionId, ConnectionState.ERROR);
      throw error;
    }
  }

  /**
   * 断开连接
   */
  async disconnect(connectionId: string): Promise<void> {
    const connection = this.connections.get(connectionId);
    if (!connection) return;

    this._updateConnectionState(connectionId, ConnectionState.DISCONNECTING);
    
    // 清理定时器
    this._clearTimers(connection);
    
    // 关闭 WebSocket
    if (connection.websocket) {
      connection.websocket.close(1000, '用户主动断开');
      connection.websocket = undefined;
    }

    this._updateConnectionState(connectionId, ConnectionState.DISCONNECTED);
    this.connections.delete(connectionId);
  }

  /**
   * 断开所有连接
   */
  async disconnectAll(): Promise<void> {
    const connectionIds = Array.from(this.connections.keys());
    await Promise.all(connectionIds.map(id => this.disconnect(id)));
  }

  /**
   * 发送消息
   */
  send(connectionId: string, message: any): boolean {
    const connection = this.connections.get(connectionId);
    if (!connection || !connection.websocket || connection.state !== ConnectionState.CONNECTED) {
      return false;
    }

    try {
      const messageData = typeof message === 'string' ? message : JSON.stringify(message);
      connection.websocket.send(messageData);
      connection.messageCount++;
      connection.lastActivity = new Date();
      return true;
    } catch (error) {
      console.error(`发送消息失败 [${connectionId}]:`, error);
      connection.errorCount++;
      return false;
    }
  }

  /**
   * 向所有连接广播消息
   */
  broadcast(message: any): number {
    let successCount = 0;
    for (const connectionId of this.connections.keys()) {
      if (this.send(connectionId, message)) {
        successCount++;
      }
    }
    return successCount;
  }

  /**
   * 注册消息处理器
   */
  onMessage(messageType: string, handler: MessageHandler): void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, []);
    }
    this.messageHandlers.get(messageType)!.push(handler);
  }

  /**
   * 注册全局消息处理器
   */
  onAnyMessage(handler: MessageHandler): void {
    this.globalMessageHandlers.push(handler);
  }

  /**
   * 注册状态变化处理器
   */
  onStateChange(handler: StateChangeHandler): void {
    this.stateChangeHandlers.push(handler);
  }

  /**
   * 移除消息处理器
   */
  offMessage(messageType: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(messageType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * 获取连接信息
   */
  getConnection(connectionId: string): ConnectionInfo | undefined {
    return this.connections.get(connectionId);
  }

  /**
   * 获取所有连接信息
   */
  getAllConnections(): ConnectionInfo[] {
    return Array.from(this.connections.values());
  }

  /**
   * 获取连接状态
   */
  getState(connectionId: string): ConnectionState | undefined {
    return this.connections.get(connectionId)?.state;
  }

  /**
   * 获取统计信息
   */
  getStats() {
    const connections = Array.from(this.connections.values());
    const stateCount = connections.reduce((acc, conn) => {
      acc[conn.state] = (acc[conn.state] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      totalConnections: connections.length,
      stateDistribution: stateCount,
      totalMessages: connections.reduce((sum, conn) => sum + conn.messageCount, 0),
      totalErrors: connections.reduce((sum, conn) => sum + conn.errorCount, 0),
      oldestConnection: connections.reduce((oldest, conn) => {
        if (!oldest || !conn.connectedAt) return oldest;
        return !oldest.connectedAt || conn.connectedAt < oldest.connectedAt ? conn : oldest;
      }, null as ConnectionInfo | null)
    };
  }

  // 私有方法
  private async _createWebSocketConnection(connectionInfo: ConnectionInfo): Promise<void> {
    const { config } = connectionInfo;
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || window.location.origin;
    const wsProtocol = apiBaseUrl.startsWith('https:') ? 'wss:' : 'ws:';
    const wsHost = apiBaseUrl.replace(/^https?:\/\//, '');
    
    // 构建 WebSocket URL
    let wsUrl = `${wsProtocol}//${wsHost}/api/v2/ws/${config.endpoint}`;
    if (config.userId) {
      wsUrl = wsUrl.replace('{user_id}', config.userId.toString());
    }
    if (config.token) {
      wsUrl += `?token=${config.token}`;
    }

    return new Promise((resolve, reject) => {
      const websocket = new WebSocket(wsUrl);
      connectionInfo.websocket = websocket;

      // 设置超时
      const timeout = setTimeout(() => {
        websocket.close();
        reject(new Error('连接超时'));
      }, 10000); // 10秒超时

      websocket.onopen = () => {
        clearTimeout(timeout);
        connectionInfo.connectedAt = new Date();
        connectionInfo.lastActivity = new Date();
        connectionInfo.reconnectAttempts = 0;
        
        this._updateConnectionState(connectionInfo.id, ConnectionState.CONNECTED);
        this._startHeartbeat(connectionInfo);
        
        resolve();
      };

      websocket.onmessage = (event) => {
        this._handleMessage(connectionInfo, event.data);
      };

      websocket.onclose = (event) => {
        clearTimeout(timeout);
        this._clearTimers(connectionInfo);
        
        if (connectionInfo.state !== ConnectionState.DISCONNECTING) {
          this._handleConnectionClose(connectionInfo, event);
        }
      };

      websocket.onerror = (error) => {
        clearTimeout(timeout);
        console.error(`WebSocket错误 [${connectionInfo.id}]:`, error);
        connectionInfo.errorCount++;
        
        if (connectionInfo.state === ConnectionState.CONNECTING) {
          reject(error);
        }
      };
    });
  }

  private _handleMessage(connectionInfo: ConnectionInfo, data: string): void {
    try {
      const message = JSON.parse(data);
      const messageType = message.type || 'unknown';
      
      connectionInfo.lastActivity = new Date();
      connectionInfo.messageCount++;

      // 处理内置消息类型
      if (messageType === 'heartbeat') {
        // 收到心跳，发送 pong
        this.send(connectionInfo.id, { type: 'pong', timestamp: new Date().toISOString() });
        return;
      }

      // 调用特定类型的处理器
      const handlers = this.messageHandlers.get(messageType);
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler(message, connectionInfo.id);
          } catch (error) {
            console.error(`消息处理器异常 [${messageType}]:`, error);
          }
        });
      }

      // 调用全局处理器
      this.globalMessageHandlers.forEach(handler => {
        try {
          handler(message, connectionInfo.id);
        } catch (error) {
          console.error('全局消息处理器异常:', error);
        }
      });

    } catch (error) {
      console.error(`解析消息失败 [${connectionInfo.id}]:`, error);
      connectionInfo.errorCount++;
    }
  }

  private _handleConnectionClose(connectionInfo: ConnectionInfo, event: CloseEvent): void {
    const shouldReconnect = connectionInfo.config.autoReconnect && 
                           connectionInfo.reconnectAttempts < (connectionInfo.config.maxReconnectAttempts || 5);

    if (shouldReconnect) {
      this._updateConnectionState(connectionInfo.id, ConnectionState.RECONNECTING);
      this._scheduleReconnect(connectionInfo);
    } else {
      this._updateConnectionState(connectionInfo.id, ConnectionState.DISCONNECTED);
      this.connections.delete(connectionInfo.id);
    }
  }

  private _scheduleReconnect(connectionInfo: ConnectionInfo): void {
    const delay = Math.min(
      (connectionInfo.config.reconnectDelay || 1000) * Math.pow(2, connectionInfo.reconnectAttempts),
      30000 // 最大30秒
    );

    connectionInfo.reconnectTimer = setTimeout(async () => {
      connectionInfo.reconnectAttempts++;
      
      try {
        await this._createWebSocketConnection(connectionInfo);
      } catch (error) {
        console.error(`重连失败 [${connectionInfo.id}]:`, error);
        this._handleConnectionClose(connectionInfo, new CloseEvent('close'));
      }
    }, delay);
  }

  private _startHeartbeat(connectionInfo: ConnectionInfo): void {
    const interval = connectionInfo.config.heartbeatInterval || 30000;
    
    connectionInfo.heartbeatTimer = setInterval(() => {
      if (connectionInfo.state === ConnectionState.CONNECTED) {
        this.send(connectionInfo.id, {
          type: 'ping',
          timestamp: new Date().toISOString()
        });
      }
    }, interval);
  }

  private _clearTimers(connectionInfo: ConnectionInfo): void {
    if (connectionInfo.heartbeatTimer) {
      clearInterval(connectionInfo.heartbeatTimer);
      connectionInfo.heartbeatTimer = undefined;
    }
    
    if (connectionInfo.reconnectTimer) {
      clearTimeout(connectionInfo.reconnectTimer);
      connectionInfo.reconnectTimer = undefined;
    }
  }

  private _updateConnectionState(connectionId: string, newState: ConnectionState): void {
    const connection = this.connections.get(connectionId);
    if (connection) {
      connection.state = newState;
      
      // 通知状态变化处理器
      this.stateChangeHandlers.forEach(handler => {
        try {
          handler(newState, connectionId);
        } catch (error) {
          console.error('状态变化处理器异常:', error);
        }
      });
    }
  }
}

// 创建全局实例
export const webSocketManager = new WebSocketManager(); 