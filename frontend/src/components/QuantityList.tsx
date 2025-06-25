import React from 'react';
import { Table, Spin, Card, Descriptions, Tag, Divider, Typography } from 'antd';
import { BarChartOutlined, BuildOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Drawing } from '../types';

const { Text, Title } = Typography;

interface QuantityListProps {
    drawing: Drawing | null;
    isQuantityProcessing: boolean;
}

const QuantityList: React.FC<QuantityListProps> = ({ drawing, isQuantityProcessing }) => {
    
    // 工程量表格列定义
    const quantityColumns = {
        walls: [
            { title: '墙体编号', dataIndex: 'id', key: 'id' },
            { title: '尺寸', dataIndex: 'dimensions', key: 'dimensions' },
            { title: '长度(m)', dataIndex: 'length', key: 'length' },
            { title: '高度(m)', dataIndex: 'height', key: 'height' },
            { title: '厚度(m)', dataIndex: 'thickness', key: 'thickness' },
            { title: '体积(m³)', dataIndex: 'volume', key: 'volume' },
        ],
        columns: [
            { title: '柱子编号', dataIndex: 'id', key: 'id' },
            { title: '尺寸', dataIndex: 'dimensions', key: 'dimensions' },
            { title: '截面积(m²)', dataIndex: 'cross_section_area', key: 'cross_section_area' },
            { title: '高度(m)', dataIndex: 'height', key: 'height' },
            { title: '体积(m³)', dataIndex: 'volume', key: 'volume' },
        ],
        beams: [
            { title: '梁编号', dataIndex: 'id', key: 'id' },
            { title: '尺寸', dataIndex: 'dimensions', key: 'dimensions' },
            { title: '长度(m)', dataIndex: 'length', key: 'length' },
            { title: '截面积(m²)', dataIndex: 'cross_section_area', key: 'cross_section_area' },
            { title: '体积(m³)', dataIndex: 'volume', key: 'volume' },
        ],
        slabs: [
            { title: '板编号', dataIndex: 'id', key: 'id' },
            { title: '尺寸', dataIndex: 'dimensions', key: 'dimensions' },
            { title: '面积(m²)', dataIndex: 'area', key: 'area' },
            { title: '厚度(m)', dataIndex: 'thickness', key: 'thickness' },
            { title: '体积(m³)', dataIndex: 'volume', key: 'volume' },
        ],
        foundations: [
            { title: '基础编号', dataIndex: 'id', key: 'id' },
            { title: '尺寸', dataIndex: 'dimensions', key: 'dimensions' },
            { title: '长度(m)', dataIndex: 'length', key: 'length' },
            { title: '宽度(m)', dataIndex: 'width', key: 'width' },
            { title: '深度(m)', dataIndex: 'depth', key: 'depth' },
            { title: '体积(m³)', dataIndex: 'volume', key: 'volume' },
        ]
    };

    // 渲染新版工程量清单（输出点2）
    const renderNewQuantityList = () => {
        // 🔧 优先使用独立的工程量清单字段（轨道2输出点）
        let quantityDisplay = drawing?.quantity_list_display;
        
        // 降级到嵌套字段（兼容性）
        if (!quantityDisplay) {
            quantityDisplay = drawing?.recognition_results?.quantity_list_display;
        }
        
        if (!quantityDisplay || !quantityDisplay.success) {
            return null;
        }

        const { components, summary, table_columns } = quantityDisplay;

        return (
            <div>
                {/* 工程量汇总信息 */}
                <Card 
                    title={<><InfoCircleOutlined /> 工程量汇总</>}
                    style={{ marginBottom: 16 }}
                    size="small"
                >
                    <Descriptions column={3} size="small">
                        <Descriptions.Item label="构件总数">
                            <Text strong>{summary.total_components}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="构件类型">
                            <Text strong>{summary.component_types}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="总体积">
                            <Text strong style={{ color: '#1890ff' }}>{summary.total_volume}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="总面积">
                            <Text strong style={{ color: '#52c41a' }}>{summary.total_area}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="数据来源" span={2}>
                            <Text type="secondary">{summary.analysis_source}</Text>
                        </Descriptions.Item>
                    </Descriptions>

                    {/* 构件类型分解 */}
                    {summary.component_breakdown && Object.keys(summary.component_breakdown).length > 0 && (
                        <div style={{ marginTop: 16 }}>
                            <Text strong>构件类型分解：</Text>
                            <div style={{ marginTop: 8 }}>
                                {Object.entries(summary.component_breakdown).map(([type, stats]: [string, any]) => (
                                    <Tag key={type} color="blue" style={{ margin: 4 }}>
                                        {type}: {stats.count}个 
                                        {stats.volume > 0 && ` (${stats.volume.toFixed(2)}m³)`}
                                        {stats.area > 0 && ` (${stats.area.toFixed(2)}m²)`}
                                    </Tag>
                                ))}
                            </div>
                        </div>
                    )}
                </Card>

                {/* 详细构件清单表格 */}
                <Card 
                    title={<><BuildOutlined /> 构件工程量清单</>}
                    size="small"
                >
                    <Table
                        columns={table_columns}
                        dataSource={components}
                        rowKey="key"
                        pagination={{ 
                            pageSize: 10, 
                            showSizeChanger: true,
                            showQuickJumper: true,
                            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
                        }}
                        size="small"
                        scroll={{ x: true }}
                        bordered
                    />
                </Card>
            </div>
        );
    };

    const renderQuantityTables = () => {
        // 优先显示新版工程量清单
        const newQuantityList = renderNewQuantityList();
        if (newQuantityList) {
            return newQuantityList;
        }

        // 降级到旧版工程量清单
        if (!drawing?.recognition_results?.quantities) {
            return (
                <div className="quantity-empty-state">
                    <BarChartOutlined className="quantity-empty-icon" />
                    <p className="quantity-empty-text">暂无工程量数据</p>
                    <p className="quantity-empty-hint">Vision分析完成后将自动计算工程量并生成清单</p>
                </div>
            );
        }

        const quantities = drawing.recognition_results.quantities;

        return (
            <div>
                {/* 工程量汇总 */}
                {quantities.total && (
                    <div className="quantity-summary">
                        <h3 className="quantity-summary-title">工程量汇总</h3>
                        <div className="quantity-summary-grid">
                            <div className="quantity-summary-item">
                                <span className="quantity-summary-label">墙体体积</span>
                                <span className="quantity-summary-value">
                                    {quantities.total.wall_volume?.toFixed(2) || '0.00'} m³
                                </span>
                            </div>
                            <div className="quantity-summary-item">
                                <span className="quantity-summary-label">柱子体积</span>
                                <span className="quantity-summary-value">
                                    {quantities.total.column_volume?.toFixed(2) || '0.00'} m³
                                </span>
                            </div>
                            <div className="quantity-summary-item">
                                <span className="quantity-summary-label">梁体积</span>
                                <span className="quantity-summary-value">
                                    {quantities.total.beam_volume?.toFixed(2) || '0.00'} m³
                                </span>
                            </div>
                            <div className="quantity-summary-item">
                                <span className="quantity-summary-label">板体积</span>
                                <span className="quantity-summary-value">
                                    {quantities.total.slab_volume?.toFixed(2) || '0.00'} m³
                                </span>
                            </div>
                            <div className="quantity-summary-item">
                                <span className="quantity-summary-label">基础体积</span>
                                <span className="quantity-summary-value">
                                    {quantities.total.foundation_volume?.toFixed(2) || '0.00'} m³
                                </span>
                            </div>
                            <div className="quantity-summary-item">
                                <span className="quantity-summary-label">总体积</span>
                                <span className="quantity-summary-value">
                                    {quantities.total.total_volume?.toFixed(2) || '0.00'} m³
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* 详细工程量表格 */}
                {quantities.walls && Array.isArray(quantities.walls) && quantities.walls.length > 0 && (
                    <div className="nvidia-quantity-table">
                        <h4 style={{ color: '#76b900', marginBottom: 16 }}>🧱 墙体工程量</h4>
                        <Table
                            columns={quantityColumns.walls}
                            dataSource={quantities.walls}
                            rowKey="id"
                            pagination={false}
                            size="middle"
                            scroll={{ x: true }}
                        />
                    </div>
                )}

                {quantities.columns && Array.isArray(quantities.columns) && quantities.columns.length > 0 && (
                    <div className="nvidia-quantity-table">
                        <h4 style={{ color: '#76b900', marginBottom: 16 }}>🏛️ 柱子工程量</h4>
                        <Table
                            columns={quantityColumns.columns}
                            dataSource={quantities.columns}
                            rowKey="id"
                            pagination={false}
                            size="middle"
                            scroll={{ x: true }}
                        />
                    </div>
                )}

                {quantities.beams && Array.isArray(quantities.beams) && quantities.beams.length > 0 && (
                    <div className="nvidia-quantity-table">
                        <h4 style={{ color: '#76b900', marginBottom: 16 }}>🌉 梁工程量</h4>
                        <Table
                            columns={quantityColumns.beams}
                            dataSource={quantities.beams}
                            rowKey="id"
                            pagination={false}
                            size="middle"
                            scroll={{ x: true }}
                        />
                    </div>
                )}

                {quantities.slabs && Array.isArray(quantities.slabs) && quantities.slabs.length > 0 && (
                    <div className="nvidia-quantity-table">
                        <h4 style={{ color: '#76b900', marginBottom: 16 }}>🗂️ 板工程量</h4>
                        <Table
                            columns={quantityColumns.slabs}
                            dataSource={quantities.slabs}
                            rowKey="id"
                            pagination={false}
                            size="middle"
                            scroll={{ x: true }}
                        />
                    </div>
                )}

                {quantities.foundations && Array.isArray(quantities.foundations) && quantities.foundations.length > 0 && (
                    <div className="nvidia-quantity-table">
                        <h4 style={{ color: '#76b900', marginBottom: 16 }}>🏗️ 基础工程量</h4>
                        <Table
                            columns={quantityColumns.foundations}
                            dataSource={quantities.foundations}
                            rowKey="id"
                            pagination={false}
                            size="middle"
                            scroll={{ x: true }}
                        />
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="nvidia-info-block">
            <div className="nvidia-block-header">
                <BarChartOutlined className="nvidia-block-icon" />
                <h2 className="nvidia-block-title">工程量清单</h2>
            </div>
            <div className="quantity-list-content">
                {isQuantityProcessing ? (
                    <div className="ocr-loading-state">
                        <Spin size="large" />
                        <p className="ocr-loading-text">正在计算工程量...</p>
                    </div>
                ) : (
                    renderQuantityTables()
                )}
            </div>
        </div>
    );
};

export default QuantityList; 