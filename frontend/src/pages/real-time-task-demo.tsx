// real-time-task-demo.tsx - 实时任务监控演示页面
import React, { useState, useEffect } from 'react';
import { Card, Button, Space, Input, Form, Select, notification, Divider, Row, Col, Tabs, Typography, Alert } from 'antd';
import { PlayCircleOutlined, PlusOutlined, ThunderboltOutlined, BugOutlined, ReloadOutlined } from '@ant-design/icons';
import RealTimeTaskMonitor, { TaskInfo, TaskStatus, TaskStage } from '../components/RealTimeTaskMonitor';

const { Option } = Select;
const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;

const RealTimeTaskDemo: React.FC = () => {
  const [demoTasks, setDemoTasks] = useState<TaskInfo[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationForm] = Form.useForm();

  // 模拟任务数据
  const DEMO_TASK_TEMPLATES = [
    {
      name: '图纸OCR识别任务',
      stages: [
        { stage: TaskStage.UPLOADING, message: '上传图纸文件', duration: 2000 },
        { stage: TaskStage.OCR_PROCESSING, message: '执行OCR文字识别', duration: 5000 },
        { stage: TaskStage.COMPONENT_DETECTION, message: '检测建筑构件', duration: 8000 },
        { stage: TaskStage.GPT_ANALYSIS, message: 'GPT智能分析', duration: 6000 },
        { stage: TaskStage.QUANTITY_CALCULATION, message: '计算工程量', duration: 4000 },
        { stage: TaskStage.COMPLETED, message: '任务完成', duration: 1000 }
      ]
    },
    {
      name: '工程量清单生成',
      stages: [
        { stage: TaskStage.QUEUED, message: '任务排队中', duration: 1000 },
        { stage: TaskStage.COMPONENT_DETECTION, message: '分析构件数据', duration: 3000 },
        { stage: TaskStage.QUANTITY_CALCULATION, message: '生成工程量清单', duration: 7000 },
        { stage: TaskStage.COMPLETED, message: '清单生成完成', duration: 1000 }
      ]
    },
    {
      name: '批量图纸处理',
      stages: [
        { stage: TaskStage.UPLOADING, message: '批量上传图纸', duration: 3000 },
        { stage: TaskStage.OCR_PROCESSING, message: '批量OCR处理', duration: 12000 },
        { stage: TaskStage.GPT_ANALYSIS, message: '智能分析处理', duration: 10000 },
        { stage: TaskStage.COMPLETED, message: '批量处理完成', duration: 1000 }
      ]
    }
  ];

  // 生成模拟任务ID
  const generateTaskId = () => {
    return `demo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  // 创建模拟任务
  const createDemoTask = (template: typeof DEMO_TASK_TEMPLATES[0], shouldFail: boolean = false): TaskInfo => {
    return {
      task_id: generateTaskId(),
      name: template.name,
      user_id: 1,
      status: TaskStatus.PENDING,
      stage: TaskStage.QUEUED,
      progress: 0,
      message: '任务已创建',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      metadata: { 
        template, 
        shouldFail,
        currentStageIndex: 0
      }
    };
  };

  // 模拟任务进度更新
  const simulateTaskProgress = async (task: TaskInfo) => {
    const template = task.metadata.template;
    const shouldFail = task.metadata.shouldFail;
    let currentStageIndex = task.metadata.currentStageIndex || 0;

    for (let i = currentStageIndex; i < template.stages.length; i++) {
      const stageInfo = template.stages[i];
      const isLastStage = i === template.stages.length - 1;
      
      // 模拟失败情况
      if (shouldFail && i === Math.floor(template.stages.length / 2)) {
        const failedTask: TaskInfo = {
          ...task,
          status: TaskStatus.FAILURE,
          stage: TaskStage.FAILED,
          progress: Math.floor((i / template.stages.length) * 100),
          message: '任务执行失败',
          error_message: '模拟的任务执行错误',
          updated_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          metadata: { ...task.metadata, currentStageIndex: i }
        };
        
        setDemoTasks(prev => prev.map(t => t.task_id === task.task_id ? failedTask : t));
        return;
      }

      // 更新阶段和进度
      const progress = isLastStage ? 100 : Math.floor(((i + 1) / template.stages.length) * 100);
      const status = isLastStage ? TaskStatus.SUCCESS : 
                    i === 0 ? TaskStatus.STARTED : TaskStatus.PROCESSING;

      const updatedTask: TaskInfo = {
        ...task,
        status,
        stage: stageInfo.stage,
        progress,
        message: stageInfo.message,
        updated_at: new Date().toISOString(),
        completed_at: isLastStage ? new Date().toISOString() : undefined,
        metadata: { ...task.metadata, currentStageIndex: i }
      };

      setDemoTasks(prev => prev.map(t => t.task_id === task.task_id ? updatedTask : t));

      // 等待指定时间
      await new Promise(resolve => setTimeout(resolve, stageInfo.duration));
    }
  };

  // 创建并运行模拟任务
  const runSimulationTask = async (templateIndex: number, shouldFail: boolean = false) => {
    const template = DEMO_TASK_TEMPLATES[templateIndex];
    const task = createDemoTask(template, shouldFail);
    
    setDemoTasks(prev => [task, ...prev].slice(0, 20)); // 最多保留20个任务
    
    // 开始模拟进度
    await simulateTaskProgress(task);
  };

  // 批量创建任务
  const createBatchTasks = async () => {
    setIsSimulating(true);
    
    const promises = DEMO_TASK_TEMPLATES.map((template, index) => {
      const shouldFail = Math.random() < 0.2; // 20%的失败率
      return runSimulationTask(index, shouldFail);
    });
    
    await Promise.all(promises);
    setIsSimulating(false);
  };

  // 清理演示数据
  const clearDemoData = () => {
    setDemoTasks([]);
    notification.info({
      message: '演示数据已清理',
      description: '所有模拟任务已被清除',
      duration: 2
    });
  };

  // 任务回调处理
  const handleTaskUpdate = (task: TaskInfo) => {
    console.log('任务更新:', task);
  };

  const handleTaskComplete = (task: TaskInfo) => {
    console.log('任务完成:', task);
  };

  const handleTaskError = (task: TaskInfo) => {
    console.log('任务失败:', task);
  };

  // 渲染使用说明
  const renderInstructions = () => (
    <Card title="使用说明" style={{ marginBottom: 24 }}>
      <Paragraph>
        这个演示展示了基于WebSocket和Celery的实时任务状态推送系统的功能：
      </Paragraph>
      
      <ul>
        <li><strong>实时状态更新</strong>：任务状态变化会立即推送到前端显示</li>
        <li><strong>进度跟踪</strong>：显示任务的详细执行进度和当前阶段</li>
        <li><strong>WebSocket连接</strong>：建立持久连接接收实时更新</li>
        <li><strong>任务管理</strong>：支持查看详情、取消任务等操作</li>
        <li><strong>统计信息</strong>：实时显示任务统计数据</li>
      </ul>

      <Alert
        message="注意"
        description="这是演示页面，实际的任务推送需要连接到后端WebSocket服务。当前显示的是模拟数据。"
        type="info"
        showIcon
        style={{ marginTop: 16 }}
      />
    </Card>
  );

  // 渲染控制面板
  const renderControlPanel = () => (
    <Card title="任务控制面板" style={{ marginBottom: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Text strong>快速操作：</Text>
          <div style={{ marginTop: 8 }}>
            <Space wrap>
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={() => runSimulationTask(0)}
                loading={isSimulating}
              >
                创建OCR任务
              </Button>
              
              <Button 
                icon={<ThunderboltOutlined />}
                onClick={() => runSimulationTask(1)}
                loading={isSimulating}
              >
                创建清单任务
              </Button>
              
              <Button 
                icon={<PlayCircleOutlined />}
                onClick={() => runSimulationTask(2)}
                loading={isSimulating}
              >
                创建批量任务
              </Button>
              
              <Button 
                icon={<BugOutlined />}
                danger
                onClick={() => runSimulationTask(0, true)}
                loading={isSimulating}
              >
                创建失败任务
              </Button>
            </Space>
          </div>
        </div>

        <Divider />

        <div>
          <Text strong>批量操作：</Text>
          <div style={{ marginTop: 8 }}>
            <Space>
              <Button 
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={createBatchTasks}
                loading={isSimulating}
              >
                批量创建任务
              </Button>
              
              <Button 
                icon={<ReloadOutlined />}
                onClick={clearDemoData}
              >
                清理演示数据
              </Button>
            </Space>
          </div>
        </div>
      </Space>
    </Card>
  );

  // 渲染API示例
  const renderApiExample = () => (
    <Card title="API使用示例">
      <Tabs defaultActiveKey="1">
        <TabPane tab="组件使用" key="1">
          <pre style={{ 
            backgroundColor: '#f6f8fa', 
            padding: 16, 
            borderRadius: 6,
            overflow: 'auto'
          }}>
{`import RealTimeTaskMonitor from '../components/RealTimeTaskMonitor';

// 基本使用
<RealTimeTaskMonitor 
  mode="detailed"
  maxDisplayTasks={10}
  showStatistics={true}
  autoConnect={true}
  onTaskUpdate={(task) => console.log('任务更新:', task)}
  onTaskComplete={(task) => console.log('任务完成:', task)}
  onTaskError={(task) => console.log('任务失败:', task)}
/>

// 紧凑模式
<RealTimeTaskMonitor 
  mode="compact"
  maxDisplayTasks={5}
  showStatistics={false}
/>`}
          </pre>
        </TabPane>

        <TabPane tab="WebSocket连接" key="2">
          <pre style={{ 
            backgroundColor: '#f6f8fa', 
            padding: 16, 
            borderRadius: 6,
            overflow: 'auto'
          }}>
{`// WebSocket连接示例
const ws = new WebSocket('ws://localhost:8000/ws/realtime/connection_id?token=jwt_token');

// 订阅任务更新
ws.send(JSON.stringify({
  type: 'subscribe_task',
  task_id: 'task_id_here'
}));

// 获取用户任务
ws.send(JSON.stringify({
  type: 'get_user_tasks'
}));

// 取消任务
ws.send(JSON.stringify({
  type: 'cancel_task',
  task_id: 'task_id_here'
}));`}
          </pre>
        </TabPane>

        <TabPane tab="后端集成" key="3">
          <pre style={{ 
            backgroundColor: '#f6f8fa', 
            padding: 16, 
            borderRadius: 6,
            overflow: 'auto'
          }}>
{`# 后端Celery任务示例
from app.tasks import status_pusher, track_progress
from app.tasks.real_time_task_manager import TaskStage

@track_progress()
def process_drawing(file_path, user_id=None, progress_tracker=None):
    # 更新进度
    await progress_tracker.update_stage(
        TaskStage.UPLOADING, 
        "正在上传文件", 
        10
    )
    
    # 执行OCR
    await progress_tracker.update_stage(
        TaskStage.OCR_PROCESSING,
        "执行OCR识别",
        30
    )
    
    # 完成任务
    await progress_tracker.complete({
        "result": "处理完成",
        "file_count": 1
    })`}
          </pre>
        </TabPane>
      </Tabs>
    </Card>
  );

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>实时任务监控系统演示</Title>
      
      <Row gutter={24}>
        <Col xs={24} lg={14}>
          {renderInstructions()}
          {renderControlPanel()}
          
          <Card title="实时任务监控组件">
            <RealTimeTaskMonitor
              mode="detailed"
              maxDisplayTasks={15}
              showStatistics={true}
              autoConnect={false} // 演示模式不自动连接
              onTaskUpdate={handleTaskUpdate}
              onTaskComplete={handleTaskComplete}
              onTaskError={handleTaskError}
            />
          </Card>
        </Col>
        
        <Col xs={24} lg={10}>
          {renderApiExample()}
          
          <Card 
            title="演示任务列表" 
            style={{ marginTop: 24 }}
            extra={<Text type="secondary">共 {demoTasks.length} 个任务</Text>}
          >
            {demoTasks.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 24, color: '#8c8c8c' }}>
                暂无演示任务，点击上方按钮创建
              </div>
            ) : (
              <div style={{ maxHeight: 400, overflow: 'auto' }}>
                {demoTasks.map(task => (
                  <div key={task.task_id} style={{ 
                    padding: 8, 
                    marginBottom: 8, 
                    border: '1px solid #f0f0f0',
                    borderRadius: 4,
                    backgroundColor: '#fafafa'
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 500 }}>
                      {task.name}
                    </div>
                    <div style={{ fontSize: 11, color: '#666' }}>
                      状态: {task.status} | 进度: {task.progress}%
                    </div>
                    <div style={{ fontSize: 10, color: '#999' }}>
                      {task.message}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default RealTimeTaskDemo; 