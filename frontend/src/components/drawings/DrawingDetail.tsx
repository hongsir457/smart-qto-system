import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { 
  Card, 
  Descriptions, 
  Tag, 
  Button, 
  Alert, 
  Spin, 
  Empty, 
  Typography, 
  Table, 
  Statistic,
  Row,
  Col,
  Space
} from 'antd';
import { EyeOutlined, ReloadOutlined, DeleteOutlined, DownloadOutlined } from '@ant-design/icons';
import RealTimeProgress from '../RealTimeProgress';

const { Title, Text, Paragraph } = Typography;

interface DrawingDetailData {
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
  ocr_recognition_display?: string | any;
  quantity_list_display?: string | any;
  components_count?: number;
  task_id?: string;
}

export default function DrawingDetail() {
  const router = useRouter();
  const { id } = router.query;
  const drawingId = Array.isArray(id) ? parseInt(id[0]) : parseInt(id as string);

  const [loading, setLoading] = useState(true);
  const [drawing, setDrawing] = useState<DrawingDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isOcrProcessing, setIsOcrProcessing] = useState(false);

  // 获取图纸详情
  const fetchDrawingDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      
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
        if (response.status === 401) {
          throw new Error('认证失败，请重新登录');
        } else if (response.status === 404) {
          throw new Error('图纸不存在');
        } else {
          throw new Error(`请求失败: ${response.status}`);
        }
      }
      
      const result = await response.json();
      setDrawing(result);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取图纸详情失败';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 处理OCR
  const handleOCR = async () => {
    if (!drawing) return;
    
    setIsOcrProcessing(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        alert('请先登录');
        return;
      }
      
      const response = await fetch(`/api/v1/drawings/${drawingId}/ocr`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`OCR处理失败: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.task_id) {
        alert('OCR识别任务已启动');
        setTimeout(() => {
          fetchDrawingDetail();
        }, 2000);
      }
    } catch (error) {
      console.error('OCR处理失败:', error);
      alert('OCR处理失败，请稍后重试');
    } finally {
      setIsOcrProcessing(false);
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
        alert('删除成功');
        router.push('/drawings');
      } else {
        throw new Error('删除失败');
      }
    } catch (error) {
      alert('删除失败，请稍后重试');
    }
  };

  // 初始化
  useEffect(() => {
    if (drawingId) {
      fetchDrawingDetail();
    }
  }, [drawingId]);

  // 显示错误状态
  if (error) {
    return (
      <div style={{ padding: '50px', textAlign: 'center' }}>
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" danger onClick={fetchDrawingDetail}>
              重试
            </Button>
          }
        />
      </div>
    );
  }

  // 显示加载状态
  if (loading) {
    return (
      <div style={{ padding: '50px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>加载图纸详情中...</div>
      </div>
    );
  }

  // 图纸不存在
  if (!drawing) {
    return (
      <div style={{ padding: '50px', textAlign: 'center' }}>
        <Empty 
          description="图纸不存在"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </div>
    );
  }

  // 渲染OCR识别结果
  const renderOCRResults = () => {
    if (!drawing.ocr_recognition_display) {
      return (
        <Card title="👁️ OCR识别结果" style={{ marginTop: 16 }}>
          <Empty description="暂无OCR识别结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <Text type="secondary">未能从图纸数据中找到有效的OCR识别结果。</Text>
          </div>
        </Card>
      );
    }

    let ocrData: any = {};
    try {
      ocrData = typeof drawing.ocr_recognition_display === 'string' 
        ? JSON.parse(drawing.ocr_recognition_display)
        : drawing.ocr_recognition_display;
    } catch (error) {
      console.error('解析OCR识别结果失败:', error);
      return (
        <Card title="👁️ OCR识别结果" style={{ marginTop: 16 }}>
          <Alert message="数据解析失败" type="error" />
        </Card>
      );
    }

    const { drawing_basic_info, component_overview, ocr_source_info } = ocrData;

    return (
      <Card title="👁️ OCR识别结果" style={{ marginTop: 16 }}>
        {/* 图纸基本信息 */}
        {drawing_basic_info && (
          <Card type="inner" title="📋 图纸基本信息" style={{ marginBottom: 16 }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="图纸名称">{drawing_basic_info.drawing_title || '—'}</Descriptions.Item>
              <Descriptions.Item label="图纸编号">{drawing_basic_info.drawing_number || '—'}</Descriptions.Item>
              <Descriptions.Item label="比例">{drawing_basic_info.scale || '—'}</Descriptions.Item>
              <Descriptions.Item label="项目名称">{drawing_basic_info.project_name || '—'}</Descriptions.Item>
              <Descriptions.Item label="图纸类型">{drawing_basic_info.drawing_type || '—'}</Descriptions.Item>
              <Descriptions.Item label="设计单位">{drawing_basic_info.design_unit || '—'}</Descriptions.Item>
            </Descriptions>
          </Card>
        )}

        {/* 构件概览 */}
        {component_overview && (
          <Card type="inner" title="🏗️ 构件概览" style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 12 }}>
              <Text strong>构件编号：</Text>
              <div style={{ marginTop: 8 }}>
                {component_overview.component_ids?.map((id: string, index: number) => (
                  <Tag key={index} color="blue" style={{ marginBottom: 4 }}>{id}</Tag>
                ))}
              </div>
            </div>
            
            <div style={{ marginBottom: 12 }}>
              <Text strong>构件类型：</Text>
              <div style={{ marginTop: 8 }}>
                {component_overview.component_types?.map((type: string, index: number) => (
                  <Tag key={index} color="green" style={{ marginBottom: 4 }}>{type}</Tag>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 12 }}>
              <Text strong>材料等级：</Text>
              <div style={{ marginTop: 8 }}>
                {component_overview.material_grades?.map((grade: string, index: number) => (
                  <Tag key={index} color="orange" style={{ marginBottom: 4 }}>{grade}</Tag>
                ))}
              </div>
            </div>

            {component_overview.summary && (
              <div style={{ marginTop: 16, padding: 12, backgroundColor: '#f6f8fa', borderRadius: 4 }}>
                <Text strong>汇总信息：</Text>
                <div style={{ marginTop: 8 }}>
                  <Text>总构件数：{component_overview.summary.total_components} 个</Text><br/>
                  <Text>主要结构类型：{component_overview.summary.main_structure_type}</Text><br/>
                  <Text>复杂度级别：{component_overview.summary.complexity_level}</Text>
                </div>
              </div>
            )}
          </Card>
        )}

        {/* OCR处理信息 */}
        {ocr_source_info && (
          <Card type="inner" title="⚙️ 处理信息">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="切片总数">{ocr_source_info.total_slices || '—'}</Descriptions.Item>
              <Descriptions.Item label="文本数量">{ocr_source_info.ocr_text_count || '—'}</Descriptions.Item>
              <Descriptions.Item label="分析方法">{ocr_source_info.analysis_method || '—'}</Descriptions.Item>
              <Descriptions.Item label="处理时间">{ocr_source_info.processing_time ? `${ocr_source_info.processing_time}秒` : '—'}</Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Card>
    );
  };

  // 渲染工程量清单
  const renderQuantityList = () => {
    if (!drawing.quantity_list_display) {
      return (
        <Card title="📊 工程量清单" style={{ marginTop: 16 }}>
          <Empty description="暂无工程量数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <Text type="secondary">Vision分析完成后将自动计算工程量并生成清单</Text>
          </div>
        </Card>
      );
    }

    let quantityData: any = {};
    try {
      quantityData = typeof drawing.quantity_list_display === 'string'
        ? JSON.parse(drawing.quantity_list_display)
        : drawing.quantity_list_display;
    } catch (error) {
      console.error('解析工程量数据失败:', error);
      return (
        <Card title="📊 工程量清单" style={{ marginTop: 16 }}>
          <Alert message="数据解析失败" type="error" />
        </Card>
      );
    }

    const { components = [], summary, table_columns } = quantityData;

    // 构件表格列定义
    const columns = [
      {
        title: '构件编号',
        dataIndex: 'component_id',
        key: 'component_id',
        width: 120,
        render: (text: string) => <Text strong>{text}</Text>
      },
      {
        title: '构件类型',
        dataIndex: 'component_type',
        key: 'component_type',
        width: 100,
        render: (type: string) => <Tag color="blue">{type}</Tag>
      },
      {
        title: '尺寸规格',
        dataIndex: 'dimensions',
        key: 'dimensions',
        width: 150
      },
      {
        title: '材料等级',
        dataIndex: 'material',
        key: 'material',
        width: 100,
        render: (material: string) => <Tag color="green">{material}</Tag>
      },
      {
        title: '体积',
        dataIndex: 'volume',
        key: 'volume',
        width: 80,
        render: (volume: string) => `${volume}m³`
      },
      {
        title: '面积',
        dataIndex: 'area',
        key: 'area',
        width: 80,
        render: (area: string) => `${area}m²`
      },
      {
        title: '结构作用',
        dataIndex: 'structural_role',
        key: 'structural_role',
        width: 100
      },
      {
        title: '置信度',
        dataIndex: 'confidence',
        key: 'confidence',
        width: 80,
        render: (confidence: string) => (
          <Text type={parseFloat(confidence) > 90 ? 'success' : 'warning'}>
            {confidence}
          </Text>
        )
      }
    ];

    return (
      <Card title="📊 工程量清单" style={{ marginTop: 16 }}>
        {/* 汇总信息 */}
        {summary && (
          <Card type="inner" title="📈 汇总统计" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="构件总数" value={summary.total_components} suffix="个" />
              </Col>
              <Col span={6}>
                <Statistic title="构件类型" value={summary.component_types} suffix="种" />
              </Col>
              <Col span={6}>
                <Statistic title="总体积" value={summary.total_volume} />
              </Col>
              <Col span={6}>
                <Statistic title="总面积" value={summary.total_area} />
              </Col>
            </Row>

            {summary.component_breakdown && (
              <div style={{ marginTop: 16 }}>
                <Text strong>分类统计：</Text>
                <div style={{ marginTop: 8 }}>
                  {Object.entries(summary.component_breakdown).map(([type, data]: [string, any]) => (
                    <div key={type} style={{ marginBottom: 8 }}>
                      <Tag color="blue">{type}</Tag>
                      <Text> 数量: {data.count}个, 体积: {data.volume}m³, 面积: {data.area}m²</Text>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        )}

        {/* 构件明细表 */}
        <Card type="inner" title="📋 构件明细">
          <Table
            columns={columns}
            dataSource={components}
            size="small"
            pagination={{ pageSize: 10, showSizeChanger: true }}
            scroll={{ x: 1000 }}
          />
        </Card>
      </Card>
    );
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* 页面标题和操作 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>
            📋 图纸详情
          </Title>
          <Text type="secondary">图纸ID: {drawing.id}</Text>
        </div>
        
        <Space>
          <Button 
            type="primary" 
            icon={<EyeOutlined />}
            onClick={handleOCR}
            loading={isOcrProcessing}
            disabled={drawing.status === 'processing'}
          >
            {isOcrProcessing ? 'OCR处理中...' : 'A→B→C智能OCR'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchDrawingDetail}>
            刷新
          </Button>
          <Button 
            danger 
            icon={<DeleteOutlined />}
            onClick={handleDeleteDrawing}
          >
            删除图纸
          </Button>
        </Space>
      </div>

      {/* 基本信息 */}
      <Card title="📄 基本信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="文件名">
            <Text code>{drawing.filename}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="文件类型">
            <Tag color="blue">{drawing.file_type?.toUpperCase() || 'UNKNOWN'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="处理状态">
            <Tag color={
              drawing.status === 'completed' ? 'green' :
              drawing.status === 'processing' ? 'orange' :
              drawing.status === 'error' ? 'red' : 'default'
            }>
              {drawing.status?.toUpperCase()}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="上传时间">
            {drawing.created_at ? new Date(drawing.created_at).toLocaleString('zh-CN') : '未知'}
          </Descriptions.Item>
          {drawing.file_size && (
            <Descriptions.Item label="文件大小">
              {(drawing.file_size / 1024 / 1024).toFixed(2)} MB
            </Descriptions.Item>
          )}
          {drawing.components_count && (
            <Descriptions.Item label="构件数量">
              {drawing.components_count} 个
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* OCR识别结果和工程量清单 */}
      {renderOCRResults()}
      {renderQuantityList()}

      {/* 处理中状态显示 */}
      {drawing.status === 'processing' && drawing.task_id && (
        <Card title="⚡ 实时处理进度" style={{ marginTop: 16 }}>
          <RealTimeProgress
            taskId={drawing.task_id}
            onComplete={(data) => {
              console.log('任务完成:', data);
              fetchDrawingDetail();
            }}
            onError={(error) => {
              console.error('任务失败:', error);
            }}
          />
        </Card>
      )}
    </div>
  );
} 