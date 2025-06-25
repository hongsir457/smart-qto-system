import React, { useState, useEffect } from 'react';
import { Upload, Button, message, Card, List, Tag, Table, Select, Pagination, Form, Input, DatePicker, Tabs, Row, Col } from 'antd';
import { InboxOutlined, FileOutlined, CloudUploadOutlined, FileTextOutlined, BarChartOutlined } from '@ant-design/icons';
import { useRouter } from 'next/router';
import { uploadDrawing, getDrawings, updateDrawingLabel } from '../services/api';
import { Drawing } from '../types';
import { UploadFile, RcFile } from 'antd/es/upload/interface';
import RealTimeTaskMessages from '../components/RealTimeTaskMessages';
import './DrawingUpload.css';

const { Dragger } = Upload;
const { Option } = Select;

const PAGE_SIZE = 10;

const ProjectUploadPage: React.FC = () => {
    const [drawings, setDrawings] = useState<Drawing[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [fileList, setFileList] = useState<UploadFile<any>[]>([]);
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const router = useRouter();

    // 项目信息表单
    const [form] = Form.useForm();

    const fetchDrawings = async (pageNum = 1, pageSize = PAGE_SIZE) => {
        try {
            // 检查是否有有效token
            const token = localStorage.getItem('token');
            if (!token) {
                console.log('未登录，跳过获取图纸列表');
                return;
            }
            
            const res = await getDrawings(pageNum, pageSize);
            setDrawings(res.items || []);
            setTotal(res.total || 0);
        } catch (error: any) {
            // 如果是认证错误，不显示错误消息，让认证系统处理
            if (error?.message?.includes('401') || error?.message?.includes('认证')) {
                console.log('认证失败，跳过显示错误');
                return;
            }
            message.error('获取图纸列表失败');
        }
    };

    useEffect(() => {
        // 延迟执行，确保认证检查完成
        const timer = setTimeout(() => {
            fetchDrawings(page, PAGE_SIZE);
        }, 1000);
        
        return () => clearTimeout(timer);
    }, [page]);

    // 批量上传
    const handleBatchUpload = async () => {
        setLoading(true);
        try {
            for (const file of fileList) {
                if (file.originFileObj) {
                    await uploadDrawing(file.originFileObj as File);
                }
            }
            message.success('批量上传成功');
            setFileList([]);
            fetchDrawings(page, PAGE_SIZE);
        } catch (error) {
            message.error('上传失败');
        } finally {
            setLoading(false);
        }
    };

    // 单文件上传兼容
    const handleUpload = async (file: File) => {
        setLoading(true);
        try {
            await uploadDrawing(file);
            message.success('上传成功');
            setSelectedFile(null);
            fetchDrawings(page, PAGE_SIZE);
        } catch (error) {
            message.error('上传失败');
        } finally {
            setLoading(false);
        }
    };

    // 标注修改
    const handleLabelChange = async (id: number, label: string) => {
        try {
            await updateDrawingLabel(id, label);
            message.success('标注已更新');
            fetchDrawings(page, PAGE_SIZE);
        } catch (error) {
            message.error('标注更新失败');
        }
    };

    // 任务完成回调
    const handleTaskComplete = (taskId: string) => {
        message.success('图纸处理完成');
        fetchDrawings(page, PAGE_SIZE); // 刷新列表
    };

    // 任务错误回调
    const handleTaskError = (taskId: string, error: string) => {
        message.error(`任务失败: ${error}`);
        fetchDrawings(page, PAGE_SIZE); // 刷新列表
    };

    // Table columns - NVIDIA风格
    const columns = [
        {
            title: '文件名',
            dataIndex: 'filename',
            key: 'filename',
            render: (text: string) => (
                <span className="nvidia-filename">
                    <FileTextOutlined style={{ marginRight: 8, color: '#76b900' }} />
                    {text}
                </span>
            ),
        },
        {
            title: '类型',
            dataIndex: 'file_type',
            key: 'file_type',
            render: (type: string) => (
                <Tag className="nvidia-tag" color="#76b900">{type}</Tag>
            ),
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => {
                const statusConfig = {
                    'completed': { color: '#76b900', text: '已完成' },
                    'processing': { color: '#00d4aa', text: '处理中' },
                    'failed': { color: '#ff6c37', text: '失败' },
                    'pending': { color: '#ffc107', text: '等待中' }
                };
                const config = statusConfig[status as keyof typeof statusConfig] || { color: '#999', text: status };
                return <Tag color={config.color}>{config.text}</Tag>;
            },
        },
        {
            title: '上传时间',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (text: string) => (
                <span className="nvidia-timestamp">
                    {new Date(text).toLocaleString()}
                </span>
            ),
        },
        {
            title: '标注',
            dataIndex: 'label',
            key: 'label',
            render: (label: string, record: Drawing) => (
                <Select
                    value={label}
                    style={{ width: 100 }}
                    className="nvidia-select"
                    onChange={val => handleLabelChange(record.id, val)}
                >
                    <Option value="结构图">结构图</Option>
                    <Option value="施工图">施工图</Option>
                    <Option value="其他">其他</Option>
                </Select>
            ),
        },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: Drawing) => (
                <Button 
                    type="link" 
                    className="nvidia-action-btn"
                    onClick={() => router.push(`/drawings/${record.id}`)}
                >
                    查看详情
                </Button>
            ),
        },
    ];

    // 上传配置
    const uploadProps = {
        multiple: true,
        accept: '.pdf,.dwg,.dxf',
        beforeUpload: (file: RcFile) => {
            setFileList(prev => [
                ...prev,
                {
                    uid: file.uid,
                    name: file.name,
                    status: 'done',
                    originFileObj: file,
                },
            ]);
            return false;
        },
        fileList,
        onRemove: (file: UploadFile<any>) => {
            setFileList(prev => prev.filter(f => f.uid !== file.uid));
        },
        showUploadList: true,
    };

    return (
        <div className="nvidia-container">
            {/* 顶部标题栏 */}
            <div className="nvidia-header">
                <div className="nvidia-header-content">
                    <h1 className="nvidia-title">
                        <span className="nvidia-brand">SMART QTO</span>
                        <span className="nvidia-subtitle">智能工程量计算系统</span>
                    </h1>
                    <div className="nvidia-header-stats">
                        <div className="nvidia-stat">
                            <span className="nvidia-stat-value">{drawings.length}</span>
                            <span className="nvidia-stat-label">图纸总数</span>
                        </div>
                        <div className="nvidia-stat">
                            <span className="nvidia-stat-value">{drawings.filter(d => d.status === 'completed').length}</span>
                            <span className="nvidia-stat-label">已完成</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 项目信息卡片 */}
            <div className="nvidia-project-card">
                <Form form={form} layout="inline" className="nvidia-form">
                    <Form.Item label="工程名称" name="projectName">
                        <Input placeholder="未命名工程" className="nvidia-input" />
                    </Form.Item>
                    <Form.Item label="工程编号" name="projectCode">
                        <Input placeholder="未知编号" className="nvidia-input" />
                    </Form.Item>
                    <Form.Item label="建设单位" name="company">
                        <Input placeholder="未知建设单位" className="nvidia-input" />
                    </Form.Item>
                    <Form.Item label="统计日期" name="date">
                        <DatePicker className="nvidia-input" />
                    </Form.Item>
                </Form>
            </div>

            {/* 主要内容区域 - 左右布局 */}
            <div className="nvidia-main-content">
                {/* 左侧面板 */}
                <div className="nvidia-left-panel">
                    {/* 文件上传区域 */}
                    <div className="nvidia-upload-section">
                        <div className="nvidia-section-header">
                            <CloudUploadOutlined className="nvidia-section-icon" />
                            <h2>文件上传</h2>
                        </div>
                        <div className="nvidia-upload-area">
                            <Dragger {...uploadProps} className="nvidia-dragger">
                                <p className="nvidia-upload-icon">
                                    <InboxOutlined />
                                </p>
                                <p className="nvidia-upload-text">拖拽或点击上传文件</p>
                                <p className="nvidia-upload-hint">
                                    支持 PDF/DWG/DXF 格式，多文件上传，最大 50MB
                                </p>
                            </Dragger>
                            <div className="nvidia-upload-actions">
                                <Button 
                                    type="primary" 
                                    className="nvidia-btn nvidia-btn-primary"
                                    onClick={handleBatchUpload} 
                                    loading={loading} 
                                    disabled={fileList.length === 0}
                                    icon={<CloudUploadOutlined />}
                                >
                                    批量上传
                                </Button>
                                <Button 
                                    className="nvidia-btn nvidia-btn-secondary"
                                    onClick={async () => {
                                        if (fileList.length > 0 && fileList[0].originFileObj) {
                                            await handleUpload(fileList[0].originFileObj as File);
                                            setFileList([]);
                                        }
                                    }}
                                    loading={loading}
                                    disabled={fileList.length === 0}
                                    icon={<FileOutlined />}
                                >
                                    单文件上传
                                </Button>
                                <Button 
                                    className="nvidia-btn nvidia-btn-success"
                                    onClick={() => message.info('导出清单功能开发中...')}
                                    icon={<BarChartOutlined />}
                                >
                                    导出清单
                                </Button>
                            </div>
                        </div>
                    </div>

                    {/* 图纸表格视图 */}
                    <div className="nvidia-table-section">
                        <div className="nvidia-section-header">
                            <FileTextOutlined className="nvidia-section-icon" />
                            <h2>图纸清单</h2>
                        </div>
                        <div className="nvidia-table-container">
                            <Table 
                                columns={columns} 
                                dataSource={drawings} 
                                rowKey="id" 
                                pagination={false}
                                loading={loading}
                                size="middle"
                                className="nvidia-table"
                                showHeader={true}
                            />
                            <div className="nvidia-pagination">
                                <Pagination
                                    current={page}
                                    pageSize={PAGE_SIZE}
                                    total={total}
                                    onChange={p => setPage(p)}
                                    showTotal={(total, range) => 
                                        `${range[0]}-${range[1]} 共 ${total} 条`
                                    }
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* 右侧面板 - 实时任务消息 */}
                <div className="nvidia-right-panel">
                    <RealTimeTaskMessages 
                        maxMessages={8}
                        onTaskComplete={handleTaskComplete}
                        onTaskError={handleTaskError}
                    />
                </div>
            </div>
        </div>
    );
};

export default ProjectUploadPage; 