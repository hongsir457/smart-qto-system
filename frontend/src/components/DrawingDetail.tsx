import React, { useState, useEffect } from 'react';
import { Button, message, Spin, Tabs } from 'antd';
import request from '../utils/request';
import OCRResultDisplay from './OCRResultDisplay';

const DrawingDetail: React.FC<{ drawingId: number }> = ({ drawingId }) => {
    const [loading, setLoading] = useState(false);
    const [ocrResults, setOcrResults] = useState<any>(null);
    const [readableOcrResults, setReadableOcrResults] = useState<any>(null);
    const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

    // 处理可读化结果
    const processReadableResults = async (rawResults: any) => {
        try {
            // 这里可以调用后端API来获取可读化结果
            // 或者直接处理rawResults如果它已经包含可读化数据
            if (rawResults?.readable_result) {
                setReadableOcrResults(rawResults.readable_result);
            } else {
                // 如果没有可读化结果，可以调用后端处理
                const response = await request.post(`/api/v1/drawings/${drawingId}/ocr/readable`, {
                    raw_results: rawResults
                });
                setReadableOcrResults(response.data);
            }
        } catch (error) {
            console.error('处理可读化结果失败:', error);
            message.warning('可读化结果处理失败，但原始结果可用');
        }
    };

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
                    // 处理可读化结果
                    await processReadableResults(results);
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
        }, 5000); // 每5秒轮询一次
        
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
            
            {(ocrResults || readableOcrResults) && (
                <div style={{ marginTop: 16 }}>
                    <Tabs defaultActiveKey="readable" type="card">
                        <Tabs.TabPane tab="📊 可读化结果" key="readable">
                            {readableOcrResults ? (
                                <OCRResultDisplay ocrResult={readableOcrResults} />
                            ) : (
                                <div style={{ textAlign: 'center', padding: 20 }}>
                                    <Spin />
                                    <p>正在生成可读化结果...</p>
                                </div>
                            )}
                        </Tabs.TabPane>
                        <Tabs.TabPane tab="🔧 原始数据" key="raw">
                            <pre style={{ 
                                background: '#f5f5f5', 
                                padding: 16,
                                borderRadius: 4,
                                maxHeight: 400,
                                overflow: 'auto'
                            }}>
                                {JSON.stringify(ocrResults, null, 2)}
                            </pre>
                        </Tabs.TabPane>
                    </Tabs>
                </div>
            )}
        </div>
    );
};

export default DrawingDetail; 