import React, { useState, useEffect, useRef } from 'react';
import { Card, Badge, Button, Space, Typography, List, Avatar, Tooltip, Modal, Select, Input } from 'antd';
import { 
  SyncOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  DeleteOutlined,
  CloudUploadOutlined,
  FileTextOutlined,
  EyeOutlined,
  CalculatorOutlined,
  BulbOutlined,
  ExpandOutlined,
  FilterOutlined,
  SearchOutlined
} from '@ant-design/icons';
import './RealTimeTaskMessages.css';
import './RealTimeTaskMessagesNvidia.css';
import { jwtDecode } from 'jwt-decode'; // 导入JWT解码库

const { Text, Title } = Typography;

// 严格对齐后端的任务状态枚举
export enum TaskStatus {
  PENDING = 'pending',      // 等待中
  STARTED = 'started',      // 已开始
  PROCESSING = 'processing', // 处理中
  SUCCESS = 'success',      // 成功完成
  FAILURE = 'failure',      // 失败
  RETRY = 'retry',          // 重试中
  REVOKED = 'revoked'       // 已撤销
}

// 严格对齐后端的任务阶段枚举
export enum TaskStage {
  QUEUED = 'queued',                     // 排队中
  UPLOADING = 'uploading',               // 上传中
  INITIALIZING = 'initializing',         // 初始化
  FILE_PROCESSING = 'file_processing',   // 文件处理
  OCR_RECOGNITION = 'ocr_recognition',   // OCR识别
  OCR_PROCESSING = 'ocr_processing',     // OCR处理中
  COMPONENT_DETECTION = 'component_detection', // 构件检测
  GPT_ANALYSIS = 'gpt_analysis',         // GPT分析
  QUANTITY_CALCULATION = 'quantity_calculation', // 工程量计算
  COMPLETED = 'completed',               // 已完成
  FAILED = 'failed'                      // 失败
}

// 消息类型枚举
export enum MessageType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error',
  PROCESSING = 'processing'
}

// 任务消息接口 - 严格对齐后端格式
export interface TaskMessage {
  id: string;
  task_id: string;
  name?: string;
  user_id?: number;
  status: TaskStatus;
  stage: TaskStage;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
  results?: any;
  metadata?: any;
  type: MessageType; // 前端显示用的消息类型
  timestamp: string; // 前端接收时间戳
}

// 任务状态配置
const TASK_STATUS_CONFIG = {
  [TaskStatus.PENDING]: {
    color: '#faad14',
    icon: <ClockCircleOutlined />,
    text: '等待中',
    messageType: MessageType.WARNING
  },
  [TaskStatus.STARTED]: {
    color: '#1890ff',
    icon: <PlayCircleOutlined />,
    text: '已开始',
    messageType: MessageType.INFO
  },
  [TaskStatus.PROCESSING]: {
    color: '#722ed1',
    icon: <LoadingOutlined spin />,
    text: '处理中',
    messageType: MessageType.PROCESSING
  },
  [TaskStatus.SUCCESS]: {
    color: '#52c41a',
    icon: <CheckCircleOutlined />,
    text: '成功',
    messageType: MessageType.SUCCESS
  },
  [TaskStatus.FAILURE]: {
    color: '#ff4d4f',
    icon: <CloseCircleOutlined />,
    text: '失败',
    messageType: MessageType.ERROR
  },
  [TaskStatus.RETRY]: {
    color: '#fa8c16',
    icon: <SyncOutlined spin />,
    text: '重试中',
    messageType: MessageType.WARNING
  },
  [TaskStatus.REVOKED]: {
    color: '#8c8c8c',
    icon: <CloseCircleOutlined />,
    text: '已撤销',
    messageType: MessageType.ERROR
  }
};

