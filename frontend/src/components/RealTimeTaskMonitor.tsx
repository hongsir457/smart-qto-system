// RealTimeTaskMonitor.tsx - 实时任务监控组件
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, Badge, Progress, Button, Tooltip, notification, Modal, Space, Statistic, Row, Col } from 'antd';
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  EyeOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import './RealTimeTaskMonitor.css';

// 任务状态枚举
export enum TaskStatus {
  PENDING = 'pending',
  STARTED = 'started', 
  PROCESSING = 'processing',
  SUCCESS = 'success',
  FAILURE = 'failure',
  RETRY = 'retry',
  REVOKED = 'revoked'
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
  user_id?: number;
  status: TaskStatus;
  stage: TaskStage;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  results?: any;
  metadata?: any;
  duration?: number;
}

// WebSocket消息类型
interface WebSocketMessage {
  type: string;
  task_id?: string;
  data?: any;
  tasks?: TaskInfo[];
  stats?: any;
  [key: string]: any;
}

// 组件属性
interface RealTimeTaskMonitorProps {
  mode?: 'detailed' | 'compact';
  maxDisplayTasks?: number;
  showStatistics?: boolean;
  autoConnect?: boolean;
  onTaskUpdate?: (task: TaskInfo) => void;
  onTaskComplete?: (task: TaskInfo) => void;
  onTaskError?: (task: TaskInfo) => void;
}

// 状态配置
const STATUS_CONFIG = {
  [TaskStatus.PENDING]: {
    color: '#faad14',
    text: '等待中',
    icon: <ClockCircleOutlined />,
    bgColor: '#fff7e6'
  },
  [TaskStatus.STARTED]: {
    color: '#1890ff',
    text: '已开始',
    icon: <PlayCircleOutlined />,
    bgColor: '#e6f7ff'
  },
  [TaskStatus.PROCESSING]: {
    color: '#722ed1',
    text: '处理中',
    icon: <SyncOutlined spin />,
    bgColor: '#f9f0ff'
  },
  [TaskStatus.SUCCESS]: {
    color: '#52c41a',
    text: '成功',
    icon: <CheckCircleOutlined />,
    bgColor: '#f6ffed'
  },
  [TaskStatus.FAILURE]: {
    color: '#ff4d4f',
    text: '失败',
    icon: <CloseCircleOutlined />,
    bgColor: '#fff2f0'
  },
  [TaskStatus.RETRY]: {
    color: '#fa8c16',
    text: '重试中',
    icon: <ReloadOutlined spin />,
    bgColor: '#fff7e6'
  },
  [TaskStatus.REVOKED]: {
    color: '#8c8c8c',
    text: '已取消',
    icon: <StopOutlined />,
    bgColor: '#f5f5f5'
  }
};

// 阶段配置
const STAGE_CONFIG = {
  [TaskStage.QUEUED]: '排队中',
  [TaskStage.UPLOADING]: '上传中',
  [TaskStage.OCR_PROCESSING]: 'OCR处理',
  [TaskStage.COMPONENT_DETECTION]: '构件检测',
  [TaskStage.GPT_ANALYSIS]: 'GPT分析',
  [TaskStage.QUANTITY_CALCULATION]: '工程量计算',
  [TaskStage.COMPLETED]: '已完成',
  [TaskStage.FAILED]: '失败'
};

