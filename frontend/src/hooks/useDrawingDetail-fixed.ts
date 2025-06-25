import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import { message, Modal } from 'antd';
import { getDrawing, exportQuantities } from '../services/api';
import { Drawing } from '../types';
import { useOcrProcessing } from './useOcrProcessing';

export interface DrawingDetailData {
  id: number;
  filename: string;
  status: string;
  created_at: string;
  updated_at: string;
  progress: number;
  file_size?: number;
  file_type?: string;
  processing_result?: any;
  recognition_results?: any;
  components_count?: number;
  task_id?: string;
}

export const useDrawingDetail = (drawingId: number) => {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DrawingDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isQuantityProcessing, setIsQuantityProcessing] = useState(false);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  const { 
    ocrResult, 
    readableOcrResults, 
    isOcrProcessing, 
    processOcrData, 
    handleAutoOCR 
  } = useOcrProcessing();

  const fetchDrawingDetail = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 检查认证状态
      const token = localStorage.getItem('token');
      if (!token) {
        console.warn('⚠️ 未找到认证token，使用测试模式');
        // 为了测试，我们可以设置一个模拟token
        localStorage.setItem('token', 'test_token_for_development');
      }
      
      console.log('🔍 获取图纸详情:', drawingId);
      
      const response = await fetch(`/api/v1/drawings/${drawingId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('认证失败，请重新登录');
        } else if (response.status === 404) {
          throw new Error('图纸不存在');
        } else {
          throw new Error(`请求失败: ${response.status}`);
        }
      }
      
      const result = await response.json();
      console.log('✅ 图纸详情获取成功:', result);
      
      setData(result);
      
      // 异步处理OCR数据，不阻塞主流程
      if (result) {
        console.log('🔄 开始异步处理OCR数据...');
        // 使用setTimeout确保loading状态先被设置为false
        setTimeout(() => {
          processOcrData(result, drawingId.toString()).catch((error) => {
            console.warn('⚠️ OCR数据处理失败:', error);
            // 即使失败也不影响页面显示
          });
        }, 100);
      }
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取图纸详情失败';
      console.error('❌ 获取图纸详情失败:', err);
      setError(errorMessage);
      message.error(errorMessage);
    } finally {
      setLoading(false); // 确保loading状态被设置为false
    }
  }, [drawingId, processOcrData]);

  /**
   * 轮询任务状态
   */
  const pollTaskStatus = useCallback(async (taskId: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.warn('未找到认证token，停止轮询');
        return;
      }

      const response = await fetch(`/api/v1/tasks/${taskId}/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`获取任务状态失败: ${response.status}`);
      }

      const result = await response.json();
      console.log('任务状态:', result);

      if (result.status === 'completed') {
        message.success('处理完成，正在刷新数据...');
        await fetchDrawingDetail();
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
      } else if (result.status === 'failed') {
        message.error(`处理失败: ${result.error || '未知错误'}`);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
      }
    } catch (error) {
      console.error('轮询任务状态失败:', error);
    }
  }, [fetchDrawingDetail, pollingInterval]);

  /**
   * 处理自动OCR
   */
  const handleOCR = useCallback(async () => {
    if (!data) {
      message.warning('请先选择图纸');
      return;
    }
    
    try {
      console.log('🚀 开始OCR处理...');
      await handleAutoOCR(drawingId);
      
      // OCR完成后重新获取数据
      setTimeout(() => {
        fetchDrawingDetail();
      }, 2000);
      
    } catch (error) {
      console.error('❌ OCR处理失败:', error);
      message.error('OCR处理失败，请稍后重试');
    }
  }, [data, drawingId, handleAutoOCR, fetchDrawingDetail]);

  /**
   * 处理工程量计算
   */
  const handleAutoQuantityCalculation = useCallback(async () => {
    if (!data || !ocrResult) {
      message.warning('请先完成OCR识别');
      return;
    }

    setIsQuantityProcessing(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      message.info('正在启动工程量计算...');
    } catch (error) {
      console.error('工程量计算失败:', error);
      message.error('工程量计算失败，请稍后重试');
    } finally {
      setIsQuantityProcessing(false);
    }
  }, [data, ocrResult]);

  /**
   * 删除图纸
   */
  const handleDeleteDrawing = useCallback(async () => {
    if (!data) return;

    Modal.confirm({
      title: '确认删除',
      content: `确定要删除图纸 "${data.filename}" 吗？此操作不可恢复。`,
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const token = localStorage.getItem('token');
          if (!token) {
            message.error('请先登录');
            return;
          }

          const response = await fetch(`/api/v1/drawings/${data.id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` }
          });

          if (!response.ok) {
            throw new Error(`删除失败: ${response.status}`);
          }

          message.success('图纸删除成功');
          router.push('/drawings');
        } catch (error) {
          console.error('删除图纸失败:', error);
          message.error('删除图纸失败，请稍后重试');
        }
      }
    });
  }, [data, router]);

  /**
   * 导出工程量清单
   */
  const handleExportQuantities = useCallback(async () => {
    if (!data) return;

    try {
      await exportQuantities(data.id);
      message.success('工程量清单导出成功');
    } catch (error) {
      console.error('导出工程量清单失败:', error);
      message.error('导出失败，请稍后重试');
    }
  }, [data]);

  /**
   * 导出计算报告
   */
  const handleExportCalculationReport = useCallback(async () => {
    if (!data) return;

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`/api/v1/drawings/${data.id}/export-report`, {
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`导出失败: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${data.filename}_计算报告.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      message.success('计算报告导出成功');
    } catch (error) {
      console.error('导出计算报告失败:', error);
      message.error('导出失败，请稍后重试');
    }
  }, [data]);

  // 组件挂载时获取数据
  useEffect(() => {
    if (drawingId) {
      fetchDrawingDetail();
    }
  }, [drawingId, fetchDrawingDetail]);

  // 监听OCR结果变化
  useEffect(() => {
    if (readableOcrResults) {
      console.log('✅ OCR结果已更新:', readableOcrResults);
      
      // 检查是否是A→B→C完整数据流结果
      if (readableOcrResults.meta?.stage === 'A→B→C完整数据流') {
        console.log('🎉 检测到A→B→C完整数据流结果');
        message.success('A→B→C智能OCR处理完成！');
      } else if (readableOcrResults.readable_text) {
        console.log('📄 检测到可读文本结果');
        message.success('OCR可读化处理完成！');
      }
    }
  }, [readableOcrResults]);

  // 组件卸载时清理轮询
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  return {
    loading,
    data,
    error,
    ocrResult,
    readableOcrResults,
    isOcrProcessing,
    isQuantityProcessing,
    handleOCR,
    handleAutoQuantityCalculation,
    handleDeleteDrawing,
    handleExportQuantities,
    handleExportCalculationReport,
    router,
    retry: fetchDrawingDetail,
    refresh: fetchDrawingDetail
  };
}; 