import React, { useState, useEffect, useRef } from 'react';
import { Card, Badge, Progress, Button, Collapse, Alert, Space, Typography, Tooltip, Modal } from 'antd';
import { 
  SyncOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  EyeOutlined,
  DeleteOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons';
import './UploadTaskStatus.css';

const { Panel } = Collapse;
const { Text, Title } = Typography;

// 任务状态枚举
export enum TaskStatus {
  PENDING = 'pending',
  STARTED = 'started', 
  PROCESSING = 'processing',
  SUCCESS = 'success',
  FAILURE = 'failure',
  RETRY = 'retry'
}

// 任务阶段枚举
export enum TaskStage {
  QUEUED = 'queued',
  UPLOADING = 'uploading',
  OCR_PROCESSING = 'ocr_processing',
  COMPONENT_DETECTION = 'component_detection',
  GPT_ANALYSIS = 'gpt_analysis',
  QUANTITY_CALCULATION = 'quantity_calculation',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

// 任务信息接口
export interface TaskInfo {
  task_id: string;
  name: string;
  status: TaskStatus;
  stage: TaskStage;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
  drawing_id?: number;
  file_name?: string;
}

// 状态配置
const STATUS_CONFIG = {
  [TaskStatus.PENDING]: {
    color: '#faad14',
    text: '等待中',
    icon: <ClockCircleOutlined />,
    badgeStatus: 'warning' as const
  },
  [TaskStatus.STARTED]: {
    color: '#1890ff',
    text: '已开始',
    icon: <PlayCircleOutlined />,
    badgeStatus: 'processing' as const
  },
  [TaskStatus.PROCESSING]: {
    color: '#722ed1',
    text: '处理中',
    icon: <SyncOutlined spin />,
    badgeStatus: 'processing' as const
  },
  [TaskStatus.SUCCESS]: {
    color: '#52c41a',
    text: '成功',
    icon: <CheckCircleOutlined />,
    badgeStatus: 'success' as const
  },
  [TaskStatus.FAILURE]: {
    color: '#ff4d4f',
    text: '失败',
    icon: <CloseCircleOutlined />,
    badgeStatus: 'error' as const
  },
  [TaskStatus.RETRY]: {
    color: '#fa8c16',
    text: '重试中',
    icon: <SyncOutlined spin />,
    badgeStatus: 'processing' as const
  }
};

// 阶段配置
const STAGE_CONFIG = {
  [TaskStage.QUEUED]: '排队中',
  [TaskStage.UPLOADING]: '上传中',
  [TaskStage.OCR_PROCESSING]: 'OCR文字识别',
  [TaskStage.COMPONENT_DETECTION]: '构件检测',
  [TaskStage.GPT_ANALYSIS]: 'GPT智能分析',
  [TaskStage.QUANTITY_CALCULATION]: '工程量计算',
  [TaskStage.COMPLETED]: '已完成',
  [TaskStage.FAILED]: '失败'
};

interface UploadTaskStatusProps {
  onTaskComplete?: (taskId: string) => void;
  onTaskError?: (taskId: string, error: string) => void;
}

const UploadTaskStatus: React.FC<UploadTaskStatusProps> = ({
  onTaskComplete,
  onTaskError
}) => {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const connectionIdRef = useRef<string | null>(null);

  // WebSocket连接
  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    console.log('🔗 尝试连接WebSocket...');
    setConnectionStatus('connecting');
    
    if (!connectionIdRef.current) {
      connectionIdRef.current = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      console.error('❌ 缺少认证令牌');
      setConnectionStatus('disconnected');
      return;
    }
    
    // 使用新的WebSocket认证端点
    const wsUrl = `ws://localhost:8000/ws/realtime/${connectionIdRef.current}?token=${encodeURIComponent(token)}`;
    
    console.log('🔗 连接URL:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('✅ WebSocket连接成功');
      setIsConnected(true);
      setConnectionStatus('connected');
      
      // 连接建立后会自动接收用户任务列表
    };
    
    ws.onmessage = (event) => {
      console.log('📥 收到WebSocket消息:', event.data);
      try {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
      } catch (error) {
        console.error('❌ 解析WebSocket消息失败:', error);
      }
    };
    
    ws.onclose = (event) => {
      console.log('🔌 WebSocket连接关闭, code:', event.code, 'reason:', event.reason);
      setIsConnected(false);
      setConnectionStatus('disconnected');
      wsRef.current = null;
      
      // 如果是认证失败，不重连
      if (event.code === 1008) {
        console.error('❌ 认证失败，请重新登录');
        return;
      }
      
      // 5秒后重连
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      reconnectTimerRef.current = setTimeout(() => {
        console.log('🔄 尝试重连...');
        connectWebSocket();
      }, 5000);
    };
    
    ws.onerror = (error) => {
      console.error('❌ WebSocket错误:', error);
    };
    
    wsRef.current = ws;
  };

  // 处理WebSocket消息
  const handleWebSocketMessage = (message: any) => {
    console.log('📨 处理WebSocket消息:', message);
    
    switch (message.type) {
      case 'connection_established':
        console.log('✅ WebSocket连接已建立');
        break;
        
      case 'user_tasks':
        // 接收用户任务列表
        if (message.tasks && Array.isArray(message.tasks)) {
          // 过滤并转换任务数据
          const validTasks = message.tasks
            .filter((task: any) => task && task.task_id && task.status)
            .map((task: any) => ({
              task_id: task.task_id,
              name: task.name,
              user_id: task.user_id,
              status: task.status as TaskStatus,
              stage: task.stage || TaskStage.QUEUED,
              progress: task.progress || 0,
              message: task.message || '',
              created_at: task.created_at,
              updated_at: task.updated_at,
              started_at: task.started_at,
              completed_at: task.completed_at,
              error_message: task.error_message,
              results: task.results,
              file_name: task.metadata?.drawing_filename || null,
              drawing_id: task.metadata?.drawing_id || null
            }));
          
          console.log(`📝 收到 ${validTasks.length} 个用户任务`);
          setTasks(validTasks);
        }
        break;
        
      case 'task_update':
        // 任务状态更新
        if (message.task) {
          const taskData = {
            task_id: message.task.task_id,
            name: message.task.name,
            user_id: message.task.user_id,
            status: message.task.status as TaskStatus,
            stage: message.task.stage || TaskStage.QUEUED,
            progress: message.task.progress || 0,
            message: message.task.message || '',
            created_at: message.task.created_at,
            updated_at: message.task.updated_at,
            started_at: message.task.started_at,
            completed_at: message.task.completed_at,
            error_message: message.task.error_message,
            results: message.task.results,
            file_name: message.task.metadata?.drawing_filename || null,
            drawing_id: message.task.metadata?.drawing_id || null
          };
          
          setTasks(prevTasks => {
            const updatedTasks = [...prevTasks];
            const taskIndex = updatedTasks.findIndex(t => t.task_id === taskData.task_id);
            
            if (taskIndex >= 0) {
              // 更新现有任务
              updatedTasks[taskIndex] = taskData;
            } else {
              // 添加新任务到开头
              updatedTasks.unshift(taskData);
            }
            
            return updatedTasks;
          });
          
          console.log(`🔄 任务状态更新: ${taskData.task_id} -> ${taskData.status}`);
          
          // 调用回调函数
          if (taskData.status === TaskStatus.SUCCESS) {
            onTaskComplete?.(taskData.task_id);
          } else if (taskData.status === TaskStatus.FAILURE) {
            onTaskError?.(taskData.task_id, taskData.error_message || '任务执行失败');
          }
        }
        break;
        
      case 'tasks_cleared':
        console.log('🧹 任务清理完成:', message);
        Modal.success({
          title: '清理完成',
          content: `已清理 ${message.cleared_count} 个历史任务`
        });
        break;
        
      case 'error':
        console.error('❌ WebSocket错误:', message.message);
        Modal.error({
          title: '操作失败',
          content: message.message || '未知错误'
        });
        break;
        
      default:
        console.log('❓ 未知消息类型:', message.type);
    }
  };

  // 组件挂载时连接WebSocket
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // 手动清理：全部清空，可选确认  
  const clearAllTasks = () => {
    if (tasks.length === 0) return;
    
    // 输出调试信息
    console.log('📊 当前任务状态统计:', tasks.map(t => ({ name: t.file_name || t.name, status: t.status, stage: t.stage })));
    
    // 扩大可清理任务范围：包括已完成、失败、和非活跃状态的任务
    const activeTasks = tasks.filter(task => 
      task.status === TaskStatus.PENDING || 
      task.status === TaskStatus.STARTED || 
      task.status === TaskStatus.PROCESSING ||
      task.status === TaskStatus.RETRY
    );
    
    const clearableTasks = tasks.filter(task => !activeTasks.includes(task));
    
    console.log('🗑️ 可清理任务:', clearableTasks.length, '活跃任务:', activeTasks.length);
    
    if (clearableTasks.length === 0 && activeTasks.length > 0) {
      Modal.info({
        title: '暂无可清理任务',
        content: `当前有 ${activeTasks.length} 个正在运行的任务，请等待完成后再清理`
      });
      return;
    }
    
    if (tasks.length === 0) {
      Modal.info({
        title: '任务列表为空',
        content: '当前没有任何任务'
      });
      return;
    }
    
    // 如果所有任务都可以清理，或者有部分可清理任务
    Modal.confirm({
      title: '清理任务',
      content: clearableTasks.length > 0 
        ? `确定要清理 ${clearableTasks.length} 个非活跃任务吗？这将从后台彻底删除这些任务记录。${activeTasks.length > 0 ? `\n\n剩余 ${activeTasks.length} 个运行中的任务将保留。` : ''}`
        : `确定要清理所有 ${tasks.length} 个任务吗？这将从后台彻底删除所有任务记录。`,
      okText: '清理',
      cancelText: '取消',
      onOk: () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'clear_user_tasks' }));
        } else {
          Modal.error({
            title: '连接断开',
            content: '无法连接到服务器，请刷新页面重试'
          });
        }
      }
    });
  };

  // 手动刷新：重新请求用户任务列表
  const refreshTasks = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'get_user_tasks' }));
    } else {
      connectWebSocket();
    }
  };

  // 渲染单个任务
  const renderTask = (task: TaskInfo) => {
    // 安全地获取状态配置，提供默认值
    const statusConfig = STATUS_CONFIG[task.status] || {
      color: '#d9d9d9',
      text: '未知状态',
      icon: <QuestionCircleOutlined />,
      badgeStatus: 'default' as const
    };
    
    // 安全地获取阶段文本，提供默认值
    const stageText = STAGE_CONFIG[task.stage] || '未知阶段';
    
    // 确定任务状态的CSS类名
    const getTaskClassName = () => {
      if (task.status === TaskStatus.PROCESSING || task.status === TaskStatus.STARTED) {
        return 'task-item task-processing';
      }
      if (task.status === TaskStatus.SUCCESS) {
        return 'task-item task-success';
      }
      if (task.status === TaskStatus.FAILURE) {
        return 'task-item task-error';
      }
      return 'task-item';
    };
    
    return (
      <div key={task.task_id} className={getTaskClassName()}>
        <div className="task-header">
          <div className="task-info">
            <Badge status={statusConfig.badgeStatus} />
            <Text strong>{task.file_name || task.name || '图纸处理'}</Text>
            <Text type="secondary" className="task-progress-text">
              {stageText}
            </Text>
          </div>
          <Text type="secondary" className="task-progress-text">
            {Math.round(task.progress || 0)}%
          </Text>
        </div>
        
        <Progress 
          percent={task.progress} 
          size="small" 
          status={task.status === TaskStatus.FAILURE ? 'exception' : 
                  task.status === TaskStatus.SUCCESS ? 'success' : 'active'}
          showInfo={false}
          className="task-progress"
        />
        
        <div className="task-footer">
          <Text type="secondary" className="task-message">
            {task.message}
          </Text>
          <Space size="small">
            {task.status === TaskStatus.FAILURE && task.error_message && (
              <Tooltip title={task.error_message}>
                <Button size="small" type="text" icon={<EyeOutlined />} />
              </Tooltip>
            )}
          </Space>
        </div>
        
        {task.status === TaskStatus.FAILURE && (
          <Alert 
            message="处理失败" 
            description={task.error_message} 
            type="error" 
            style={{ marginTop: 8, fontSize: 12 }}
            showIcon
          />
        )}
      </div>
    );
  };

  // 获取活跃任务数量
  const getActiveTasksCount = () => {
    return tasks.filter(task => 
      task.status === TaskStatus.PROCESSING || 
      task.status === TaskStatus.STARTED ||
      task.status === TaskStatus.PENDING
    ).length;
  };

  return (
    <Card 
      size="small"
      className="upload-task-status"
      style={{ height: '100%', minHeight: 400 }}
      title={
        <Space className="connection-status">
          <span>实时任务状态</span>
          <Badge 
            count={getActiveTasksCount()} 
            style={{ backgroundColor: getActiveTasksCount() > 0 ? '#52c41a' : '#d9d9d9' }}
          />
          <Badge 
            status={connectionStatus === 'connected' ? 'success' : connectionStatus === 'connecting' ? 'processing' : 'error'} 
            text={connectionStatus === 'connected' ? '已连接' : connectionStatus === 'connecting' ? '连接中' : '已断开'}
          />
        </Space>
      }
      extra={
        <Space>
          <Button 
            size="small" 
            type="text" 
            onClick={clearAllTasks}
            disabled={tasks.length === 0}
          >
            清理
          </Button>
          <Button 
            size="small" 
            type="text" 
            icon={<SyncOutlined />} 
            onClick={refreshTasks}
          />
        </Space>
      }
      bodyStyle={{ 
        padding: '12px',
        height: 'calc(100% - 56px)',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {tasks.length > 0 ? (
        <div style={{ 
          flex: 1,
          overflowY: 'auto',
          paddingRight: 4
        }}>
          {tasks.map(renderTask)}
        </div>
      ) : (
        <div className="empty-state" style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center'
        }}>
          <ClockCircleOutlined style={{ fontSize: 32, color: '#d9d9d9', marginBottom: 12 }} />
          <Text type="secondary" style={{ fontSize: 16, marginBottom: 8 }}>暂无活跃任务</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            上传文件后，任务状态将在此处实时显示
          </Text>
        </div>
      )}
    </Card>
  );
};

export default UploadTaskStatus; 