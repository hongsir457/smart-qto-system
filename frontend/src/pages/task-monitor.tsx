'use client';

import { useState, useEffect } from 'react';
import TaskProgressMonitor from '../../components/TaskProgressMonitor';

interface DemoTask {
  id: string;
  name: string;
  stage: 'waiting' | 'started' | 'processing' | 'completed' | 'error' | 'retrying';
  progress: number;
  message: string;
  startTime?: number;
  endTime?: number;
  error?: string;
  results?: any;
}

export default function TaskMonitorDemo() {
  const [tasks, setTasks] = useState<DemoTask[]>([
    {
      id: '1',
      name: 'PDF文件上传',
      stage: 'completed',
      progress: 100,
      message: '文件上传完成',
      startTime: Date.now() - 30000,
      endTime: Date.now() - 25000,
      results: { fileId: 123, size: '2.5MB' }
    },
    {
      id: '2',
      name: 'OCR文字识别',
      stage: 'processing',
      progress: 65,
      message: '正在识别第 3/5 页...',
      startTime: Date.now() - 20000
    },
    {
      id: '3',
      name: '构件检测',
      stage: 'waiting',
      progress: 0,
      message: '等待OCR完成...'
    },
    {
      id: '4',
      name: '工程量计算',
      stage: 'error',
      progress: 30,
      message: '计算失败',
      startTime: Date.now() - 40000,
      endTime: Date.now() - 35000,
      error: '缺少必要的尺寸参数'
    },
    {
      id: '5',
      name: 'GPT分析',
      stage: 'retrying',
      progress: 20,
      message: '重试中... (第2次)',
      startTime: Date.now() - 15000
    }
  ]);

  const [mode, setMode] = useState<'compact' | 'detailed'>('detailed');

  // 模拟任务进度更新
  useEffect(() => {
    const interval = setInterval(() => {
      setTasks(prevTasks => 
        prevTasks.map(task => {
          if (task.stage === 'processing') {
            const newProgress = Math.min(100, task.progress + Math.random() * 5);
            return {
              ...task,
              progress: newProgress,
              stage: newProgress >= 100 ? 'completed' : 'processing',
              endTime: newProgress >= 100 ? Date.now() : undefined,
              message: newProgress >= 100 ? '处理完成' : `处理中... ${newProgress.toFixed(0)}%`
            };
          }
          if (task.stage === 'retrying') {
            const newProgress = Math.min(100, task.progress + Math.random() * 3);
            return {
              ...task,
              progress: newProgress,
              stage: newProgress >= 100 ? 'completed' : 'retrying',
              endTime: newProgress >= 100 ? Date.now() : undefined,
              message: newProgress >= 100 ? '重试成功' : `重试中... ${newProgress.toFixed(0)}%`
            };
          }
          return task;
        })
      );
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const addNewTask = () => {
    const newTask: DemoTask = {
      id: Date.now().toString(),
      name: `新任务 ${tasks.length + 1}`,
      stage: 'started',
      progress: 0,
      message: '任务开始...',
      startTime: Date.now()
    };
    setTasks(prev => [...prev, newTask]);
  };

  const handleTaskComplete = (taskId: string, results: any) => {
    console.log('任务完成:', taskId, results);
  };

  const handleTaskError = (taskId: string, error: string) => {
    console.log('任务失败:', taskId, error);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            任务进度监控演示
          </h1>
          <p className="text-gray-600 mb-6">
            这是 TaskProgressMonitor 组件的演示页面，展示了不同状态的任务进度监控。
          </p>
          
          <div className="flex space-x-4 mb-6">
            <button
              onClick={addNewTask}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              添加新任务
            </button>
            
            <div className="flex space-x-2">
              <button
                onClick={() => setMode('detailed')}
                className={`px-4 py-2 rounded-md transition-colors ${
                  mode === 'detailed'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                详细模式
              </button>
              <button
                onClick={() => setMode('compact')}
                className={`px-4 py-2 rounded-md transition-colors ${
                  mode === 'compact'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                紧凑模式
              </button>
            </div>
          </div>
        </div>

        <TaskProgressMonitor
          tasks={tasks}
          onTaskComplete={handleTaskComplete}
          onTaskError={handleTaskError}
          mode={mode}
          maxDisplayTasks={10}
          showHistory={true}
        />

        <div className="mt-8 bg-white rounded-lg border p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">使用说明</h2>
          <div className="space-y-4 text-sm text-gray-600">
            <div>
              <h3 className="font-medium text-gray-900">功能特点：</h3>
              <ul className="list-disc list-inside space-y-1 mt-2">
                <li>实时显示任务进度和状态</li>
                <li>支持多种任务状态：等待、进行中、完成、错误、重试</li>
                <li>可折叠的详细信息显示</li>
                <li>任务统计和过滤功能</li>
                <li>紧凑和详细两种显示模式</li>
                <li>动画效果和交互体验</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-900">状态说明：</h3>
              <div className="grid grid-cols-2 gap-4 mt-2">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span>⏳</span>
                    <span>等待中 - 任务排队等待执行</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span>▶️</span>
                    <span>已开始 - 任务开始执行</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span>⚙️</span>
                    <span>处理中 - 任务正在执行中</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span>✅</span>
                    <span>已完成 - 任务执行成功</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span>❌</span>
                    <span>错误 - 任务执行失败</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span>🔄</span>
                    <span>重试中 - 任务正在重试</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 