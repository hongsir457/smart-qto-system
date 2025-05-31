import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Card, Table, Button, message, Spin, Descriptions, Space } from 'antd';
import { DownloadOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { getDrawing, exportQuantities, deleteDrawing, verifyDrawing, aiAssistDrawing } from '../services/api';
import { Drawing } from '../types';
import { message as antdMessage } from 'antd';

const DrawingDetail: React.FC = () => {
    const router = useRouter();
    const { id } = router.query;
    const [drawing, setDrawing] = useState<Drawing | null>(null);
    const [loading, setLoading] = useState(true);
    const [ocrResult, setOcrResult] = useState<string | null>(null);
    const [detectResult, setDetectResult] = useState<any>(null);
    const [verifyResult, setVerifyResult] = useState<any>(null);
    const [aiResult, setAiResult] = useState<any>(null);
    const [isPolling, setIsPolling] = useState(false);

    useEffect(() => {
        fetchDrawing();
    }, [id]);

    // 监听 drawing.status，决定是否轮询
    useEffect(() => {
        if (drawing?.status === 'pending') {
            setIsPolling(true);
        } else {
            setIsPolling(false);
        }
    }, [drawing?.status]);

    // 轮询副作用
    useEffect(() => {
        if (!isPolling) return;
        const timer = setInterval(() => {
            fetchDrawing();
        }, 5000);
        return () => clearInterval(timer);
    }, [isPolling]);

    const fetchDrawing = async () => {
        try {
            const data = await getDrawing(Number(id));
            setDrawing(data);
        } catch (error) {
            message.error('获取图纸详情失败');
            router.push('/drawings');
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async () => {
        try {
            const blob = await exportQuantities(Number(id));
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `quantities_${drawing?.filename}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            message.error('导出工程量失败');
        }
    };

    const handleDelete = async () => {
        if (!drawing) return;
        try {
            await deleteDrawing(drawing.id);
            message.success('删除成功');
            router.push('/drawings');
        } catch (error) {
            message.error('删除失败');
        }
    };

    const pollTaskStatus = async (taskId: string) => {
        if (!taskId || taskId === 'undefined') {
            throw new Error('无效的任务ID');
        }

        const maxAttempts = 60; // 最多轮询60次
        let attempts = 0;
        
        while (attempts < maxAttempts) {
            try {
                const res = await fetch(`/api/v1/drawings/tasks/${taskId}`, {
                    headers: { 
                        Authorization: 'Bearer ' + localStorage.getItem('token'),
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                
                const data = await res.json();
                console.log('Task status:', data);
                
                if (data.status === 'completed' && data.result) {
                    return data.result;
                } else if (data.status === 'failed') {
                    throw new Error(data.error || '任务执行失败');
                } else if (data.status === 'processing') {
                    console.log(data.message || '处理中...');
                } else {
                    console.warn('未知的任务状态:', data);
                }
                
                attempts++;
                await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒
            } catch (error) {
                console.error('轮询任务状态失败:', error);
                throw error;
            }
        }
        throw new Error('任务超时');
    };

    const handleOCR = async () => {
        if (!drawing) return;
        setOcrResult(null);
        try {
            antdMessage.loading({ content: 'OCR识别中...', key: 'ocr' });
            const res = await fetch(`/api/v1/drawings/${drawing.id}/ocr`, {
                method: 'POST',
                headers: { 
                    Authorization: 'Bearer ' + localStorage.getItem('token'),
                    'Content-Type': 'application/json'
                }
            });
            
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            
            const data = await res.json();
            console.log('OCR task started:', data);
            
            if (!data.task_id) {
                throw new Error('服务器未返回任务ID');
            }
            
            const result = await pollTaskStatus(data.task_id);
            console.log('OCR result:', result);
            
            if (typeof result === 'string') {
                setOcrResult(result);
            } else if (result && typeof result.text === 'string') {
                setOcrResult(result.text);
            } else {
                setOcrResult(JSON.stringify(result, null, 2));
            }
            
            antdMessage.success({ content: 'OCR识别成功', key: 'ocr' });
        } catch (error: any) {
            console.error('OCR error:', error);
            setOcrResult('识别失败');
            antdMessage.error({ 
                content: '识别失败: ' + (error.message || '未知错误'), 
                key: 'ocr' 
            });
        }
    };

    const handleDetect = async () => {
        if (!drawing) return;
        setDetectResult(null);
        try {
            antdMessage.loading({ content: '构件识别中...', key: 'detect' });
            const res = await fetch(`/api/v1/drawings/${drawing.id}/detect-components`, {
                method: 'POST',
                headers: { 
                    Authorization: 'Bearer ' + localStorage.getItem('token'),
                    'Content-Type': 'application/json'
                }
            });
            
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            
            const data = await res.json();
            console.log('Component detection task started:', data);
            
            if (!data.task_id) {
                throw new Error('服务器未返回任务ID');
            }
            
            const result = await pollTaskStatus(data.task_id);
            
            if (result && result.components) {
                setDetectResult(result.components);
                antdMessage.success({ content: '构件识别成功', key: 'detect' });
            } else if (result && result.recognition && result.recognition.components) {
                setDetectResult(result.recognition.components);
                antdMessage.success({ content: '构件识别成功', key: 'detect' });
            } else {
                setDetectResult(JSON.stringify(result, null, 2));
                antdMessage.success({ content: '构件识别完成', key: 'detect' });
            }
        } catch (error: any) {
            setDetectResult('识别失败: ' + (error.message || '未知错误'));
            antdMessage.error({ 
                content: '构件识别失败: ' + (error.message || '未知错误'), 
                key: 'detect' 
            });
        }
    };

    const handleVerify = async () => {
        if (!drawing) return;
        try {
            const res = await verifyDrawing(drawing.id);
            setVerifyResult(res);
            antdMessage.success('二次校验成功');
        } catch (error) {
            antdMessage.error('二次校验失败');
        }
    };
    const handleAiAssist = async () => {
        if (!drawing) return;
        try {
            const res = await aiAssistDrawing(drawing.id);
            setAiResult(res);
            antdMessage.success('AI辅助成功');
        } catch (error) {
            antdMessage.error('AI辅助失败');
        }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <Spin size="large" />
            </div>
        );
    }

    const columns = {
        walls: [
            { title: 'ID', dataIndex: 'id', key: 'id' },
            { title: '类型', dataIndex: 'type', key: 'type' },
            { title: '材料', dataIndex: 'material', key: 'material' },
            { title: '长度(m)', dataIndex: ['quantities', 'length'], key: 'length' },
            { title: '面积(m²)', dataIndex: ['quantities', 'area'], key: 'area' },
            { title: '体积(m³)', dataIndex: ['quantities', 'volume'], key: 'volume' },
        ],
        columns: [
            { title: 'ID', dataIndex: 'id', key: 'id' },
            { title: '类型', dataIndex: 'type', key: 'type' },
            { title: '材料', dataIndex: 'material', key: 'material' },
            { title: '截面面积(m²)', dataIndex: ['quantities', 'area'], key: 'area' },
            { title: '高度(m)', dataIndex: ['quantities', 'height'], key: 'height' },
            { title: '体积(m³)', dataIndex: ['quantities', 'volume'], key: 'volume' },
        ],
        beams: [
            { title: 'ID', dataIndex: 'id', key: 'id' },
            { title: '类型', dataIndex: 'type', key: 'type' },
            { title: '材料', dataIndex: 'material', key: 'material' },
            { title: '长度(m)', dataIndex: ['quantities', 'length'], key: 'length' },
            { title: '截面面积(m²)', dataIndex: ['quantities', 'area'], key: 'area' },
            { title: '体积(m³)', dataIndex: ['quantities', 'volume'], key: 'volume' },
        ],
        slabs: [
            { title: 'ID', dataIndex: 'id', key: 'id' },
            { title: '类型', dataIndex: 'type', key: 'type' },
            { title: '材料', dataIndex: 'material', key: 'material' },
            { title: '面积(m²)', dataIndex: ['quantities', 'area'], key: 'area' },
            { title: '厚度(m)', dataIndex: ['quantities', 'thickness'], key: 'thickness' },
            { title: '体积(m³)', dataIndex: ['quantities', 'volume'], key: 'volume' },
        ],
        foundations: [
            { title: 'ID', dataIndex: 'id', key: 'id' },
            { title: '类型', dataIndex: 'type', key: 'type' },
            { title: '材料', dataIndex: 'material', key: 'material' },
            { title: '底面积(m²)', dataIndex: ['quantities', 'area'], key: 'area' },
            { title: '高度(m)', dataIndex: ['quantities', 'height'], key: 'height' },
            { title: '体积(m³)', dataIndex: ['quantities', 'volume'], key: 'volume' },
        ],
    };

    return (
        <div style={{ padding: 24 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
                <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/drawings')}>
                    返回列表
                </Button>
                <Button type="primary" icon={<DownloadOutlined />} onClick={handleExport} disabled={!drawing || !drawing.recognition_results}>
                    导出工程量
                </Button>
                <Button danger onClick={handleDelete} disabled={!drawing}>
                    删除图纸
                </Button>
                <Button onClick={handleOCR} disabled={!drawing}>OCR识别</Button>
                <Button onClick={handleDetect} disabled={!drawing}>构件识别</Button>
                <Button onClick={handleVerify} disabled={!drawing}>二次校验</Button>
                <Button onClick={handleAiAssist} disabled={!drawing}>AI辅助</Button>
            </Space>

            {ocrResult !== null && (
                <Card title="OCR识别结果" style={{ marginTop: 16 }}>
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{ocrResult || '未识别到任何内容'}</pre>
                </Card>
            )}
            {detectResult !== null && (
                <Card title="构件识别结果" style={{ marginTop: 16 }}>
                    {typeof detectResult === 'string' ? (
                        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                            {detectResult || '未识别到任何构件'}
                        </pre>
                    ) : (
                        <div>
                            <div style={{ marginBottom: 16 }}>
                                <h4>构件统计：</h4>
                                <Space>
                                    {detectResult.walls && <span>墙体: {detectResult.walls.length}个</span>}
                                    {detectResult.columns && <span>柱子: {detectResult.columns.length}个</span>}
                                    {detectResult.beams && <span>梁: {detectResult.beams.length}个</span>}
                                    {detectResult.slabs && <span>板: {detectResult.slabs.length}个</span>}
                                    {detectResult.foundations && <span>基础: {detectResult.foundations.length}个</span>}
                                </Space>
                            </div>
                            
                            {/* 墙体识别结果 */}
                            {detectResult.walls && detectResult.walls.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                    <h4>🧱 墙体构件 ({detectResult.walls.length}个)</h4>
                                    <Table
                                        size="small"
                                        dataSource={detectResult.walls.map((wall, index) => ({ ...wall, key: index }))}
                                        columns={[
                                            { title: '序号', dataIndex: 'key', width: 60, render: (_, __, index) => index + 1 },
                                            { title: '置信度', dataIndex: 'confidence', width: 80, render: (val) => (val * 100).toFixed(1) + '%' },
                                            { title: '宽度(mm)', dataIndex: ['dimensions', 'width'], width: 100, render: (val) => val?.toFixed(0) },
                                            { title: '高度(mm)', dataIndex: ['dimensions', 'height'], width: 100, render: (val) => val?.toFixed(0) },
                                        ]}
                                        pagination={false}
                                        scroll={{ x: true }}
                                    />
                                </div>
                            )}

                            {/* 柱子识别结果 */}
                            {detectResult.columns && detectResult.columns.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                    <h4>🏛️ 柱子构件 ({detectResult.columns.length}个)</h4>
                                    <Table
                                        size="small"
                                        dataSource={detectResult.columns.map((column, index) => ({ ...column, key: index }))}
                                        columns={[
                                            { title: '序号', dataIndex: 'key', width: 60, render: (_, __, index) => index + 1 },
                                            { title: '置信度', dataIndex: 'confidence', width: 80, render: (val) => (val * 100).toFixed(1) + '%' },
                                            { title: '宽度(mm)', dataIndex: ['dimensions', 'width'], width: 100, render: (val) => val?.toFixed(0) },
                                            { title: '高度(mm)', dataIndex: ['dimensions', 'height'], width: 100, render: (val) => val?.toFixed(0) },
                                        ]}
                                        pagination={false}
                                        scroll={{ x: true }}
                                    />
                                </div>
                            )}

                            {/* 梁识别结果 */}
                            {detectResult.beams && detectResult.beams.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                    <h4>🌉 梁构件 ({detectResult.beams.length}个)</h4>
                                    <Table
                                        size="small"
                                        dataSource={detectResult.beams.map((beam, index) => ({ ...beam, key: index }))}
                                        columns={[
                                            { title: '序号', dataIndex: 'key', width: 60, render: (_, __, index) => index + 1 },
                                            { title: '置信度', dataIndex: 'confidence', width: 80, render: (val) => (val * 100).toFixed(1) + '%' },
                                            { title: '宽度(mm)', dataIndex: ['dimensions', 'width'], width: 100, render: (val) => val?.toFixed(0) },
                                            { title: '高度(mm)', dataIndex: ['dimensions', 'height'], width: 100, render: (val) => val?.toFixed(0) },
                                        ]}
                                        pagination={false}
                                        scroll={{ x: true }}
                                    />
                                </div>
                            )}

                            {/* 板识别结果 */}
                            {detectResult.slabs && detectResult.slabs.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                    <h4>🗂️ 板构件 ({detectResult.slabs.length}个)</h4>
                                    <Table
                                        size="small"
                                        dataSource={detectResult.slabs.map((slab, index) => ({ ...slab, key: index }))}
                                        columns={[
                                            { title: '序号', dataIndex: 'key', width: 60, render: (_, __, index) => index + 1 },
                                            { title: '置信度', dataIndex: 'confidence', width: 80, render: (val) => (val * 100).toFixed(1) + '%' },
                                            { title: '宽度(mm)', dataIndex: ['dimensions', 'width'], width: 100, render: (val) => val?.toFixed(0) },
                                            { title: '高度(mm)', dataIndex: ['dimensions', 'height'], width: 100, render: (val) => val?.toFixed(0) },
                                        ]}
                                        pagination={false}
                                        scroll={{ x: true }}
                                    />
                                </div>
                            )}

                            {/* 基础识别结果 */}
                            {detectResult.foundations && detectResult.foundations.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                    <h4>🏗️ 基础构件 ({detectResult.foundations.length}个)</h4>
                                    <Table
                                        size="small"
                                        dataSource={detectResult.foundations.map((foundation, index) => ({ ...foundation, key: index }))}
                                        columns={[
                                            { title: '序号', dataIndex: 'key', width: 60, render: (_, __, index) => index + 1 },
                                            { title: '置信度', dataIndex: 'confidence', width: 80, render: (val) => (val * 100).toFixed(1) + '%' },
                                            { title: '宽度(mm)', dataIndex: ['dimensions', 'width'], width: 100, render: (val) => val?.toFixed(0) },
                                            { title: '高度(mm)', dataIndex: ['dimensions', 'height'], width: 100, render: (val) => val?.toFixed(0) },
                                        ]}
                                        pagination={false}
                                        scroll={{ x: true }}
                                    />
                                </div>
                            )}

                            {/* 如果没有检测到任何构件 */}
                            {(!detectResult.walls || detectResult.walls.length === 0) &&
                             (!detectResult.columns || detectResult.columns.length === 0) &&
                             (!detectResult.beams || detectResult.beams.length === 0) &&
                             (!detectResult.slabs || detectResult.slabs.length === 0) &&
                             (!detectResult.foundations || detectResult.foundations.length === 0) && (
                                <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>
                                    <p>⚠️ 未识别到任何建筑构件</p>
                                    <p>可能的原因：图纸格式不适合、分辨率过低、或者YOLO模型需要训练</p>
                                </div>
                            )}
                        </div>
                    )}
                </Card>
            )}
            {verifyResult && (
                <Card title="二次校验结果" style={{ marginTop: 16 }}>
                    <pre>{JSON.stringify(verifyResult, null, 2)}</pre>
                </Card>
            )}
            {aiResult && (
                <Card title="AI辅助结果" style={{ marginTop: 16 }}>
                    <pre>{JSON.stringify(aiResult, null, 2)}</pre>
                </Card>
            )}

            {!drawing || !drawing.recognition_results ? (
                <Card style={{ marginTop: 16 }}>
                    <div>暂无工程量数据</div>
                </Card>
            ) : (
                <>
                    <Card title="图纸信息" style={{ marginTop: 16 }}>
                        <Descriptions>
                            <Descriptions.Item label="文件名">{drawing.filename}</Descriptions.Item>
                            <Descriptions.Item label="文件类型">{drawing.file_type}</Descriptions.Item>
                            <Descriptions.Item label="上传时间">
                                {new Date(drawing.created_at).toLocaleString()}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>

                    <Card title="总工程量" style={{ marginTop: 16 }}>
                        <Descriptions>
                            <Descriptions.Item label="墙体体积">{drawing.recognition_results.quantities.total.wall_volume.toFixed(2)} m³</Descriptions.Item>
                            <Descriptions.Item label="柱子体积">{drawing.recognition_results.quantities.total.column_volume.toFixed(2)} m³</Descriptions.Item>
                            <Descriptions.Item label="梁体积">{drawing.recognition_results.quantities.total.beam_volume.toFixed(2)} m³</Descriptions.Item>
                            <Descriptions.Item label="板体积">{drawing.recognition_results.quantities.total.slab_volume.toFixed(2)} m³</Descriptions.Item>
                            <Descriptions.Item label="基础体积">{drawing.recognition_results.quantities.total.foundation_volume.toFixed(2)} m³</Descriptions.Item>
                            <Descriptions.Item label="总体积">{drawing.recognition_results.quantities.total.total_volume.toFixed(2)} m³</Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {drawing.recognition_results.quantities.walls.length > 0 && (
                        <Card title="墙体工程量" style={{ marginTop: 16 }}>
                            <Table
                                columns={columns.walls}
                                dataSource={drawing.recognition_results.quantities.walls}
                                rowKey="id"
                            />
                        </Card>
                    )}

                    {drawing.recognition_results.quantities.columns.length > 0 && (
                        <Card title="柱子工程量" style={{ marginTop: 16 }}>
                            <Table
                                columns={columns.columns}
                                dataSource={drawing.recognition_results.quantities.columns}
                                rowKey="id"
                            />
                        </Card>
                    )}

                    {drawing.recognition_results.quantities.beams.length > 0 && (
                        <Card title="梁工程量" style={{ marginTop: 16 }}>
                            <Table
                                columns={columns.beams}
                                dataSource={drawing.recognition_results.quantities.beams}
                                rowKey="id"
                            />
                        </Card>
                    )}

                    {drawing.recognition_results.quantities.slabs.length > 0 && (
                        <Card title="板工程量" style={{ marginTop: 16 }}>
                            <Table
                                columns={columns.slabs}
                                dataSource={drawing.recognition_results.quantities.slabs}
                                rowKey="id"
                            />
                        </Card>
                    )}

                    {drawing.recognition_results.quantities.foundations.length > 0 && (
                        <Card title="基础工程量" style={{ marginTop: 16 }}>
                            <Table
                                columns={columns.foundations}
                                dataSource={drawing.recognition_results.quantities.foundations}
                                rowKey="id"
                            />
                        </Card>
                    )}
                </>
            )}
        </div>
    );
};

export default DrawingDetail; 