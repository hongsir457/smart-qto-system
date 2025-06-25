'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface TaskProgress {
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

interface TaskProgressMonitorProps {
  tasks: TaskProgress[];
  onTaskComplete?: (taskId: string, results: any) => void;
  onTaskError?: (taskId: string, error: string) => void;
  className?: string;
  mode?: 'compact' | 'detailed' | 'grid';
  showHistory?: boolean;
  maxDisplayTasks?: number;
}

export default function TaskProgressMonitor({
  tasks = [],
  onTaskComplete,
  onTaskError,
  className = '',
  mode = 'detailed',
  showHistory = false,
  maxDisplayTasks = 10
}: TaskProgressMonitorProps) {
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'error'>('all');

  // 任务状态统计
  const taskStats = tasks.reduce((stats, task) => {
    stats.total++;
    if (task.stage === 'completed') stats.completed++;
    else if (task.stage === 'error') stats.error++;
    else if (['processing', 'started', 'retrying'].includes(task.stage)) stats.active++;
    else stats.waiting++;
    return stats;
  }, { total: 0, active: 0, completed: 0, error: 0, waiting: 0 });

  // 过滤任务
  const filteredTasks = tasks.filter(task => {
    if (filter === 'all') return true;
    if (filter === 'active') return ['waiting', 'started', 'processing', 'retrying'].includes(task.stage);
    if (filter === 'completed') return task.stage === 'completed';
    if (filter === 'error') return task.stage === 'error';
    return true;
  }).slice(0, maxDisplayTasks);

  const toggleTaskExpansion = useCallback((taskId: string) => {
    setExpandedTasks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(taskId)) {
        newSet.delete(taskId);
      } else {
        newSet.add(taskId);
      }
      return newSet;
    });
  }, []);

  const getStageIcon = (stage: string) => {
    switch (stage) {
      case 'waiting': return '⏳';
      case 'started': return '▶️';
      case 'processing': return '⚙️';
      case 'completed': return '✅';
      case 'error': return '❌';
      case 'retrying': return '🔄';
      default: return '📋';
    }
  };

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'waiting': return 'text-gray-500 bg-gray-100';
      case 'started': return 'text-blue-600 bg-blue-100';
      case 'processing': return 'text-blue-600 bg-blue-100';
      case 'completed': return 'text-green-600 bg-green-100';
      case 'error': return 'text-red-600 bg-red-100';
      case 'retrying': return 'text-yellow-600 bg-yellow-100';
      default: return 'text-gray-500 bg-gray-100';
    }
  };

  const formatDuration = (startTime?: number, endTime?: number) => {
    if (!startTime) return '';
    const duration = (endTime || Date.now()) - startTime;
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    if (minutes > 0) {
      return `${minutes}分${seconds % 60}秒`;
    }
    return `${seconds}秒`;
  };

  // 紧凑模式渲染
  const renderCompactTask = (task: TaskProgress) => (
    <motion.div
      key={task.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="flex items-center space-x-3 p-2 rounded-lg border bg-white hover:shadow-sm transition-shadow"
    >
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${getStageColor(task.stage)}`}>
        {getStageIcon(task.stage)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-gray-900 truncate">{task.name}</p>
          <span className="text-xs text-gray-500">{task.progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
          <div
            className={`h-1.5 rounded-full transition-all duration-300 ${
              task.stage === 'error' ? 'bg-red-500' :
              task.stage === 'completed' ? 'bg-green-500' :
              'bg-blue-500'
            }`}
            style={{ width: `${Math.min(100, Math.max(0, task.progress))}%` }}
          />
        </div>
      </div>
    </motion.div>
  );

  // 详细模式渲染
  const renderDetailedTask = (task: TaskProgress) => {
    const isExpanded = expandedTasks.has(task.id);
    
    return (
      <motion.div
        key={task.id}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="bg-white rounded-lg border shadow-sm overflow-hidden"
      >
        <div 
          className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => toggleTaskExpansion(task.id)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${getStageColor(task.stage)}`}>
                {getStageIcon(task.stage)}
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-900">{task.name}</h3>
                <p className="text-xs text-gray-500 mt-1">{task.message}</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-sm font-medium text-gray-900">{task.progress}%</span>
              <svg 
                className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
          
          <div className="mt-3">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <motion.div
                className={`h-2 rounded-full transition-all duration-300 ${
                  task.stage === 'error' ? 'bg-red-500' :
                  task.stage === 'completed' ? 'bg-green-500' :
                  task.stage === 'processing' ? 'bg-blue-500' :
                  'bg-gray-400'
                }`}
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, Math.max(0, task.progress))}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
          </div>
        </div>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-t border-gray-100"
            >
              <div className="p-4 space-y-3">
                {task.startTime && (
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>持续时间:</span>
                    <span>{formatDuration(task.startTime, task.endTime)}</span>
                  </div>
                )}
                
                {task.error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                    <strong>错误:</strong> {task.error}
                  </div>
                )}
                
                {task.results && task.stage === 'completed' && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded">
                    <div className="text-sm font-medium text-green-800 mb-2">处理结果:</div>
                    <div className="text-xs text-green-700">
                      {typeof task.results === 'object' ? (
                        <pre className="whitespace-pre-wrap">
                          {JSON.stringify(task.results, null, 2)}
                        </pre>
                      ) : (
                        <span>{task.results}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  };

  if (tasks.length === 0) {
    return (
      <div className={`task-progress-monitor ${className}`}>
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">📋</div>
          <p>暂无任务</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`task-progress-monitor ${className}`}>
      {/* 统计信息 */}
      <div className="bg-white rounded-lg border p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-gray-900">任务监控</h2>
          <div className="flex space-x-2">
            {(['all', 'active', 'completed', 'error'] as const).map(filterType => (
              <button
                key={filterType}
                onClick={() => setFilter(filterType)}
                className={`px-3 py-1 text-xs rounded-full transition-colors ${
                  filter === filterType
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {filterType === 'all' && `全部 (${taskStats.total})`}
                {filterType === 'active' && `进行中 (${taskStats.active})`}
                {filterType === 'completed' && `已完成 (${taskStats.completed})`}
                {filterType === 'error' && `错误 (${taskStats.error})`}
              </button>
            ))}
          </div>
        </div>
        
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{taskStats.total}</div>
            <div className="text-xs text-gray-500">总任务</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{taskStats.active}</div>
            <div className="text-xs text-gray-500">进行中</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{taskStats.completed}</div>
            <div className="text-xs text-gray-500">已完成</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{taskStats.error}</div>
            <div className="text-xs text-gray-500">错误</div>
          </div>
        </div>
      </div>

      {/* 任务列表 */}
      <div className="space-y-3">
        <AnimatePresence>
          {filteredTasks.map(task => 
            mode === 'compact' ? renderCompactTask(task) : renderDetailedTask(task)
          )}
        </AnimatePresence>
      </div>

      {tasks.length > maxDisplayTasks && (
        <div className="mt-4 text-center">
          <button className="text-sm text-blue-600 hover:text-blue-800">
            查看更多任务 ({tasks.length - maxDisplayTasks} 个隐藏)
          </button>
        </div>
      )}
    </div>
  );
} 