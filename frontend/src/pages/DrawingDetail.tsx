import React, { useState, useEffect } from 'react';
import { Button, Spin, Table, Card, Tag, Typography, message, Descriptions, Divider } from 'antd';
import { 
    ArrowLeftOutlined, 
    DownloadOutlined, 
    FileTextOutlined,
    EyeOutlined,
    DeleteOutlined,
    InfoCircleOutlined,
    BuildOutlined
} from '@ant-design/icons';
import { useRouter } from 'next/router';
import { Drawing } from '../types';
import DrawingInfo from '../components/DrawingInfo';
import QuantityList from '../components/QuantityList';
import './DrawingDetail.css';

const { Text, Paragraph } = Typography;

/**
 * OCR识别块组件（输出点1）
 */
const OCRRecognitionBlock = ({ ocrDisplay }: { ocrDisplay: any }) => {
    const { drawing_basic_info, component_overview, ocr_source_info } = ocrDisplay;

    return (
        <div>
            {/* 图纸基本信息 */}
            <Card 
                title={<span><InfoCircleOutlined style={{ marginRight: 8 }} />图纸基本信息</span>}
                style={{ marginBottom: 16 }}
                size="small"
            >
                <Descriptions column={2} size="small">
                    <Descriptions.Item label="图纸标题">
                        {drawing_basic_info.drawing_title || '未识别'}
                    </Descriptions.Item>
                    <Descriptions.Item label="图号">
                        {drawing_basic_info.drawing_number || '未识别'}
                    </Descriptions.Item>
                    <Descriptions.Item label="比例">
                        {drawing_basic_info.scale || '未识别'}
                    </Descriptions.Item>
                    <Descriptions.Item label="工程名称">
                        {drawing_basic_info.project_name || '未识别'}
                    </Descriptions.Item>
                    <Descriptions.Item label="图纸类型" span={2}>
                        {drawing_basic_info.drawing_type || '未识别'}
                    </Descriptions.Item>
                </Descriptions>
            </Card>

            {/* 构件概览信息 */}
            <Card 
                title={<span><BuildOutlined style={{ marginRight: 8 }} />构件概览信息</span>}
                size="small"
            >
                <div style={{ marginBottom: 16 }}>
                    <Text strong>构件编号清单：</Text>
                    <div style={{ marginTop: 8 }}>
                        {component_overview.component_ids.length > 0 ? (
                            component_overview.component_ids.map((id: string) => (
                                <Tag key={id} color="blue" style={{ margin: 2 }}>{id}</Tag>
                            ))
                        ) : (
                            <Text type="secondary">暂无构件编号</Text>
                        )}
                    </div>
                </div>
                
                <div style={{ marginBottom: 16 }}>
                    <Text strong>构件类型：</Text>
                    <div style={{ marginTop: 8 }}>
                        {component_overview.component_types.length > 0 ? (
                            component_overview.component_types.map((type: string) => (
                                <Tag key={type} color="green" style={{ margin: 2 }}>{type}</Tag>
                            ))
                        ) : (
                            <Text type="secondary">暂无构件类型</Text>
                        )}
                    </div>
                </div>

                <div style={{ marginBottom: 16 }}>
                    <Text strong>材料等级：</Text>
                    <div style={{ marginTop: 8 }}>
                        {component_overview.material_grades.length > 0 ? (
                            component_overview.material_grades.map((material: string) => (
                                <Tag key={material} color="orange" style={{ margin: 2 }}>{material}</Tag>
                            ))
                        ) : (
                            <Text type="secondary">暂无材料等级</Text>
                        )}
                    </div>
                </div>

                <div style={{ marginBottom: 16 }}>
                    <Text strong>轴线编号：</Text>
                    <div style={{ marginTop: 8 }}>
                        {component_overview.axis_lines.length > 0 ? (
                            component_overview.axis_lines.map((axis: string) => (
                                <Tag key={axis} color="purple" style={{ margin: 2 }}>{axis}</Tag>
                            ))
                        ) : (
                            <Text type="secondary">暂无轴线编号</Text>
                        )}
                    </div>
                </div>

                <Divider />

                {/* 分析汇总 */}
                <div>
                    <Text strong>分析汇总：</Text>
                    <Descriptions column={3} size="small" style={{ marginTop: 8 }}>
                        <Descriptions.Item label="构件总数">
                            {component_overview.summary.total_components || 0}
                        </Descriptions.Item>
                        <Descriptions.Item label="主要结构">
                            {component_overview.summary.main_structure_type || '未知'}
                        </Descriptions.Item>
                        <Descriptions.Item label="复杂程度">
                            <Tag color={
                                component_overview.summary.complexity_level === '简单' ? 'green' :
                                component_overview.summary.complexity_level === '中等' ? 'orange' : 'red'
                            }>
                                {component_overview.summary.complexity_level || '未知'}
                            </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="数据来源" span={3}>
                            <Text type="secondary">
                                {ocr_source_info.analysis_method} - 
                                基于 {ocr_source_info.total_slices} 个切片的 {ocr_source_info.ocr_text_count} 条OCR文本
                            </Text>
                        </Descriptions.Item>
                    </Descriptions>
                </div>
            </Card>
        </div>
    );
};