// 任务阶段配置
const TASK_STAGE_CONFIG = {
  [TaskStage.QUEUED]: {
    text: '排队中',
    icon: <ClockCircleOutlined />
  },
  [TaskStage.UPLOADING]: {
    text: '上传中',
    icon: <CloudUploadOutlined />
  },
  [TaskStage.INITIALIZING]: {
    text: '初始化',
    icon: <LoadingOutlined spin />
  },
  [TaskStage.FILE_PROCESSING]: {
    text: '文件处理',
    icon: <FileTextOutlined />
  },
  [TaskStage.OCR_RECOGNITION]: {
    text: 'OCR识别',
    icon: <EyeOutlined />
  },
  [TaskStage.OCR_PROCESSING]: {
    text: 'OCR处理中',
    icon: <EyeOutlined />
  },
  [TaskStage.COMPONENT_DETECTION]: {
    text: '构件检测',
    icon: <BulbOutlined />
  },
  [TaskStage.GPT_ANALYSIS]: {
    text: 'GPT分析',
    icon: <BulbOutlined />
  },
  [TaskStage.QUANTITY_CALCULATION]: {
    text: '工程量计算',
    icon: <CalculatorOutlined />
  },
  [TaskStage.COMPLETED]: {
    text: '已完成',
    icon: <CheckCircleOutlined />
  },
  [TaskStage.FAILED]: {
    text: '失败',
    icon: <CloseCircleOutlined />
  }
};

// 消息类型配置
const MESSAGE_TYPE_CONFIG = {
  [MessageType.INFO]: {
    color: '#1890ff',
    icon: <InfoCircleOutlined />,
    avatar: { icon: <InfoCircleOutlined />, style: { backgroundColor: '#1890ff' } }
  },
  [MessageType.SUCCESS]: {
    color: '#52c41a',
    icon: <CheckCircleOutlined />,
    avatar: { icon: <CheckCircleOutlined />, style: { backgroundColor: '#52c41a' } }
  },
  [MessageType.WARNING]: {
    color: '#faad14',
    icon: <ClockCircleOutlined />,
    avatar: { icon: <ClockCircleOutlined />, style: { backgroundColor: '#faad14' } }
  },
  [MessageType.ERROR]: {
    color: '#ff4d4f',
    icon: <CloseCircleOutlined />,
    avatar: { icon: <CloseCircleOutlined />, style: { backgroundColor: '#ff4d4f' } }
  },
  [MessageType.PROCESSING]: {
    color: '#722ed1',
    icon: <LoadingOutlined spin />,
    avatar: { icon: <LoadingOutlined spin />, style: { backgroundColor: '#722ed1' } }
  }
};

interface User {
  id: number;
  username: string;
}

interface RealTimeTaskMessagesProps {
  maxMessages?: number;
  onTaskComplete?: (taskId: string) => void;
  onTaskError?: (taskId: string, error: string) => void;
}

