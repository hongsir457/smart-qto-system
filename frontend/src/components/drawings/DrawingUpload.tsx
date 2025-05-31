import { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import RealTimeProgress from '../RealTimeProgress';

export default function DrawingUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [currentTaskId, setCurrentTaskId] = useState<string>('');
  const [showProgress, setShowProgress] = useState(false);
  const [uploadedDrawing, setUploadedDrawing] = useState<any>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/dwg': ['.dwg'],
      'application/dxf': ['.dxf']
    },
    onDrop: acceptedFiles => {
      setFiles(acceptedFiles);
      setMessage('');
    }
  });

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setMessage('');

    try {
      const formData = new FormData();
      formData.append('file', files[0]);

      const token = localStorage.getItem('token');
      const authHeader = token?.startsWith('Bearer ') ? token : `Bearer ${token}`;
      console.log('上传时用的 token:', token);
      console.log('上传时用的 Authorization 头:', authHeader);
      
      const response = await axios.post(
        'http://localhost:8000/api/v1/drawings/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': authHeader
          },
        }
      );

      setMessage('文件上传成功！');
      setUploadedDrawing(response.data);
      setFiles([]);
      
      // 如果后端返回了任务ID，显示实时进度
      if (response.data.task_id) {
        setCurrentTaskId(response.data.task_id);
        setShowProgress(true);
      } else if (response.data.status === 'processing') {
        // 如果状态是处理中，但没有任务ID，可以尝试轮询状态
        setMessage('文件上传成功，正在后台处理...');
      }
      
    } catch (error: any) {
      let detail = error.response?.data?.detail || error.message || '上传失败，请重试';
      setMessage('上传失败: ' + detail);
      console.error('Upload error:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleProgressComplete = (data: any) => {
    console.log('处理完成:', data);
    setShowProgress(false);
    setCurrentTaskId('');
    setMessage('图纸处理完成！');
    
    // 更新上传的图纸信息
    if (uploadedDrawing) {
      setUploadedDrawing({
        ...uploadedDrawing,
        status: 'completed'
      });
    }
  };

  const handleProgressError = (data: any) => {
    console.error('处理失败:', data);
    setShowProgress(false);
    setCurrentTaskId('');
    setMessage('图纸处理失败: ' + (data.message || '未知错误'));
    
    // 更新上传的图纸信息
    if (uploadedDrawing) {
      setUploadedDrawing({
        ...uploadedDrawing,
        status: 'error'
      });
    }
  };

  return (
    <div className="max-w-xl mx-auto p-6">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-gray-400'}`}
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <p className="text-primary-600">将文件拖放到这里...</p>
        ) : (
          <div>
            <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
              <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="mt-2 text-gray-600">
              拖放PDF或CAD文件到这里，或点击选择文件
            </p>
            <p className="mt-1 text-sm text-gray-500">
              支持 PDF、DWG、DXF 格式
            </p>
          </div>
        )}
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          <p className="font-medium text-gray-700">已选择文件：</p>
          <div className="mt-2 bg-gray-50 rounded-md p-3">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-gray-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
              </svg>
              <span className="text-sm text-gray-700">{files[0].name}</span>
              <span className="ml-auto text-xs text-gray-500">
                {(files[0].size / 1024 / 1024).toFixed(2)} MB
              </span>
            </div>
          </div>
          
          <button
            onClick={handleUpload}
            disabled={uploading}
            className={`mt-4 w-full py-2 px-4 rounded-md text-white font-medium transition-colors
              ${uploading ? 'bg-primary-400 cursor-not-allowed' : 'bg-primary-600 hover:bg-primary-700'}`}
          >
            {uploading ? (
              <div className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                上传中...
              </div>
            ) : (
              '上传文件'
            )}
          </button>
        </div>
      )}

      {/* 上传成功后的图纸信息 */}
      {uploadedDrawing && (
        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-md p-4">
          <h4 className="text-sm font-medium text-blue-800 mb-2">上传成功</h4>
          <div className="text-sm text-blue-700">
            <p>文件名: {uploadedDrawing.filename}</p>
            <p>图纸ID: {uploadedDrawing.id}</p>
            <p>状态: <span className={`font-medium ${
              uploadedDrawing.status === 'completed' ? 'text-green-600' :
              uploadedDrawing.status === 'processing' ? 'text-yellow-600' :
              uploadedDrawing.status === 'error' ? 'text-red-600' :
              'text-gray-600'
            }`}>{uploadedDrawing.status}</span></p>
          </div>
        </div>
      )}

      {/* 实时进度显示 */}
      {showProgress && currentTaskId && (
        <div className="mt-4 bg-white border border-gray-200 rounded-md p-4">
          <h4 className="text-sm font-medium text-gray-800 mb-3">处理进度</h4>
          <RealTimeProgress
            taskId={currentTaskId}
            onComplete={handleProgressComplete}
            onError={handleProgressError}
          />
        </div>
      )}

      {/* 消息显示 */}
      {message && (
        <div className={`mt-4 p-4 rounded-md ${
          message.includes('失败') ? 'bg-red-50 text-red-700 border border-red-200' : 
          message.includes('成功') ? 'bg-green-50 text-green-700 border border-green-200' :
          'bg-blue-50 text-blue-700 border border-blue-200'
        }`}>
          <div className="flex">
            <div className="flex-shrink-0">
              {message.includes('失败') ? (
                <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <div className="ml-3">
              <p className="text-sm">{message}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 