/**
 * 这是一个新的、自包含的渲染组件，用于生成丰富的OCR结果显示。
 * 它直接从后端返回的 drawingData 中解析数据，绕过了复杂的前端钩子。
 * 支持新的两个输出点：OCR识别块和工程量清单块
 */
const RichOcrResultDisplay = ({ drawingData, isProcessing }: { drawingData: any, isProcessing: boolean }) => {
    if (isProcessing) {
        return (
            <div className="ocr-loading-state">
                <Spin size="large" />
                <p className="ocr-loading-text">正在进行OCR识别和分析...</p>
            </div>
        );
    }

    // 🔧 优先使用独立的OCR识别块字段（轨道1输出点）
    if (drawingData?.ocr_recognition_display) {
        return <OCRRecognitionBlock ocrDisplay={drawingData.ocr_recognition_display} />;
    }

    // 降级到嵌套字段（兼容性）
    const recResults = drawingData?.recognition_results;
    if (recResults?.ocr_recognition_display) {
        return <OCRRecognitionBlock ocrDisplay={recResults.ocr_recognition_display} />;
    }
    
    // 降级到旧版显示
    if (!recResults || !recResults.components || recResults.components.length === 0) {
        return (
            <div className="ocr-empty-state">
                <EyeOutlined className="ocr-empty-icon" />
                <p className="ocr-empty-text">暂无OCR识别结果</p>
                <p className="ocr-empty-hint">未能从图纸数据中找到有效的构件列表。</p>
            </div>
        );
    }
    
    const { components = [], analysis_summary, analysis_engine, total_texts } = recResults;

    // 生成自然语言描述
    const generateNaturalLanguageSummary = () => {
        const componentTypes = Array.from(new Set(components.map((c: any) => c.component_type).filter(Boolean)));
        let summary = `本次AI分析使用 <strong>${analysis_engine || '未知引擎'}</strong> 完成。`;
        summary += ` 从图纸中总共识别了 <strong>${total_texts || '大量'}</strong> 处文本，并成功提取出 <strong>${components.length}</strong> 个结构化构件。`;
        if (componentTypes.length > 0) {
            summary += ` 主要构件类型包括：<strong>${componentTypes.join('、')}</strong>。`;
        }
        if (analysis_summary?.data_integrity) {
            summary += ` 数据完整性评估为：<span class="ant-tag ant-tag-green">${analysis_summary.data_integrity}</span>。`;
        }
        return summary;
    };

    const columns = [
        { title: '构件ID', dataIndex: 'component_id', key: 'component_id', width: 150, render: (text: string) => <Text strong>{text}</Text> },
        { title: '构件类型', dataIndex: 'component_type', key: 'component_type', width: 120, render: (type: string) => <Tag color="blue">{type}</Tag> },
        { title: '尺寸/规格', dataIndex: 'dimensions', key: 'dimensions', render: (text: string) => text || 'N/A' },
        { title: '备注', dataIndex: 'notes', key: 'notes', render: (text: string) => <Text type="secondary">{text || '-'}</Text> },
    ];

    return (
        <div>
            {/* 自然语言分析摘要 */}
            <Card 
                title={<span><InfoCircleOutlined style={{ marginRight: 8 }} />AI分析摘要</span>} 
                style={{ marginBottom: 16 }}
                size="small"
            >
                <Paragraph>
                    <span dangerouslySetInnerHTML={{ __html: generateNaturalLanguageSummary() }} />
                </Paragraph>
            </Card>

            {/* 构件清单 */}
            <Card 
                title={<span><BuildOutlined style={{ marginRight: 8 }} />识别构件清单</span>}
                size="small"
            >
                <Table
                    columns={columns}
                    dataSource={components.map((c: any, index: number) => ({ ...c, key: c.component_id || index }))}
                    pagination={{ pageSize: 10, size: 'small', simple: true }}
                    size="small"
                />
            </Card>
        </div>
    );
};

