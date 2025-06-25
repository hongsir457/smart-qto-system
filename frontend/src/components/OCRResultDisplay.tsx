import React, { useState } from 'react';
import { Card, Descriptions, Tag, Collapse, Typography, Progress, Empty, Tabs, Button, message, Table, Space, Divider } from 'antd';
import { 
    FileTextOutlined, 
    BuildOutlined, 
    ProjectOutlined, 
    UserOutlined,
    CalendarOutlined,
    SettingOutlined,
    InfoCircleOutlined,
    CopyOutlined,
    EyeOutlined,
    ReloadOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Component {
    component_id?: string;
    id?: string;
    component_type?: string;
    type?: string;
    dimensions?: string;
    material?: string;
    quantity?: number;
    unit?: string;
}

interface OCRResult {
    meta: any;
    raw_statistics: any;
    classified_content: any;
    project_analysis: any;
    drawing_analysis: any;
    component_analysis: any;
    construction_specs: string[];
    readable_summary: string;
    readable_text?: string;
    intelligent_corrections?: any[];
    sealos_storage?: {
        saved: boolean;
        s3_key?: string;
        filename?: string;
        save_time?: string;
        error?: string;
        message?: string;
        real_data?: boolean;
        format?: string;
        s3_url?: string;
    };
    components?: Component[];
    ocr_texts?: string[];
    analysis_summary?: string;
    analysis_engine?: string;
    pipeline_type?: string;
    processing_time?: string;
    // 新增输出点1: OCR识别块数据
    ocr_recognition_display?: {
        drawing_basic_info: {
            drawing_title?: string;
            drawing_number?: string;
            scale?: string;
            project_name?: string;
            drawing_type?: string;
        };
        component_overview: {
            component_ids: string[];
            component_types: string[];
            material_grades: string[];
            axis_lines: string[];
            summary: {
                total_components?: number;
                main_structure_type?: string;
                complexity_level?: string;
            };
        };
        ocr_source_info: {
            total_slices: number;
            ocr_text_count: number;
            analysis_method: string;
        };
    };
    // 新增输出点2: 工程量清单块数据
    quantity_list_display?: {
        success: boolean;
        components: any[];
        summary: {
            total_components: number;
            component_types: number;
            total_volume: string;
            total_area: string;
            component_breakdown: any;
            analysis_source: string;
        };
        table_columns: any[];
    };
}

interface OCRResultDisplayProps {
    ocrResult: OCRResult;
}

const OCRResultDisplay: React.FC<OCRResultDisplayProps> = ({ ocrResult }) => {
    // 优先显示可读文本，若失败自动降级显示结构化内容
    const [activeTab, setActiveTab] = useState(ocrResult?.readable_text ? 'readable' : 'structured');
    const [showStructured, setShowStructured] = useState(false);
    const [retrying, setRetrying] = useState(false);

    if (!ocrResult) {
        return <Empty description="暂无OCR识别结果" />;
    }

    const { meta, raw_statistics, classified_content, project_analysis, drawing_analysis, component_analysis, readable_summary, readable_text, intelligent_corrections, sealos_storage, components, ocr_texts } = ocrResult;

    // 复制文本到剪贴板
    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text).then(() => {
            message.success('已复制到剪贴板');
        });
    };

    // 获取置信度颜色
    const getConfidenceColor = (confidence: number) => {
        if (confidence >= 0.9) return 'green';
        if (confidence >= 0.7) return 'orange';
        return 'red';
    };

    // 渲染文本项目列表
    const renderTextItems = (items: Array<{ text: string; confidence: number; index: number }>, maxItems = 10) => {
        if (!items || items.length === 0) {
            return <Text type="secondary">暂无数据</Text>;
        }
        return (
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                {items.slice(0, maxItems).map((item, idx) => (
                    <div key={idx} style={{ marginBottom: 8 }}>
                        <Text strong>{item.text}</Text>
                        <Tag 
                            color={getConfidenceColor(item.confidence)} 
                            style={{ marginLeft: 8 }}
                        >
                            置信度: {(item.confidence * 100).toFixed(1)}%
                        </Tag>
                    </div>
                ))}
                {items.length > maxItems && (
                    <Text type="secondary">... 还有 {items.length - maxItems} 项</Text>
                )}
            </div>
        );
    };

    // 构件清单表格列定义
    const componentColumns = [
        {
            title: '构件编号',
            dataIndex: 'component_id',
            key: 'component_id',
            width: 120,
            render: (text: string, record: Component) => {
                const id = text || record.id || '-';
                return <Text strong>{id}</Text>;
            }
        },
        {
            title: '构件类型',
            dataIndex: 'component_type',
            key: 'component_type',
            width: 100,
            render: (text: string, record: Component) => (
                <Tag color="blue">{text || record.type || '-'}</Tag>
            )
        },
        {
            title: '尺寸规格',
            dataIndex: 'dimensions',
            key: 'dimensions',
            width: 150,
            render: (text: string) => text || '-'
        },
        {
            title: '材料',
            dataIndex: 'material',
            key: 'material',
            width: 100,
            render: (text: string) => text || '-'
        },
        {
            title: '数量',
            dataIndex: 'quantity',
            key: 'quantity',
            width: 80,
            render: (num: number) => num || 0
        },
        {
            title: '单位',
            dataIndex: 'unit',
            key: 'unit',
            width: 60,
            render: (text: string) => text || '-'
        }
    ];

    // 将原始OCR文本转换为自然语言描述
    const generateNaturalLanguageDescription = (texts: string[]): string => {
        if (texts.length === 0) return "未识别到文本内容";
        
        const structuralTexts = texts.filter(text => 
            text.includes('框架柱') || text.includes('K-') || text.includes('×') || text.includes('C30')
        );
        const infoTexts = texts.filter(text => 
            text.includes('图号') || text.includes('比例') || text.includes('设计') || text.includes('审核') || text.includes('年')
        );
        
        let description = "通过OCR识别，从图纸中提取到以下信息：\n\n";
        
        if (structuralTexts.length > 0) {
            description += `🏗️ **结构构件信息**：识别到${structuralTexts.length}条构件相关文本，包括${structuralTexts.slice(0, 3).join('、')}`;
            if (structuralTexts.length > 3) {
                description += `等${structuralTexts.length}项构件信息`;
            }
            description += "。\n\n";
        }
        
        if (infoTexts.length > 0) {
            description += `📋 **图纸信息**：识别到图纸基本信息，包括${infoTexts.join('、')}。\n\n`;
        }
        
        description += `📊 **识别统计**：共识别到${texts.length}条文本信息，经过AI分析处理后提取出${ocrResult.components?.length || 0}个结构化构件数据。`;
        
        return description;
    };

    // 可读文本标签页内容
    const readableTabContent = readable_text ? (
        <Card 
            title="📋 OCR识别结果报告"
            extra={
                <Button 
                    icon={<CopyOutlined />} 
                    onClick={() => copyToClipboard(readable_text)}
                    size="small"
                >
                    复制文本
                </Button>
            }
            style={{ marginBottom: 16 }}
            bodyStyle={{ background: '#f8fafb' }}
        >
            <Paragraph>
                <pre style={{ 
                    whiteSpace: 'pre-wrap', 
                    fontSize: '14px',
                    lineHeight: '1.6',
                    backgroundColor: '#f6f8fa',
                    padding: '16px',
                    borderRadius: '6px',
                    border: '1px solid #e1e4e8',
                    fontFamily: 'Monaco, Consolas, "Lucida Console", monospace'
                }}>
                    {readable_text}
                </pre>
            </Paragraph>
        </Card>
    ) : (
        <Empty description="暂无可读文本" />
    );

    // 渲染OCR识别块（输出点1）
    const renderOCRRecognitionBlock = () => {
        const ocrDisplay = ocrResult.ocr_recognition_display;
        if (!ocrDisplay) return null;

        const { drawing_basic_info, component_overview, ocr_source_info } = ocrDisplay;

        return (
            <Card 
                title={<><EyeOutlined /> OCR识别结果</>}
                style={{ marginBottom: 16 }}
                bodyStyle={{ background: '#f8fafb' }}
            >
                {/* 图纸基本信息 */}
                <div style={{ marginBottom: 16 }}>
                    <Text strong>📋 图纸基本信息</Text>
                    <Descriptions column={2} size="small" style={{ marginTop: 8 }}>
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
                </div>

                <Divider />

                {/* 构件概览信息 */}
                <div style={{ marginBottom: 16 }}>
                    <Text strong>🏗️ 构件概览信息</Text>
                    <div style={{ marginTop: 8 }}>
                        <div style={{ marginBottom: 8 }}>
                            <Text type="secondary">构件编号清单：</Text>
                            <div style={{ marginTop: 4 }}>
                                {component_overview.component_ids.length > 0 ? (
                                    component_overview.component_ids.map(id => (
                                        <Tag key={id} color="blue" style={{ margin: 2 }}>{id}</Tag>
                                    ))
                                ) : (
                                    <Text type="secondary">暂无构件编号</Text>
                                )}
                            </div>
                        </div>
                        
                        <div style={{ marginBottom: 8 }}>
                            <Text type="secondary">构件类型：</Text>
                            <div style={{ marginTop: 4 }}>
                                {component_overview.component_types.length > 0 ? (
                                    component_overview.component_types.map(type => (
                                        <Tag key={type} color="green" style={{ margin: 2 }}>{type}</Tag>
                                    ))
                                ) : (
                                    <Text type="secondary">暂无构件类型</Text>
                                )}
                            </div>
                        </div>

                        <div style={{ marginBottom: 8 }}>
                            <Text type="secondary">材料等级：</Text>
                            <div style={{ marginTop: 4 }}>
                                {component_overview.material_grades.length > 0 ? (
                                    component_overview.material_grades.map(material => (
                                        <Tag key={material} color="orange" style={{ margin: 2 }}>{material}</Tag>
                                    ))
                                ) : (
                                    <Text type="secondary">暂无材料等级</Text>
                                )}
                            </div>
                        </div>

                        <div style={{ marginBottom: 8 }}>
                            <Text type="secondary">轴线编号：</Text>
                            <div style={{ marginTop: 4 }}>
                                {component_overview.axis_lines.length > 0 ? (
                                    component_overview.axis_lines.map(axis => (
                                        <Tag key={axis} color="purple" style={{ margin: 2 }}>{axis}</Tag>
                                    ))
                                ) : (
                                    <Text type="secondary">暂无轴线编号</Text>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <Divider />

                {/* 分析汇总 */}
                <div>
                    <Text strong>📊 分析汇总</Text>
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
        );
    };

    // 结构化数据标签页内容
    const structuredTabContent = (
        <div>
            {/* 新增OCR识别块 */}
            {renderOCRRecognitionBlock()}

            {/* 基本信息卡片 */}
            <Card 
                title={<><InfoCircleOutlined /> 基本信息</>}
                style={{ marginBottom: 16 }}
                bodyStyle={{ background: '#f8fafb' }}
            >
                <Descriptions column={2} size="small">
                    <Descriptions.Item label="处理ID">{meta.result_id}</Descriptions.Item>
                    <Descriptions.Item label="处理时间">{new Date(meta.process_time).toLocaleString()}</Descriptions.Item>
                    <Descriptions.Item label="总文本数">{raw_statistics.total_texts}</Descriptions.Item>
                    <Descriptions.Item label="平均置信度">
                        <Progress 
                            percent={Math.round(raw_statistics.average_confidence * 100)} 
                            size="small" 
                            style={{ width: 100 }}
                        />
                    </Descriptions.Item>
                </Descriptions>
                <div style={{ marginTop: 16 }}>
                    <Text strong>可读摘要：</Text>
                    <Paragraph style={{ marginTop: 8, padding: 12, backgroundColor: '#f6f8fa', borderRadius: 6 }}>
                        {readable_summary}
                    </Paragraph>
                </div>
            </Card>
            {/* 项目和图纸信息 */}
            <Card 
                title={<><ProjectOutlined /> 项目与图纸信息</>}
                style={{ marginBottom: 16 }}
                bodyStyle={{ background: '#f8fafb' }}
            >
                <Descriptions column={1} size="small">
                    <Descriptions.Item label="项目名称">
                        {project_analysis?.project_name || '未识别'}
                    </Descriptions.Item>
                    <Descriptions.Item label="公司名称">
                        {project_analysis?.company_name || '未识别'}
                    </Descriptions.Item>
                    <Descriptions.Item label="图纸名称">
                        {drawing_analysis?.drawing_name || '未识别'}
                    </Descriptions.Item>
                    <Descriptions.Item label="比例">
                        {drawing_analysis?.scale || '未识别'}
                    </Descriptions.Item>
                    <Descriptions.Item label="图号">
                        {drawing_analysis?.drawing_number || '未识别'}
                    </Descriptions.Item>
                </Descriptions>
            </Card>
            {/* 构件分析 */}
            <Card 
                title={<><BuildOutlined /> 构件分析</>}
                style={{ marginBottom: 16 }}
                bodyStyle={{ background: '#f8fafb' }}
            >
                <Descriptions column={2} size="small">
                    <Descriptions.Item label="构件总数">{component_analysis?.total_components}</Descriptions.Item>
                    <Descriptions.Item label="尺寸总数">{component_analysis?.total_dimensions}</Descriptions.Item>
                </Descriptions>
                {component_analysis?.component_types && Object.keys(component_analysis.component_types).length > 0 && (
                    <div style={{ marginTop: 16 }}>
                        <Text strong>构件类型统计：</Text>
                        <div style={{ marginTop: 8 }}>
                            {Object.entries(component_analysis.component_types).map(([type, count]) => (
                                <Tag key={type} style={{ margin: 4 }}>
                                    {type}: {count as number}
                                </Tag>
                            ))}
                        </div>
                    </div>
                )}
            </Card>
            {/* 详细分类内容 */}
            <Card 
                title={<><SettingOutlined /> 详细内容分类</>}
                style={{ marginBottom: 16 }}
                bodyStyle={{ background: '#f8fafb' }}
            >
                <Collapse>
                    <Panel header={`项目信息 (${classified_content?.project_info?.length || 0} 项)`} key="project">
                        {renderTextItems(classified_content?.project_info)}
                    </Panel>
                    <Panel header={`图纸信息 (${classified_content?.drawing_info?.length || 0} 项)`} key="drawing">
                        {renderTextItems(classified_content?.drawing_info)}
                    </Panel>
                    <Panel header={`构件编号 (${classified_content?.component_codes?.length || 0} 项)`} key="components">
                        {renderTextItems(classified_content?.component_codes)}
                    </Panel>
                    <Panel header={`尺寸信息 (${classified_content?.dimensions?.length || 0} 项)`} key="dimensions">
                        {renderTextItems(classified_content?.dimensions)}
                    </Panel>
                    <Panel header={`材料规格 (${classified_content?.materials?.length || 0} 项)`} key="materials">
                        {renderTextItems(classified_content?.materials)}
                    </Panel>
                    <Panel header={`标高信息 (${classified_content?.elevations?.length || 0} 项)`} key="elevations">
                        {renderTextItems(classified_content?.elevations)}
                    </Panel>
                    <Panel header={`人员信息 (${classified_content?.personnel?.length || 0} 项)`} key="personnel">
                        {renderTextItems(classified_content?.personnel)}
                    </Panel>
                    <Panel header={`规范要求 (${classified_content?.specifications?.length || 0} 项)`} key="specifications">
                        {renderTextItems(classified_content?.specifications)}
                    </Panel>
                </Collapse>
            </Card>
            {/* Intelligent Corrections */}
            {intelligent_corrections && intelligent_corrections.length > 0 && (
                <Card 
                    title={<><SettingOutlined /> 智能纠错</>}
                    style={{ marginBottom: 16 }}
                    bodyStyle={{ background: '#f8fafb' }}
                >
                    <Collapse>
                        {intelligent_corrections.map((correction, index) => (
                            <Panel header={`纠错 ${index + 1}`} key={`correction-${index}`}>
                                <Descriptions column={2} size="small">
                                    <Descriptions.Item label="原文">{correction.original}</Descriptions.Item>
                                    <Descriptions.Item label="纠正后">{correction.corrected}</Descriptions.Item>
                                    <Descriptions.Item label="置信度">{correction.confidence.toFixed(2)}</Descriptions.Item>
                                    <Descriptions.Item label="方法">{correction.correction_method}</Descriptions.Item>
                                    <Descriptions.Item label="说明">{correction.explanation}</Descriptions.Item>
                                    <Descriptions.Item label="类别">{correction.category}</Descriptions.Item>
                                </Descriptions>
                            </Panel>
                        ))}
                    </Collapse>
                </Card>
            )}
            {/* Sealos存储信息 */}
            {sealos_storage && (
                <Card 
                    title="☁️ Sealos存储信息"
                    size="small"
                    bodyStyle={{ background: '#f8fafb' }}
                >
                    <Descriptions column={1} size="small">
                        <Descriptions.Item label="存储状态">
                            <Tag color={sealos_storage.saved ? 'green' : 'red'}>
                                {sealos_storage.saved ? '✅ 已保存' : '❌ 保存失败'}
                            </Tag>
                        </Descriptions.Item>
                        {sealos_storage.saved && (
                            <>
                                <Descriptions.Item label="文件名">
                                    {sealos_storage.filename}
                                </Descriptions.Item>
                                <Descriptions.Item label="S3键">
                                    {sealos_storage.s3_key}
                                </Descriptions.Item>
                                <Descriptions.Item label="保存时间">
                                    {sealos_storage.save_time && new Date(sealos_storage.save_time).toLocaleString()}
                                </Descriptions.Item>
                                {sealos_storage.s3_url && (
                                    <Descriptions.Item label="TXT下载">
                                        <a href={sealos_storage.s3_url} target="_blank" rel="noopener noreferrer">下载TXT</a>
                                    </Descriptions.Item>
                                )}
                            </>
                        )}
                        {!sealos_storage.saved && (
                            <>
                                {sealos_storage.error && (
                                    <Descriptions.Item label="错误信息">
                                        <Text type="danger">{sealos_storage.error}</Text>
                                    </Descriptions.Item>
                                )}
                                <Descriptions.Item label="操作">
                                    <Button 
                                        icon={<ReloadOutlined />} 
                                        loading={retrying}
                                        onClick={() => {
                                            setRetrying(true);
                                            window.location.reload();
                                        }}
                                        size="small"
                                    >
                                        重试
                                    </Button>
                                </Descriptions.Item>
                                {ocrResult.readable_text && (
                                    <Descriptions.Item label="本地TXT">
                                        <Button 
                                            icon={<CopyOutlined />} 
                                            onClick={() => ocrResult.readable_text && copyToClipboard(ocrResult.readable_text)}
                                            size="small"
                                        >
                                            复制TXT内容
                                        </Button>
                                    </Descriptions.Item>
                                )}
                            </>
                        )}
                    </Descriptions>
                </Card>
            )}
            {/* 原始OCR文本的自然语言描述 */}
            {ocr_texts && ocr_texts.length > 0 && (
                <Card 
                    title={
                        <span>
                            <EyeOutlined style={{ marginRight: 8 }} />
                            OCR识别文本分析
                        </span>
                    }
                    style={{ marginBottom: 16 }}
                    size="small"
                >
                    <Paragraph style={{ whiteSpace: 'pre-line', marginBottom: 0 }}>
                        {generateNaturalLanguageDescription(ocr_texts)}
                    </Paragraph>
                    
                    <Divider style={{ margin: '12px 0' }} />
                    
                    <div>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                            原始识别文本：{ocr_texts.join(' | ')}
                        </Text>
                    </div>
                </Card>
            )}
            {/* 构件清单 */}
            {components && components.length > 0 && (
                <Card 
                    title={<><SettingOutlined /> 构件清单</>}
                    style={{ marginBottom: 16 }}
                    bodyStyle={{ background: '#f8fafb' }}
                >
                    <Table 
                        columns={componentColumns} 
                        dataSource={components} 
                        rowKey="component_id"
                        pagination={{ pageSize: 10 }}
                    />
                </Card>
            )}
        </div>
    );

    // 自动降级逻辑：如果TXT失败，自动切换到结构化内容
    React.useEffect(() => {
        if (!ocrResult.readable_text && activeTab === 'readable') {
            setActiveTab('structured');
            setShowStructured(true);
        }
    }, [ocrResult.readable_text, activeTab]);

    return (
        <div style={{ padding: 0 }}>
            <Title level={4} style={{ margin: '0 0 16px 0', color: '#222' }}>
                <FileTextOutlined /> OCR识别结果
            </Title>
            <Tabs 
                activeKey={activeTab} 
                onChange={setActiveTab} 
                style={{ marginBottom: 16 }}
                items={[
                    {
                        key: 'readable',
                        label: <><EyeOutlined /> 可读文本</>,
                        children: readableTabContent
                    },
                    {
                        key: 'structured',
                        label: <><SettingOutlined /> 结构化数据</>,
                        children: structuredTabContent
                    }
                ]}
            />
        </div>
    );
};

export default OCRResultDisplay; 