const RealTimeTaskMonitor: React.FC<RealTimeTaskMonitorProps> = ({
  mode = 'detailed',
  maxDisplayTasks = 10,
  showStatistics = true,
  autoConnect = true,
  onTaskUpdate,
  onTaskComplete,
  onTaskError
}) => {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [statistics, setStatistics] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [selectedTask, setSelectedTask] = useState<TaskInfo | null>(null);
  const [showTaskDetails, setShowTaskDetails] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const connectionIdRef = useRef<string>('');

  // 生成连接ID
  const generateConnectionId = useCallback(() => {
    return `task_monitor_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // WebSocket连接
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    connectionIdRef.current = generateConnectionId();
    
    const token = localStorage.getItem('token');
    if (!token) {
      setConnectionStatus('disconnected');
      notification.error({
        message: '连接失败',
        description: '缺少认证令牌，请重新登录',
        duration: 3
      });
      return;
    }
    
    // 使用正确的WebSocket认证端点
    const wsUrl = `ws://localhost:8000/ws/realtime/${connectionIdRef.current}?token=${encodeURIComponent(token)}`;
    console.log('连接WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setIsConnected(true);
      setConnectionStatus('connected');
      notification.success({
        message: '连接成功',
        description: '实时任务监控已连接',
        duration: 2
      });
      
      // 连接成功后会自动接收用户任务列表，无需手动请求
      
      // 获取统计信息
      if (showStatistics) {
        ws.send(JSON.stringify({ type: 'get_task_stats' }));
      }
    };
    
    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        console.log('收到WebSocket消息:', message);
        
        switch (message.type) {
          case 'connection':
            // 连接确认消息
            console.log('WebSocket连接确认:', message);
            break;
            
          case 'user_tasks':
            // 用户任务列表
            if (message.tasks && Array.isArray(message.tasks)) {
              setTasks(message.tasks.slice(0, maxDisplayTasks));
              console.log(`收到任务列表，共${message.tasks.length}个任务`);
            }
            break;
            
          case 'task_update':
            // 单个任务更新
            if (message.task_id && message.data) {
              const taskData = message.data;
              setTasks(prevTasks => {
                const existingIndex = prevTasks.findIndex(t => t.task_id === message.task_id);
                if (existingIndex >= 0) {
                  const updatedTasks = [...prevTasks];
                  updatedTasks[existingIndex] = taskData;
                  return updatedTasks;
                } else {
                  // 新任务，添加到列表顶部
                  return [taskData, ...prevTasks.slice(0, maxDisplayTasks - 1)];
                }
              });
              
              // 调用回调函数
              if (onTaskUpdate) {
                onTaskUpdate(taskData);
              }
              
              // 特殊状态处理
              if (taskData.status === TaskStatus.SUCCESS && onTaskComplete) {
                onTaskComplete(taskData);
              }
              if (taskData.status === TaskStatus.FAILURE && onTaskError) {
                onTaskError(taskData);
              }
            }
            break;
            
          case 'statistics':
            // 统计信息更新
            if (message.stats) {
              setStatistics(message.stats);
            }
            break;
            
          case 'notification':
            // 系统通知
            if (message.level === 'success') {
              notification.success({
                message: message.title || '成功',
                description: message.message,
                duration: 3
              });
            } else if (message.level === 'error') {
              notification.error({
                message: message.title || '错误',
                description: message.message,
                duration: 5
              });
            } else {
              notification.info({
                message: message.title || '通知',
                description: message.message,
                duration: 3
              });
            }
            break;
            
          case 'drawing_deleted':
            // 图纸删除事件
            if (message.data) {
              const { drawing_id, filename, deleted_tasks } = message.data;
              
              // 从任务列表中移除相关任务
              setTasks(prevTasks => {
                const updatedTasks = prevTasks.filter(task => {
                  const taskDrawingId = task.metadata?.drawing_id;
                  return taskDrawingId !== drawing_id;
                });
                
                console.log(`图纸删除: ${filename}, 移除 ${prevTasks.length - updatedTasks.length} 个任务`);
                return updatedTasks;
              });
              
              // 显示通知
              notification.info({
                message: '图纸已删除',
                description: `图纸 "${filename}" 及其相关任务已清理`,
                duration: 4
              });
            }
            break;
            
          default:
            console.log('未处理的WebSocket消息类型:', message.type, message);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error, event.data);
      }
    };
    
    ws.onclose = (event) => {
      setIsConnected(false);
      setConnectionStatus('disconnected');
      wsRef.current = null;
      
      // 根据关闭代码决定是否重连
      if (event.code === 1008) {
        // 认证失败，不重连
        notification.error({
          message: '认证失败',
          description: '请重新登录后再试',
          duration: 5
        });
        return;
      }
      
      // 自动重连
      if (autoConnect) {
        reconnectTimerRef.current = setTimeout(() => {
          connectWebSocket();
        }, 3000);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      notification.error({
        message: '连接错误',
        description: '实时任务监控连接失败',
        duration: 3
      });
    };
    
    wsRef.current = ws;
  }, [autoConnect, showStatistics, generateConnectionId, maxDisplayTasks, onTaskUpdate, onTaskComplete, onTaskError]);

  // 清理已完成任务
  const clearCompletedTasks = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'clear_completed_tasks' }));
    }
  }, []);

  // 刷新任务列表
  const refreshTasks = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'get_user_tasks' }));
    } else {
      connectWebSocket();
    }
  }, [connectWebSocket]);

  // 订阅任务
  const subscribeToTask = useCallback((taskId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe_task',
        task_id: taskId
      }));
    }
  }, []);

  // 取消任务
  const cancelTask = useCallback((taskId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'cancel_task',
        task_id: taskId
      }));
    }
  }, []);

  // 格式化持续时间
  const formatDuration = (duration?: number): string => {
    if (!duration) return '-';
    
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    
    if (minutes > 0) {
      return `${minutes}分${seconds}秒`;
    }
    return `${seconds}秒`;
  };

  // 获取进度条颜色
  const getProgressColor = (status: TaskStatus): string => {
    switch (status) {
      case TaskStatus.SUCCESS:
        return '#52c41a';
      case TaskStatus.FAILURE:
        return '#ff4d4f';
      case TaskStatus.PROCESSING:
        return '#1890ff';
      default:
        return '#faad14';
    }
  };

  // 渲染任务卡片
  const renderTaskCard = (task: TaskInfo) => {
    const statusConfig = STATUS_CONFIG[task.status];
    
    return (
      <motion.div
        key={task.task_id}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="task-card"
      >
        <Card
          size="small"
          style={{ 
            marginBottom: 8,
            backgroundColor: statusConfig.bgColor,
            border: `1px solid ${statusConfig.color}`
          }}
          bodyStyle={{ padding: mode === 'compact' ? '8px 12px' : '12px 16px' }}
        >
          <div className="task-header">
            <div className="task-title">
              <Badge 
                status={task.status === TaskStatus.SUCCESS ? 'success' : 
                       task.status === TaskStatus.FAILURE ? 'error' : 'processing'}
                text={task.name}
              />
              <span style={{ color: statusConfig.color, marginLeft: 8 }}>
                {statusConfig.icon} {statusConfig.text}
              </span>
            </div>
            
            <div className="task-actions">
              <Tooltip title="查看详情">
                <Button
                  type="text"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => {
                    setSelectedTask(task);
                    setShowTaskDetails(true);
                  }}
                />
              </Tooltip>
              
              {[TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PROCESSING].includes(task.status) && (
                <Tooltip title="取消任务">
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<StopOutlined />}
                    onClick={() => cancelTask(task.task_id)}
                  />
                </Tooltip>
              )}
            </div>
          </div>
          
          {mode === 'detailed' && (
            <div className="task-details">
              <div className="task-stage">
                阶段: {STAGE_CONFIG[task.stage] || task.stage}
              </div>
              
              <div className="task-progress">
                <Progress
                  percent={task.progress}
                  size="small"
                  strokeColor={getProgressColor(task.status)}
                  showInfo={false}
                />
                <span className="progress-text">{task.progress}%</span>
              </div>
              
              <div className="task-message">
                {task.message}
              </div>
              
              <div className="task-meta">
                <span>持续时间: {formatDuration(task.duration)}</span>
                <span>更新时间: {new Date(task.updated_at).toLocaleTimeString()}</span>
              </div>
            </div>
          )}
        </Card>
      </motion.div>
    );
  };

  // 渲染统计信息
  const renderStatistics = () => {
    if (!showStatistics || !statistics) return null;
    
    return (
      <Card title="任务统计" size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic 
              title="总计" 
              value={statistics.total} 
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="等待中" 
              value={statistics.pending} 
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="处理中" 
              value={statistics.processing} 
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="已完成" 
              value={statistics.completed} 
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
        </Row>
      </Card>
    );
  };

  // 渲染任务详情模态框
  const renderTaskDetailsModal = () => {
    if (!selectedTask) return null;
    
    return (
      <Modal
        title={`任务详情 - ${selectedTask.name}`}
        open={showTaskDetails}
        onCancel={() => setShowTaskDetails(false)}
        footer={null}
        width={600}
      >
        <div className="task-detail-content">
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <strong>任务ID:</strong> {selectedTask.task_id}
            </Col>
            <Col span={12}>
              <strong>状态:</strong> 
              <Badge 
                status={selectedTask.status === TaskStatus.SUCCESS ? 'success' : 
                       selectedTask.status === TaskStatus.FAILURE ? 'error' : 'processing'}
                text={STATUS_CONFIG[selectedTask.status].text}
                style={{ marginLeft: 8 }}
              />
            </Col>
            <Col span={12}>
              <strong>阶段:</strong> {STAGE_CONFIG[selectedTask.stage]}
            </Col>
            <Col span={12}>
              <strong>进度:</strong> {selectedTask.progress}%
            </Col>
            <Col span={24}>
              <strong>消息:</strong> {selectedTask.message}
            </Col>
            {selectedTask.error_message && (
              <Col span={24}>
                <strong>错误信息:</strong> 
                <div style={{ color: '#ff4d4f', marginTop: 4 }}>
                  {selectedTask.error_message}
                </div>
              </Col>
            )}
            <Col span={12}>
              <strong>创建时间:</strong> {new Date(selectedTask.created_at).toLocaleString()}
            </Col>
            <Col span={12}>
              <strong>更新时间:</strong> {new Date(selectedTask.updated_at).toLocaleString()}
            </Col>
            {selectedTask.duration && (
              <Col span={12}>
                <strong>持续时间:</strong> {formatDuration(selectedTask.duration)}
              </Col>
            )}
            {selectedTask.results && (
              <Col span={24}>
                <strong>结果:</strong>
                <pre style={{ 
                  backgroundColor: '#f5f5f5', 
                  padding: 8, 
                  borderRadius: 4,
                  marginTop: 4,
                  maxHeight: 200,
                  overflow: 'auto'
                }}>
                  {JSON.stringify(selectedTask.results, null, 2)}
                </pre>
              </Col>
            )}
          </Row>
        </div>
      </Modal>
    );
  };

  // 生命周期管理
  useEffect(() => {
    if (autoConnect) {
      connectWebSocket();
    }
    
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [autoConnect, connectWebSocket]);

  return (
    <div className="real-time-task-monitor">
      <div className="monitor-header">
        <h3>实时任务监控</h3>
        <div className="connection-status">
          <Badge 
            status={connectionStatus === 'connected' ? 'success' : 
                   connectionStatus === 'connecting' ? 'processing' : 'error'}
            text={connectionStatus === 'connected' ? '已连接' : 
                 connectionStatus === 'connecting' ? '连接中' : '未连接'}
          />
          {!isConnected && (
            <Button 
              type="primary" 
              size="small" 
              style={{ marginLeft: 8 }}
              onClick={connectWebSocket}
            >
              重新连接
            </Button>
          )}
        </div>
      </div>
      
      {renderStatistics()}
      
      <div className="task-list">
        <AnimatePresence>
          {tasks.map(task => renderTaskCard(task))}
        </AnimatePresence>
        
        {tasks.length === 0 && (
          <div className="empty-state">
            <p style={{ textAlign: 'center', color: '#8c8c8c', marginTop: 32 }}>
              暂无任务
            </p>
          </div>
        )}
      </div>
      
      {renderTaskDetailsModal()}
    </div>
  );
};

export default RealTimeTaskMonitor; 