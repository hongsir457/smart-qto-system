import React, { useState, useEffect } from 'react';
import { Upload, Button, message, Card, List, Tag, Table, Select, Pagination, Form, Input, DatePicker, Tabs } from 'antd';
import { InboxOutlined, FileOutlined } from '@ant-design/icons';
import { useRouter } from 'next/router';
import { uploadDrawing, getDrawings, updateDrawingLabel } from '../services/api';
import { Drawing } from '../types';
import { UploadFile, RcFile } from 'antd/es/upload/interface';

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
            const res = await getDrawings(pageNum, pageSize);
            setDrawings(res.items || res);
            setTotal(res.total || (res.length || 0));
        } catch (error) {
            message.error('获取图纸列表失败');
        }
    };

    useEffect(() => {
        fetchDrawings(page, PAGE_SIZE);
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

    // Table columns
    const columns = [
        {
            title: '文件名',
            dataIndex: 'filename',
            key: 'filename',
        },
        {
            title: '类型',
            dataIndex: 'file_type',
            key: 'file_type',
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
        },
        {
            title: '上传时间',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (text: string) => new Date(text).toLocaleString(),
        },
        {
            title: '标注',
            dataIndex: 'label',
            key: 'label',
            render: (label: string, record: Drawing) => (
                <Select
                    value={label}
                    style={{ width: 100 }}
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
                <Button type="link" onClick={() => router.push(`/drawings/${record.id}`)}>
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
        <div style={{ padding: 24 }}>
            {/* 项目信息 */}
            <Card style={{ marginBottom: 16 }}>
                <Form form={form} layout="inline">
                    <Form.Item label="工程名称" name="projectName"><Input placeholder="未命名工程" /></Form.Item>
                    <Form.Item label="工程编号" name="projectCode"><Input placeholder="未知编号" /></Form.Item>
                    <Form.Item label="建设单位" name="company"><Input placeholder="未知建设单位" /></Form.Item>
                    <Form.Item label="统计日期" name="date"><DatePicker /></Form.Item>
                    {/* 其它项目信息... */}
                </Form>
            </Card>

            {/* 上传区 */}
            <Card style={{ marginBottom: 16 }}>
                <Dragger {...uploadProps}>
                    <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                    <p className="ant-upload-text">拖拽或点击上传文件</p>
                    <p className="ant-upload-hint">仅支持DXF/DWG格式，支持多文件，最大50MB</p>
                </Dragger>
                <div style={{ marginTop: 16, textAlign: 'right' }}>
                    <Button type="primary" style={{ marginRight: 8 }} onClick={handleBatchUpload} loading={loading} disabled={fileList.length === 0}>批量上传</Button>
                    <Button type="primary" style={{ marginRight: 8 }}
                        onClick={async () => {
                            if (fileList.length > 0 && fileList[0].originFileObj) {
                                await handleUpload(fileList[0].originFileObj as File);
                                setFileList([]);
                            }
                        }}
                        loading={loading}
                        disabled={fileList.length === 0}
                    >上传</Button>
                    <Button type="primary" style={{ background: '#21ba45', borderColor: '#21ba45', marginRight: 8 }}>导出清单</Button>
                    <Button>导出计算书</Button>
                </div>
            </Card>

            {/* 图纸解析结果 */}
            <Card>
                <Tabs 
                    defaultActiveKey="2"
                    items={[
                        {
                            key: '2',
                            label: '表格视图',
                            children: (
                                <>
                                    <Table columns={columns} dataSource={drawings} rowKey="id" pagination={false} />
                                    <Pagination
                                        style={{ marginTop: 16, textAlign: 'right' }}
                                        current={page}
                                        pageSize={PAGE_SIZE}
                                        total={total}
                                        onChange={p => setPage(p)}
                                    />
                                </>
                            )
                        }
                    ]}
                />
            </Card>
        </div>
    );
};

export default ProjectUploadPage; 