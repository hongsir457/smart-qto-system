import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Alert,
} from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { styled } from '@mui/material/styles';

const VisuallyHiddenInput = styled('input')({
  clip: 'rect(0 0 0 0)',
  clipPath: 'inset(50%)',
  height: 1,
  overflow: 'hidden',
  position: 'absolute',
  bottom: 0,
  left: 0,
  whiteSpace: 'nowrap',
  width: 1,
});

const DrawingUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/v1/drawings/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setUploadResult(`上传成功！图纸ID: ${data.drawing_id}`);
      } else {
        throw new Error('上传失败');
      }
    } catch (error) {
      console.error('上传失败:', error);
      setUploadResult('上传失败，请重试');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        图纸上传
      </Typography>

      <Card>
        <CardContent>
          <Box sx={{ mb: 3 }}>
            <Button
              component="label"
              variant="outlined"
              startIcon={<CloudUpload />}
              fullWidth
              sx={{ mb: 2, p: 3, height: '100px' }}
            >
              {file ? file.name : '选择图纸文件'}
              <VisuallyHiddenInput
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileChange}
              />
            </Button>
          </Box>

          {file && (
            <Button
              variant="contained"
              onClick={handleUpload}
              disabled={uploading}
              fullWidth
            >
              {uploading ? '上传中...' : '开始上传'}
            </Button>
          )}

          {uploading && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress />
            </Box>
          )}

          {uploadResult && (
            <Alert 
              severity={uploadResult.includes('成功') ? 'success' : 'error'} 
              sx={{ mt: 2 }}
            >
              {uploadResult}
            </Alert>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default DrawingUpload; 