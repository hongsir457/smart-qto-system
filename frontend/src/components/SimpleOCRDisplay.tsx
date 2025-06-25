import React from 'react';
import { Table, Card, Tag, Typography } from 'antd';
import { BuildOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface Component {
    id: string;
    type: string;
    dimensions?: string;
}

interface SimpleOCRDisplayProps {
    drawingData: any;
}

const extractRelevantComponents = (data: any): Component[] => {
    const recResults = data?.recognition_results;
    if (!recResults) return [];

    const componentsSource = recResults.components || recResults.all_ocr_results?.[0]?.ai_components || [];
    
    return componentsSource.map((c: any) => ({
        id: c.component_id || c.id || '未知ID',
        type: c.component_type || c.type || '未知类型',
        dimensions: c.dimensions || 'N/A',
    }));
};

const SimpleOCRDisplay: React.FC<SimpleOCRDisplayProps> = ({ drawingData }) => {
    const components = extractRelevantComponents(drawingData);

    if (components.length === 0) {
        return (
            <Card>
                <Text type="secondary">在 recognition_results 中未找到有效的构件数据。</Text>
            </Card>
        );
    }

    const columns = [
        {
            title: '构件ID',
            dataIndex: 'id',
            key: 'id',
            render: (text: string) => <Text strong>{text}</Text>,
        },
        {
            title: '构件类型',
            dataIndex: 'type',
            key: 'type',
            render: (text: string) => <Tag color="cyan">{text}</Tag>,
        },
        {
            title: '尺寸',
            dataIndex: 'dimensions',
            key: 'dimensions',
        },
    ];

    return (
        <Card 
            title={
                <span>
                    <BuildOutlined style={{ marginRight: 8 }} />
                    构件清单 (共 {components.length} 个)
                </span>
            }
        >
            <Table
                columns={columns}
                dataSource={components.map(c => ({ ...c, key: c.id }))}
                pagination={{ pageSize: 5 }}
                size="small"
            />
        </Card>
    );
};

export default SimpleOCRDisplay; 