const DrawingDetail: React.FC = () => {
    const router = useRouter();
    const { id } = router.query;
    const drawingId = Array.isArray(id) ? parseInt(id[0]) : parseInt(id as string);

    const [drawing, setDrawing] = useState<Drawing | null>(null);
    const [loading, setLoading] = useState(true);
    const [isOcrProcessing, setIsOcrProcessing] = useState(false);
    const [isQuantityProcessing, setIsQuantityProcessing] = useState(false);

    // 获取图纸详情
    const fetchDrawingDetail = async () => {
        try {
            setLoading(true);
            
            const token = localStorage.getItem('token');
            if (!token) {
                localStorage.setItem('token', 'test_token_for_development');
            }
            
            const response = await fetch(`/api/v1/drawings/${drawingId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`请求失败: ${response.status}`);
            }
            
            const result = await response.json();
            setDrawing(result as Drawing);
            
        } catch (err) {
            console.error('获取图纸详情失败:', err);
            message.error('获取图纸详情失败');
        } finally {
            setLoading(false);
        }
    };

    // 删除图纸
    const handleDeleteDrawing = async () => {
        if (!drawing || !confirm(`确定要删除图纸 "${drawing.filename}" 吗？`)) return;

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`/api/v1/drawings/${drawingId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            });

            if (response.ok) {
                message.success('删除成功');
                router.push('/drawings');
            } else {
                throw new Error('删除失败');
            }
        } catch (error) {
            message.error('删除失败，请稍后重试');
        }
    };

    // 导出工程量
    const handleExportQuantities = async () => {
        message.info('导出工程量功能开发中...');
    };

    // 导出计算报告
    const handleExportCalculationReport = async () => {
        message.info('导出计算报告功能开发中...');
    };

    // 初始化
    useEffect(() => {
        if (drawingId) {
            fetchDrawingDetail();
        }
    }, [drawingId]);

    if (loading && !drawing) {
        return (
            <div className="drawing-detail-loading">
                <Spin size="large" />
                <p>正在加载图纸详情...</p>
            </div>
        );
    }

    if (!drawing) {
        return (
            <div className="drawing-detail-error">
                <p>图纸不存在或已被删除</p>
                <Button onClick={() => router.push('/drawings')}>
                    <ArrowLeftOutlined /> 返回列表
                </Button>
            </div>
        );
    }

    return (
        <div className="drawing-detail-container">
            {/* 标题栏 */}
            <div className="drawing-detail-header">
                <div className="drawing-detail-title">
                    <Button 
                        type="text" 
                        icon={<ArrowLeftOutlined />} 
                        onClick={() => router.push('/drawings')}
                        className="back-button"
                    >
                        返回列表
                    </Button>
                    <h1 className="page-title">图纸详情分析</h1>
                </div>
                
                <div className="drawing-detail-actions">
                    <Button type="primary" icon={<DownloadOutlined />} onClick={handleExportQuantities} className="action-button export-button">
                        导出工程量
                    </Button>
                    <Button type="default" icon={<FileTextOutlined />} onClick={handleExportCalculationReport} className="action-button report-button">
                        导出计算书
                    </Button>
                    <Button type="default" danger icon={<DeleteOutlined />} onClick={handleDeleteDrawing} className="action-button delete-button">
                        删除图纸
                    </Button>
                </div>
            </div>

            {/* 主要内容区域 */}
            <div className="drawing-detail-content">
                <DrawingInfo drawing={drawing} />

                {/* OCR识别块 - 使用新的、自包含的渲染组件 */}
                <div className="nvidia-info-block">
                    <div className="nvidia-block-header">
                        <EyeOutlined className="nvidia-block-icon" />
                        <h2 className="nvidia-block-title">OCR识别结果</h2>
                    </div>
                    <div className="ocr-recognition-content">
                        <RichOcrResultDisplay drawingData={drawing} isProcessing={isOcrProcessing} />
                    </div>
                </div>

                <QuantityList 
                    drawing={drawing} 
                    isQuantityProcessing={isQuantityProcessing} 
                />
                
                {/* 导致崩溃的"工程量计算"按钮区域已被安全移除 */}
            </div>
        </div>
    );
};

export default DrawingDetail;