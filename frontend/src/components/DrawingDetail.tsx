import React, { useState, useEffect } from 'react';
import { Button, message, Spin } from 'antd';
import request from '../utils/request';

const DrawingDetail: React.FC<{ drawingId: number }> = ({ drawingId }) => {
    const [loading, setLoading] = useState(false);
    const [ocrResults, setOcrResults] = useState<any>(null);
    const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

    // 开始OCR处理
    const handleOCR = async () => {
        try {
            setLoading(true);
            const response = await request.post(`/api/v1/drawings/${drawingId}/ocr`);
            message.success(response.data.message);
            // 开始轮询状态
            startPolling();
        } catch (error) {
            message.error('OCR处理失败');
        }
    };

    // 开始轮询
    const startPolling = () => {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        const interval = setInterval(async () => {
            try {
                const response = await request.get(`/api/v1/drawings/${drawingId}/ocr/status`);
                const { status, results, error_message } = response.data;
                
                if (status === 'completed') {
                    setOcrResults(results);
                    setLoading(false);
                    clearInterval(interval);
                    message.success('OCR处理完成');
                } else if (status === 'error') {
                    setLoading(false);
                    clearInterval(interval);
                    message.error(error_message || 'OCR处理失败');
                }
            } catch (error) {
                setLoading(false);
                clearInterval(interval);
                message.error('获取OCR状态失败');
            }
        }, 3000); // 每3秒轮询一次
        
        setPollingInterval(interval);
    };

    // 组件卸载时清理轮询
    useEffect(() => {
        return () => {
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
        };
    }, [pollingInterval]);

    return (
        <div>
            <Button 
                type="primary" 
                onClick={handleOCR}
                loading={loading}
                disabled={loading}
            >
                {loading ? 'OCR处理中...' : '开始OCR'}
            </Button>
            
            {loading && (
                <div style={{ marginTop: 16, textAlign: 'center' }}>
                    <Spin />
                    <p>正在处理中，请稍候...</p>
                </div>
            )}
            
            {ocrResults && (
                <div style={{ marginTop: 16 }}>
                    <h3>OCR识别结果：</h3>
                    <pre style={{ 
                        background: '#f5f5f5', 
                        padding: 16,
                        borderRadius: 4,
                        maxHeight: 400,
                        overflow: 'auto'
                    }}>
                        {JSON.stringify(ocrResults, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
};

export default DrawingDetail; 