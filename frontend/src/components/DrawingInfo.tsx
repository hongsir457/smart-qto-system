import React from 'react';
import { InfoCircleOutlined } from '@ant-design/icons';
import { Drawing } from '../types';

interface DrawingInfoProps {
    drawing: Drawing | null;
}

const DrawingInfo: React.FC<DrawingInfoProps> = ({ drawing }) => {
    return (
        <div className="nvidia-info-block">
            <div className="nvidia-block-header">
                <InfoCircleOutlined className="nvidia-block-icon" />
                <h2 className="nvidia-block-title">图纸信息</h2>
            </div>
            <div className="nvidia-drawing-info">
                <div className="drawing-info-item">
                    <span className="drawing-info-label">文件名</span>
                    <span className="drawing-info-value">{drawing?.filename || '暂无'}</span>
                </div>
                <div className="drawing-info-item">
                    <span className="drawing-info-label">文件类型</span>
                    <span className="drawing-info-value">{drawing?.file_type || 'pdf'}</span>
                </div>
                <div className="drawing-info-item">
                    <span className="drawing-info-label">上传时间</span>
                    <span className="drawing-info-value">
                        {drawing?.created_at ? new Date(drawing.created_at).toLocaleString() : '暂无'}
                    </span>
                </div>
                <div className="drawing-info-item">
                    <span className="drawing-info-label">处理状态</span>
                    <span className="drawing-info-value">{drawing?.status || '暂无'}</span>
                </div>
                <div className="drawing-info-item">
                    <span className="drawing-info-label">标注</span>
                    <span className="drawing-info-value">{drawing?.label || '暂无'}</span>
                </div>
                <div className="drawing-info-item">
                    <span className="drawing-info-label">文件大小</span>
                    <span className="drawing-info-value">
                        {drawing?.file_size ? `${(drawing.file_size / 1024 / 1024).toFixed(2)} MB` : '暂无'}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default DrawingInfo; 