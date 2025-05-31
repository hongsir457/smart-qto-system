import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import RealTimeProgress from '../RealTimeProgress';

interface ComponentDetection {
  walls: Array<{
    bbox: number[];
    confidence: number;
    dimensions: { width: number; height: number; };
  }>;
  columns: Array<{
    bbox: number[];
    confidence: number;
    dimensions: { width: number; height: number; };
  }>;
  beams: Array<{
    bbox: number[];
    confidence: number;
    dimensions: { width: number; height: number; };
  }>;
  slabs: Array<{
    bbox: number[];
    confidence: number;
    dimensions: { width: number; height: number; };
  }>;
  foundations: Array<{
    bbox: number[];
    confidence: number;
    dimensions: { width: number; height: number; };
  }>;
}

interface DrawingDetail {
  id: number;
  filename: string;
  file_type: string;
  status: string;
  created_at: string;
  components?: {
    type: string;
    count: number;
    dimensions?: {
      width: number;
      height: number;
      depth: number;
    };
  }[];
  text_content?: string;
  recognition_results?: any;
  task_id?: string;
}

export default function DrawingDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [drawing, setDrawing] = useState<DrawingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [componentDetection, setComponentDetection] = useState<ComponentDetection | null>(null);
  const [detectingComponents, setDetectingComponents] = useState(false);
  const [detectionError, setDetectionError] = useState('');
  const [currentTaskId, setCurrentTaskId] = useState<string>('');
  const [showProgress, setShowProgress] = useState(false);

  useEffect(() => {
    if (id) {
      fetchDrawingDetail();
    }
  }, [id]);

  const fetchDrawingDetail = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`http://localhost:8000/api/v1/drawings/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setDrawing(response.data);
      
      // 如果图纸正在处理中，显示进度
      if (response.data.status === 'processing' && response.data.task_id) {
        setCurrentTaskId(response.data.task_id);
        setShowProgress(true);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '获取图纸详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleComponentDetection = async () => {
    if (!id) return;
    
    setDetectingComponents(true);
    setDetectionError('');
    
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `http://localhost:8000/api/v1/drawings/${id}/detect-components`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      // 如果返回了任务ID，显示实时进度
      if (response.data.task_id) {
        setCurrentTaskId(response.data.task_id);
        setShowProgress(true);
      } else {
        setComponentDetection(response.data);
      }
    } catch (err: any) {
      setDetectionError(err.response?.data?.detail || '构件识别失败');
    } finally {
      setDetectingComponents(false);
    }
  };

  const handleOCRProcessing = async () => {
    if (!id) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `http://localhost:8000/api/v1/drawings/${id}/ocr`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      // 如果返回了任务ID，显示实时进度
      if (response.data.task_id) {
        setCurrentTaskId(response.data.task_id);
        setShowProgress(true);
      }
    } catch (err: any) {
      console.error('OCR处理失败:', err);
    }
  };

  const handleProgressComplete = (data: any) => {
    console.log('任务完成:', data);
    setShowProgress(false);
    setCurrentTaskId('');
    // 刷新图纸详情
    fetchDrawingDetail();
  };

  const handleProgressError = (data: any) => {
    console.error('任务失败:', data);
    setShowProgress(false);
    setCurrentTaskId('');
    setDetectionError(data.message || '处理失败');
  };

  const renderComponentDetectionResults = () => {
    if (!componentDetection) return null;

    const componentTypes = [
      { key: 'walls', label: '墙体', icon: '🧱' },
      { key: 'columns', label: '柱子', icon: '🏛️' },
      { key: 'beams', label: '梁', icon: '📏' },
      { key: 'slabs', label: '板', icon: '⬜' },
      { key: 'foundations', label: '基础', icon: '🏗️' }
    ];

    const totalComponents = Object.values(componentDetection).reduce(
      (sum, components) => sum + components.length, 0
    );

    return (
      <div className="bg-blue-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
        <dt className="text-sm font-medium text-gray-500">构件识别结果</dt>
        <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
          <div className="mb-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
              🎯 总共检测到 {totalComponents} 个构件
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {componentTypes.map(({ key, label, icon }) => {
              const components = componentDetection[key as keyof ComponentDetection];
              if (components.length === 0) return null;
              
              return (
                <div key={key} className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-900 flex items-center">
                      <span className="mr-2">{icon}</span>
                      {label}
                    </h4>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {components.length}个
                    </span>
                  </div>
                  
                  <div className="space-y-2">
                    {components.slice(0, 3).map((component, index) => (
                      <div key={index} className="text-xs text-gray-600">
                        <div className="flex justify-between">
                          <span>置信度: {(component.confidence * 100).toFixed(1)}%</span>
                        </div>
                        <div className="text-gray-500">
                          尺寸: {component.dimensions.width.toFixed(0)} × {component.dimensions.height.toFixed(0)} mm
                        </div>
                      </div>
                    ))}
                    {components.length > 3 && (
                      <div className="text-xs text-gray-400">
                        ... 还有 {components.length - 3} 个
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </dd>
      </div>
    );
  };

  if (loading) {
    return <div className="text-center py-4">加载中...</div>;
  }

  if (error) {
    return <div className="text-red-500 text-center py-4">{error}</div>;
  }

  if (!drawing) {
    return <div className="text-center py-4">未找到图纸</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6 flex justify-between items-center">
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              图纸详情
            </h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-500">
              图纸ID: {drawing.id}
            </p>
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={handleOCRProcessing}
              disabled={drawing.status === 'processing'}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              OCR识别
            </button>
            <button
              onClick={handleComponentDetection}
              disabled={detectingComponents || drawing.status === 'processing'}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
            >
              {detectingComponents ? '识别中...' : '构件识别'}
            </button>
          </div>
        </div>

        {/* 实时进度显示 */}
        {showProgress && currentTaskId && (
          <div className="px-4 py-5 sm:px-6 border-t border-gray-200">
            <h4 className="text-md font-medium text-gray-900 mb-4">处理进度</h4>
            <RealTimeProgress
              taskId={currentTaskId}
              onComplete={handleProgressComplete}
              onError={handleProgressError}
              className="mb-4"
            />
          </div>
        )}

        <div className="border-t border-gray-200">
          <dl>
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">文件名</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {drawing.filename}
              </dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">文件类型</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {drawing.file_type.toUpperCase()}
              </dd>
            </div>
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">状态</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
                  drawing.status === 'completed' ? 'bg-green-100 text-green-800' :
                  drawing.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                  drawing.status === 'error' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {drawing.status}
                </span>
              </dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">上传时间</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {new Date(drawing.created_at).toLocaleString()}
              </dd>
            </div>
            
            {drawing.recognition_results && (
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">识别结果</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  <details className="cursor-pointer">
                    <summary className="text-blue-600 hover:text-blue-800">
                      查看详细结果
                    </summary>
                    <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto max-h-96">
                      {JSON.stringify(drawing.recognition_results, null, 2)}
                    </pre>
                  </details>
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* 构件识别结果 */}
        {componentDetection && (
          <div className="px-4 py-5 sm:px-6 border-t border-gray-200">
            <h4 className="text-md font-medium text-gray-900 mb-4">构件识别结果</h4>
            <div className="bg-gray-50 p-4 rounded">
              <pre className="text-sm overflow-auto max-h-96">
                {JSON.stringify(componentDetection, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* 错误信息 */}
        {detectionError && (
          <div className="px-4 py-5 sm:px-6 border-t border-gray-200">
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="text-sm text-red-700">
                {detectionError}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 