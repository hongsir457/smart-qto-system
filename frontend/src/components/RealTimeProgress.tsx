'use client';

import { useState, useEffect } from 'react';
import ProgressWebSocket from './ProgressWebSocket';

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

interface RealTimeProgressProps {
  taskId: string;
  onComplete?: (data: ProgressData) => void;
  onError?: (data: ProgressData) => void;
  className?: string;
}

export default function RealTimeProgress({
  taskId,
  onComplete,
  onError,
  className = ''
}: RealTimeProgressProps) {
  const [currentProgress, setCurrentProgress] = useState<ProgressData>({
    stage: 'waiting',
    progress: 0,
    message: '等待开始...'
  });
  const [progressHistory, setProgressHistory] = useState<ProgressData[]>([]);
  const [isCompleted, setIsCompleted] = useState(false);
  const [hasError, setHasError] = useState(false);

  const handleProgress = (data: ProgressData) => {
    setCurrentProgress(data);
    setProgressHistory(prev => [...prev, { ...data, timestamp: Date.now() } as any]);
    
    if (data.error) {
      setHasError(true);
    }
  };

  const handleComplete = (data: ProgressData) => {
    setCurrentProgress(data);
    setProgressHistory(prev => [...prev, { ...data, timestamp: Date.now() } as any]);
    setIsCompleted(true);
    
    if (onComplete) {
      onComplete(data);
    }
  };

  const handleError = (data: ProgressData) => {
    setCurrentProgress(data);
    setProgressHistory(prev => [...prev, { ...data, timestamp: Date.now() } as any]);
    setHasError(true);
    
    if (onError) {
      onError(data);
    }
  };

  const getStageDisplayName = (stage: string) => {
    const stageMap: { [key: string]: string } = {
      'waiting': '等待中',
      'started': '已开始',
      'processing': '处理中',
      'completed': '已完成',
      'error': '错误',
      'retrying': '重试中'
    };
    return stageMap[stage] || stage;
  };

  const getProgressColor = () => {
    if (hasError) return 'bg-red-500';
    if (isCompleted) return 'bg-green-500';
    if (currentProgress.stage === 'retrying') return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  const getProgressBarClass = () => {
    const baseClass = 'h-2 rounded-full transition-all duration-300 ease-out';
    return `${baseClass} ${getProgressColor()}`;
  };

  return (
    <div className={`real-time-progress ${className}`}>
      {/* WebSocket连接状态 */}
      <ProgressWebSocket
        taskId={taskId}
        onProgress={handleProgress}
        onComplete={handleComplete}
        onError={handleError}
        autoConnect={true}
      />

      {/* 主进度显示 */}
      <div className="mt-4 space-y-3">
        {/* 当前状态 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className={`inline-block w-3 h-3 rounded-full ${
              hasError ? 'bg-red-500' : 
              isCompleted ? 'bg-green-500' : 
              currentProgress.stage === 'retrying' ? 'bg-yellow-500' : 
              'bg-blue-500'
            } ${currentProgress.stage === 'processing' ? 'animate-pulse' : ''}`}></span>
            <span className="font-medium text-gray-700">
              {getStageDisplayName(currentProgress.stage)}
            </span>
          </div>
          <span className="text-sm text-gray-500">
            {currentProgress.progress}%
          </span>
        </div>

        {/* 进度条 */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={getProgressBarClass()}
            style={{ width: `${Math.max(0, Math.min(100, currentProgress.progress))}%` }}
          ></div>
        </div>

        {/* 当前消息 */}
        <div className={`text-sm ${
          hasError ? 'text-red-600' : 
          isCompleted ? 'text-green-600' : 
          'text-gray-600'
        }`}>
          {currentProgress.message}
        </div>

        {/* 警告信息 */}
        {currentProgress.warning && (
          <div className="text-sm text-yellow-600 bg-yellow-50 p-2 rounded">
            ⚠️ {currentProgress.warning}
          </div>
        )}

        {/* 完成结果摘要 */}
        {isCompleted && currentProgress.results && (
          <div className="text-sm text-green-600 bg-green-50 p-3 rounded">
            <div className="font-medium mb-1">处理完成</div>
            {currentProgress.results.total_components !== undefined && (
              <div>识别构件数量: {currentProgress.results.total_components}</div>
            )}
            {currentProgress.results.text_blocks !== undefined && (
              <div>文字块数量: {currentProgress.results.text_blocks}</div>
            )}
            {currentProgress.results.total_text !== undefined && (
              <div>文字总长度: {currentProgress.results.total_text}</div>
            )}
            {currentProgress.results.quantities_calculated !== undefined && (
              <div>工程量计算: {currentProgress.results.quantities_calculated ? '已完成' : '未完成'}</div>
            )}
            {currentProgress.compressed && (
              <div className="text-yellow-600">数据已压缩存储</div>
            )}
          </div>
        )}

        {/* 进度历史（可折叠） */}
        {progressHistory.length > 1 && (
          <details className="mt-4">
            <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
              查看详细进度历史 ({progressHistory.length} 条记录)
            </summary>
            <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
              {progressHistory.map((item, index) => (
                <div key={index} className="text-xs text-gray-500 flex justify-between">
                  <span>{item.message}</span>
                  <span>{item.progress}%</span>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
} 