const RealTimeTaskMessages: React.FC<RealTimeTaskMessagesProps> = ({
  maxMessages = 20,
  onTaskComplete,
  onTaskError
}) => {
  const [messages, setMessages] = useState<TaskMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [messageDetailVisible, setMessageDetailVisible] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<any>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchText, setSearchText] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reconnectAttemptsRef = useRef<number | null>(null);

  // 自动滚动到最新消息
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // WebSocket连接
  const connectWebSocket = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('🔌 WebSocket 已连接，无需重复连接。');
      return;
    }

    console.log('🔗 正在尝试连接WebSocket...');
    setConnectionStatus('connecting');

    const token = localStorage.getItem('token');
    if (!token) {
      console.error('❌ 缺少认证令牌，无法连接WebSocket。');
      setConnectionStatus('disconnected');
      return;
    }

    // 从Token中解码用户ID
    let userId: number | null = null;
    try {
      const decodedToken: { sub: string } = jwtDecode(token);
      userId = parseInt(decodedToken.sub, 10);
    } catch (error) {
      console.error('❌ 解析Token失败:', error);
      // 作为备用方案，尝试从 localStorage 获取用户信息
      const userString = localStorage.getItem('user');
      if (userString) {
        try {
          const user: User = JSON.parse(userString);
          userId = user.id;
        } catch (parseError) {
          console.error('❌ 解析用户信息失败:', parseError);
        }
      }
    }

    if (!userId) {
      console.error('❌ 无法获取用户ID，无法连接WebSocket。');
      setConnectionStatus('disconnected');
      return;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || window.location.origin;
    const wsProtocol = apiBaseUrl.startsWith('https:') ? 'wss:' : 'ws:';
    const wsHost = apiBaseUrl.replace(/^https?:\/\//, '');

    // 构建新的、正确的WebSocket URL
    // 格式: wss://your-backend-host/api/v1/ws/tasks/{user_id}?token=...
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/ws/tasks/${userId}?token=${token}`;

    console.log(`📡 准备连接到: ${wsUrl}`);

    try {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        console.log('✅ WebSocket 连接成功！');
        setIsConnected(true);
        setConnectionStatus('connected');
        
        // 添加连接成功消息
        addSystemMessage('WebSocket连接已建立，开始接收实时任务消息', MessageType.SUCCESS);
        
        // 启动心跳机制
        startHeartbeat();
      };
      
      socket.onmessage = (event) => {
        console.log('📥 收到WebSocket消息:', event.data);
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('❌ 解析WebSocket消息失败:', error);
        }
      };
      
      socket.onclose = (event) => {
        console.log('🔌 WebSocket连接关闭, code:', event.code, 'reason:', event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        wsRef.current = null;
        
        // 停止心跳
        stopHeartbeat();
        
        // 添加断开连接消息
        if (event.code === 1000) {
          addSystemMessage('WebSocket连接正常关闭', MessageType.INFO);
        } else {
          addSystemMessage(`WebSocket连接异常关闭 (${event.code})`, MessageType.WARNING);
        }
        
        // 处理不同的关闭代码
        if (event.code === 1008) {
          console.error('❌ 认证失败，请重新登录');
          addSystemMessage('认证失败，请重新登录', MessageType.ERROR);
          return;
        }
        
        if (event.code === 1011) {
          console.error('❌ 服务器内部错误');
          addSystemMessage('服务器内部错误，稍后重试', MessageType.ERROR);
        }
        
        // 避免频繁重连，使用递增延迟
        const reconnectDelay = Math.min(5000 * Math.pow(2, Math.min(reconnectAttemptsRef.current || 0, 4)), 30000);
        
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        
        console.log(`🔄 ${reconnectDelay/1000}秒后尝试重连... (尝试次数: ${(reconnectAttemptsRef.current || 0) + 1})`);
        
        reconnectTimerRef.current = setTimeout(() => {
          reconnectAttemptsRef.current = (reconnectAttemptsRef.current || 0) + 1;
          if (reconnectAttemptsRef.current <= 5) { // 最多重试5次
            connectWebSocket();
          } else {
            console.error('❌ 重连次数过多，停止自动重连');
            addSystemMessage('连接失败次数过多，请手动刷新重连', MessageType.ERROR);
          }
        }, reconnectDelay);
      };
      
      socket.onerror = (error) => {
        console.error('❌ WebSocket错误:', error);
        
        // 根据错误类型提供不同的处理
        if (error instanceof Event && error.type === 'error') {
          // 网络错误或连接被拒绝
          addSystemMessage('网络连接错误，正在尝试重连...', MessageType.WARNING);
        } else {
          addSystemMessage('WebSocket连接出错', MessageType.ERROR);
        }
      };
    } catch (error) {
      console.error('❌ WebSocket连接失败:', error);
      addSystemMessage('WebSocket连接失败', MessageType.ERROR);
    }
  };

  // 智能解析和格式化WebSocket消息
  const parseWebSocketMessage = (rawMessage: any) => {
    // 如果是字符串，尝试解析为JSON
    if (typeof rawMessage === 'string') {
      try {
        return JSON.parse(rawMessage);
      } catch (error) {
        console.warn('无法解析JSON消息:', rawMessage);
        return { type: 'raw_text', message: rawMessage };
      }
    }
    return rawMessage;
  };

  // 处理WebSocket消息 - 严格对齐后端格式
  const handleWebSocketMessage = (rawMessage: any) => {
    const message = parseWebSocketMessage(rawMessage);
    console.log('📨 处理WebSocket消息:', message);
    
    switch (message.type) {
      case 'connection_established':
        addSystemMessage('WebSocket连接已建立，开始接收实时任务消息', MessageType.SUCCESS);
        break;
        
      case 'user_tasks':
        // 接收用户任务列表
        if (message.tasks && Array.isArray(message.tasks)) {
          addSystemMessage(`已加载 ${message.tasks.length} 个历史任务`, MessageType.INFO);
          
          // 处理每个历史任务
          message.tasks.forEach((taskData: any) => {
            if (isValidTaskData(taskData)) {
              addTaskMessage(taskData);
            }
          });
        }
        break;
        
      case 'task_update':
        // 单个任务更新 - 严格按后端格式处理
        if (message.task_id && message.data && isValidTaskData(message.data)) {
          addTaskMessage(message.data);
          
          // 执行回调
          const taskData = message.data;
          if (taskData.status === TaskStatus.SUCCESS && onTaskComplete) {
            onTaskComplete(message.task_id);
          } else if (taskData.status === TaskStatus.FAILURE && onTaskError) {
            onTaskError(message.task_id, taskData.error_message || taskData.message || '任务执行失败');
          }
        }
        break;
        
      case 'task_message':
        // 任务详细消息处理 - 后端发送的进度消息
        if (message.task_id && message.message) {
          // 构造任务数据对象
          const taskData = {
            task_id: message.task_id,
            name: message.task_name || '任务处理',
            status: message.status || TaskStatus.PROCESSING,
            stage: message.stage || TaskStage.QUEUED,
            progress: message.progress || 0,
            message: message.message,
            created_at: message.timestamp || new Date().toISOString(),
            updated_at: message.timestamp || new Date().toISOString(),
            user_id: message.user_id
          };
          
          if (isValidTaskData(taskData)) {
            addTaskMessage(taskData);
            
            // 执行回调
            if (taskData.status === TaskStatus.SUCCESS && onTaskComplete) {
              onTaskComplete(message.task_id);
            } else if (taskData.status === TaskStatus.FAILURE && onTaskError) {
              onTaskError(message.task_id, taskData.message || '任务执行失败');
            }
          }
        }
        break;
        
      case 'task_history':
        // 兼容旧的任务历史消息类型
        if (message.tasks && Array.isArray(message.tasks)) {
          addSystemMessage(`已加载 ${message.tasks.length} 个历史任务`, MessageType.INFO);
          message.tasks.forEach((taskData: any) => {
            if (isValidTaskData(taskData)) {
              addTaskMessage(taskData);
            }
          });
        }
        break;
        
      case 'raw_text':
        // 处理无法解析的原始文本消息
        if (typeof message.message === 'string' && message.message.trim()) {
          // 如果是超长的JSON字符串，尝试提取关键信息
          if (message.message.length > 200 && message.message.includes('{')) {
            addSystemMessage('收到复杂数据消息（已简化显示）', MessageType.INFO);
          } else {
            addSystemMessage(message.message, MessageType.INFO);
          }
        }
        break;
        
      case 'error':
        addSystemMessage(message.message || '发生错误', MessageType.ERROR);
        break;
        
      case 'pong':
        // 忽略pong消息，这是心跳响应
        console.debug('收到pong消息');
        break;
        
      default:
        console.log('未处理的消息类型:', message.type, message);
        // 智能处理未知消息类型
        if (message.task_id && message.message) {
          // 如果有任务ID和消息，作为任务消息处理
          addSystemMessage(`[${message.task_id.substring(0, 8)}] ${message.message}`, MessageType.INFO);
        } else if (message.message) {
          // 如果只有消息内容，作为系统消息处理
          addSystemMessage(message.message, MessageType.INFO);
        } else if (message.type) {
          // 如果有类型但格式不规范，显示简化信息
          addSystemMessage(`收到 ${message.type} 类型消息`, MessageType.WARNING);
        } else {
          // 完全未知的消息，记录但不显示具体内容
          console.warn('收到未知格式的WebSocket消息:', message);
          addSystemMessage('收到未知格式的消息（详情请查看控制台）', MessageType.WARNING);
        }
    }
  };

  // 验证任务数据格式
  const isValidTaskData = (taskData: any): boolean => {
    return taskData && 
           typeof taskData.task_id === 'string' &&
           typeof taskData.status === 'string' &&
           typeof taskData.stage === 'string' &&
           typeof taskData.progress === 'number' &&
           typeof taskData.message === 'string';
  };

  // 添加任务消息 - 严格按后端格式处理
  const addTaskMessage = (taskData: any) => {
    const statusConfig = TASK_STATUS_CONFIG[taskData.status as TaskStatus];
    const stageConfig = TASK_STAGE_CONFIG[taskData.stage as TaskStage];
    
    if (!statusConfig || !stageConfig) {
      console.warn('未知的任务状态或阶段:', taskData.status, taskData.stage);
      return;
    }

    // 构建详细的消息内容
    let messageContent = taskData.message || '任务状态更新';
    
    // 添加进度信息
    if (taskData.progress !== undefined && taskData.progress >= 0) {
      messageContent += ` (${Math.round(taskData.progress)}%)`;
    }
    
    // 如果有错误消息，显示错误详情
    if (taskData.error_message && taskData.status === TaskStatus.FAILURE) {
      messageContent = `${messageContent} - 错误: ${taskData.error_message}`;
    }

    const taskMessage: TaskMessage = {
      id: `task_${taskData.task_id}`, // 使用固定ID，方便更新
      task_id: taskData.task_id,
      name: taskData.name,
      user_id: taskData.user_id,
      status: taskData.status as TaskStatus,
      stage: taskData.stage as TaskStage,
      progress: taskData.progress || 0,
      message: messageContent,
      created_at: taskData.created_at,
      updated_at: taskData.updated_at,
      error_message: taskData.error_message,
      results: taskData.results,
      metadata: taskData.metadata,
      type: statusConfig.messageType,
      timestamp: new Date().toISOString()
    };

    setMessages(prevMessages => {
      // 查找是否已存在同一个任务的消息
      const existingIndex = prevMessages.findIndex(msg => 
        msg.task_id === taskData.task_id && msg.task_id !== 'system'
      );
      
      if (existingIndex !== -1) {
        // 如果找到了现有消息，更新它
        const updatedMessages = [...prevMessages];
        updatedMessages[existingIndex] = taskMessage;
        
        // 如果任务完成或失败，将消息移到顶部
        if (taskData.status === TaskStatus.SUCCESS || taskData.status === TaskStatus.FAILURE) {
          updatedMessages.splice(existingIndex, 1);
          updatedMessages.unshift(taskMessage);
        }
        
        return updatedMessages.slice(0, maxMessages);
      } else {
        // 如果没有找到，添加新消息
        const updatedMessages = [taskMessage, ...prevMessages];
        return updatedMessages.slice(0, maxMessages);
      }
    });
  };

  // 添加系统消息
  const addSystemMessage = (message: string, type: MessageType = MessageType.INFO) => {
    const systemMessage: TaskMessage = {
      id: `sys_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      task_id: 'system',
      status: TaskStatus.SUCCESS,
      stage: TaskStage.COMPLETED,
      progress: 100,
      message: message,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      type: type,
      timestamp: new Date().toISOString()
    };

    setMessages(prevMessages => {
      const updatedMessages = [systemMessage, ...prevMessages];
      return updatedMessages.slice(0, maxMessages);
    });
  };

  // 清空消息
  const clearMessages = () => {
    setMessages([]);
    addSystemMessage('消息列表已清空', MessageType.INFO);
  };

  // 清理已完成任务的历史进度消息，只保留最终状态
  const cleanupCompletedTasks = () => {
    setMessages(prevMessages => {
      const taskMap = new Map<string, TaskMessage>();
      const systemMessages: TaskMessage[] = [];
      
      // 遍历消息，保留系统消息和每个任务的最新状态
      prevMessages.forEach(message => {
        if (message.task_id === 'system') {
          systemMessages.push(message);
        } else {
          // 对于任务消息，只保留最新的（优先保留已完成或失败的状态）
          const existing = taskMap.get(message.task_id);
          if (!existing || 
              (message.status === TaskStatus.SUCCESS || message.status === TaskStatus.FAILURE) ||
              (existing.status !== TaskStatus.SUCCESS && existing.status !== TaskStatus.FAILURE)) {
            taskMap.set(message.task_id, message);
          }
        }
      });
      
      // 合并系统消息和任务最终状态
      const cleanedMessages = [...systemMessages, ...Array.from(taskMap.values())];
      
      // 按时间戳排序，最新的在前
      cleanedMessages.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      
      addSystemMessage(`已清理重复进度消息，保留 ${cleanedMessages.length} 条消息`, MessageType.INFO);
      return cleanedMessages.slice(0, maxMessages);
    });
  };

  // 刷新连接
  const refreshConnection = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    connectWebSocket();
  };

  // 格式化时间
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // 显示消息详情
  const showMessageDetail = (message: TaskMessage) => {
    setSelectedMessage(message);
    setMessageDetailVisible(true);
  };

  // 格式化显示对象
  const formatObjectForDisplay = (obj: any, depth = 0): string => {
    if (depth > 3) return '[深层对象...]';
    
    if (obj === null || obj === undefined) return String(obj);
    if (typeof obj === 'string') return obj;
    if (typeof obj === 'number' || typeof obj === 'boolean') return String(obj);
    
    if (Array.isArray(obj)) {
      if (obj.length === 0) return '[]';
      if (obj.length > 10) return `[数组包含${obj.length}个元素...]`;
      return '[' + obj.map(item => formatObjectForDisplay(item, depth + 1)).join(', ') + ']';
    }
    
    if (typeof obj === 'object') {
      const keys = Object.keys(obj);
      if (keys.length === 0) return '{}';
      if (keys.length > 20) return `{对象包含${keys.length}个属性...}`;
      
      const entries = keys.slice(0, 5).map(key => {
        const value = formatObjectForDisplay(obj[key], depth + 1);
        return `${key}: ${value}`;
      });
      
      if (keys.length > 5) {
        entries.push('...');
      }
      
      return '{' + entries.join(', ') + '}';
    }
    
    return String(obj);
  };

  // 过滤消息
  const filteredMessages = messages.filter(message => {
    // 状态过滤
    if (filterStatus !== 'all' && message.status !== filterStatus) {
      return false;
    }
    
    // 搜索过滤
    if (searchText.trim()) {
      const search = searchText.toLowerCase();
      return (
        message.message.toLowerCase().includes(search) ||
        message.task_id.toLowerCase().includes(search) ||
        (message.name && message.name.toLowerCase().includes(search)) ||
        (message.error_message && message.error_message.toLowerCase().includes(search))
      );
    }
    
    return true;
  });

  // 消息统计
  const messageStats = {
    total: messages.length,
    success: messages.filter(m => m.status === TaskStatus.SUCCESS).length,
    failure: messages.filter(m => m.status === TaskStatus.FAILURE).length,
    processing: messages.filter(m => m.status === TaskStatus.PROCESSING).length,
    pending: messages.filter(m => m.status === TaskStatus.PENDING).length
  };

  // 心跳机制
  const startHeartbeat = () => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
    }
    
    // 每30秒发送一次心跳
    heartbeatTimerRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'ping',
          timestamp: new Date().toISOString()
        }));
        console.debug('💓 发送心跳ping');
      }
    }, 30000);
  };

  const stopHeartbeat = () => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  };

  // 连接WebSocket
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (heartbeatTimerRef.current) {
        clearInterval(heartbeatTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <Card 
      size="small"
      className="real-time-messages-nvidia"
      style={{ height: '100%', maxHeight: '100%' }}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <PlayCircleOutlined style={{ color: '#76b900' }} />
          <span>实时任务消息</span>
          <Badge 
            count={messages.length} 
            style={{ 
              backgroundColor: messages.length > 0 ? '#76b900' : '#666',
              color: '#000',
              fontWeight: 'bold'
            }}
          />
        </div>
      }
      bodyStyle={{ 
        padding: 0,
        height: 'calc(100% - 55px)',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* 连接状态指示器 */}
      <div className="nvidia-connection-status">
        <div className={`nvidia-connection-indicator ${connectionStatus}`} />
        <span className="nvidia-connection-text">
          {connectionStatus === 'connected' ? 'CONNECTED' : 
           connectionStatus === 'connecting' ? 'CONNECTING' : 'DISCONNECTED'}
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Button
            type="text"
            size="small"
            icon={<FilterOutlined />}
            onClick={() => setShowFilters(!showFilters)}
            style={{ color: showFilters ? '#76b900' : '#ffffff' }}
          >
            过滤
          </Button>
          <span className="nvidia-message-count">
            {filteredMessages.length}/{messages.length} 消息
          </span>
        </div>
      </div>

      {/* 过滤器区域 */}
      {showFilters && (
        <div style={{ 
          padding: '12px 20px', 
          background: 'rgba(0, 0, 0, 0.4)', 
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          gap: '12px',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#ffffff', fontSize: '12px' }}>状态:</span>
            <Select
              size="small"
              value={filterStatus}
              onChange={setFilterStatus}
              style={{ width: 120 }}
              options={[
                { label: '全部', value: 'all' },
                { label: '等待中', value: TaskStatus.PENDING },
                { label: '处理中', value: TaskStatus.PROCESSING },
                { label: '成功', value: TaskStatus.SUCCESS },
                { label: '失败', value: TaskStatus.FAILURE },
                { label: '重试中', value: TaskStatus.RETRY }
              ]}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
            <span style={{ color: '#ffffff', fontSize: '12px' }}>搜索:</span>
            <Input
              size="small"
              placeholder="搜索任务ID、消息内容..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              prefix={<SearchOutlined style={{ color: '#00d4aa' }} />}
              style={{ flex: 1, maxWidth: 250 }}
              allowClear
            />
          </div>
          {messageStats.total > 0 && (
            <div style={{ 
              display: 'flex', 
              gap: '12px', 
              fontSize: '11px',
              color: '#888'
            }}>
              <span>成功: <span style={{color: '#76b900'}}>{messageStats.success}</span></span>
              <span>失败: <span style={{color: '#ff6c37'}}>{messageStats.failure}</span></span>
              <span>处理中: <span style={{color: '#00d4aa'}}>{messageStats.processing}</span></span>
              <span>等待: <span style={{color: '#ffc107'}}>{messageStats.pending}</span></span>
            </div>
          )}
        </div>
      )}

      {/* 消息列表区域 */}
      <div className="nvidia-messages-container">
        {filteredMessages.length > 0 ? (
          <>
            {filteredMessages.map((message) => {
              const config = MESSAGE_TYPE_CONFIG[message.type];
              return (
                <div 
                  key={message.id}
                  className={`nvidia-message-item type-${message.type}`}
                >
                  <div className="nvidia-message-content">
                    <div className={`nvidia-message-icon type-${message.type}`}>
                      {config.icon}
                    </div>
                    <div className="nvidia-message-body">
                      <div className="nvidia-message-text">
                        {message.name && (
                          <span className="nvidia-task-highlight">
                            [{message.name}] 
                          </span>
                        )}
                        {message.message}
                      </div>
                      <div className="nvidia-message-meta">
                        <span className="nvidia-message-time">
                          {formatTimestamp(message.timestamp)}
                        </span>
                        {message.stage && (
                          <span className="nvidia-message-task">
                            {TASK_STAGE_CONFIG[message.stage as TaskStage].text}
                          </span>
                        )}
                        {message.progress !== undefined && (
                          <span style={{ color: '#00d4aa' }}>
                            {Math.round(message.progress)}%
                          </span>
                        )}
                      </div>
                      {message.progress !== undefined && (
                        <div className="nvidia-progress-bar">
                          <div 
                            className="nvidia-progress-fill"
                            style={{ width: `${message.progress}%` }}
                          />
                        </div>
                      )}
                    </div>
                    {/* 消息详情按钮 */}
                    <div className="nvidia-message-actions">
                      <Tooltip title="查看详情">
                        <Button
                          type="text"
                          size="small"
                          icon={<ExpandOutlined />}
                          onClick={() => showMessageDetail(message)}
                          style={{ 
                            color: '#00d4aa',
                            border: 'none',
                            padding: '2px 4px'
                          }}
                        />
                      </Tooltip>
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </>
        ) : (
          <div className="nvidia-no-messages">
            <div className="nvidia-no-messages-icon">
              <InfoCircleOutlined />
            </div>
            <div className="nvidia-no-messages-text">
              {messages.length === 0 ? '暂无任务消息' : '没有符合条件的消息'}
            </div>
            <div className="nvidia-no-messages-hint">
              {messages.length === 0 
                ? '实时任务消息将在此处显示' 
                : '尝试调整过滤条件或清空搜索'
              }
            </div>
          </div>
        )}
      </div>

      {/* 操作按钮区域 */}
      <div className="nvidia-actions-bar">
        <div>
          <Button 
            size="small" 
            className="nvidia-action-btn nvidia-action-btn-danger"
            icon={<DeleteOutlined />}
            onClick={clearMessages}
            disabled={filteredMessages.length === 0}
          >
            清空消息
          </Button>
        </div>
        <div>
          <Button 
            size="small" 
            className="nvidia-action-btn"
            icon={<SyncOutlined />} 
            onClick={refreshConnection}
          >
            重新连接
          </Button>
        </div>
      </div>

      {/* 消息详情模态框 */}
      <Modal
        title="消息详情"
        open={messageDetailVisible}
        onCancel={() => setMessageDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setMessageDetailVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {selectedMessage && (
          <div style={{ fontSize: '14px' }}>
            <div style={{ marginBottom: '16px' }}>
              <strong>任务ID:</strong> {selectedMessage.task_id}
            </div>
            {selectedMessage.name && (
              <div style={{ marginBottom: '16px' }}>
                <strong>任务名称:</strong> {selectedMessage.name}
              </div>
            )}
                         <div style={{ marginBottom: '16px' }}>
               <strong>状态:</strong> {TASK_STATUS_CONFIG[selectedMessage.status as TaskStatus]?.text || selectedMessage.status}
             </div>
            <div style={{ marginBottom: '16px' }}>
              <strong>阶段:</strong> {TASK_STAGE_CONFIG[selectedMessage.stage as TaskStage]?.text || selectedMessage.stage}
            </div>
            <div style={{ marginBottom: '16px' }}>
              <strong>进度:</strong> {selectedMessage.progress}%
            </div>
            <div style={{ marginBottom: '16px' }}>
              <strong>时间:</strong> {formatTimestamp(selectedMessage.timestamp)}
            </div>
            <div style={{ marginBottom: '16px' }}>
              <strong>消息内容:</strong>
              <div style={{ 
                marginTop: '8px', 
                padding: '12px', 
                backgroundColor: '#f5f5f5', 
                borderRadius: '4px',
                wordBreak: 'break-word',
                maxHeight: '200px',
                overflowY: 'auto'
              }}>
                {selectedMessage.message}
              </div>
            </div>
            {selectedMessage.error_message && (
              <div style={{ marginBottom: '16px' }}>
                <strong>错误信息:</strong>
                <div style={{ 
                  marginTop: '8px', 
                  padding: '12px', 
                  backgroundColor: '#fff2f0', 
                  borderRadius: '4px',
                  color: '#ff4d4f',
                  wordBreak: 'break-word'
                }}>
                  {selectedMessage.error_message}
                </div>
              </div>
            )}
            {selectedMessage.results && (
              <div style={{ marginBottom: '16px' }}>
                <strong>结果数据:</strong>
                <div style={{ 
                  marginTop: '8px', 
                  padding: '12px', 
                  backgroundColor: '#f6ffed', 
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  maxHeight: '200px',
                  overflowY: 'auto',
                  wordBreak: 'break-word'
                }}>
                  {formatObjectForDisplay(selectedMessage.results)}
                </div>
              </div>
            )}
            {selectedMessage.metadata && (
              <div style={{ marginBottom: '16px' }}>
                <strong>元数据:</strong>
                <div style={{ 
                  marginTop: '8px', 
                  padding: '12px', 
                  backgroundColor: '#f0f0f0', 
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  maxHeight: '200px',
                  overflowY: 'auto',
                  wordBreak: 'break-word'
                }}>
                  {formatObjectForDisplay(selectedMessage.metadata)}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </Card>
  );
};

export default RealTimeTaskMessages; 