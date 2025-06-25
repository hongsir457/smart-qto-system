import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Button,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Description,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Refresh,
} from '@mui/icons-material';

interface Drawing {
  id: number;
  filename: string;
  status: string;
  created_at: string;
  recognition_results?: any;
}

const DrawingList: React.FC = () => {
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDrawings = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/drawings/');
      
      if (response.ok) {
        const data = await response.json();
        setDrawings(data.drawings || []);
        setError(null);
      } else {
        throw new Error('获取图纸列表失败');
      }
    } catch (err) {
      console.error('获取图纸列表失败:', err);
      setError('获取图纸列表失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrawings();
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'processing':
        return <CircularProgress size={24} />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <Warning color="warning" />;
    }
  };

  const getStatusColor = (status: string): "success" | "warning" | "error" | "default" => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'processing':
        return '处理中';
      case 'failed':
        return '失败';
      default:
        return '未知';
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          图纸列表
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={fetchDrawings}
        >
          刷新
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Card>
        <CardContent>
          {drawings.length === 0 ? (
            <Typography variant="body1" color="text.secondary">
              暂无图纸数据
            </Typography>
          ) : (
            <List>
              {drawings.map((drawing) => (
                <ListItem key={drawing.id} divider>
                  <ListItemIcon>
                    {getStatusIcon(drawing.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Description />
                        <Typography variant="subtitle1">
                          {drawing.filename}
                        </Typography>
                        <Chip
                          label={getStatusText(drawing.status)}
                          color={getStatusColor(drawing.status)}
                          size="small"
                        />
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                          ID: {drawing.id} | 创建时间: {new Date(drawing.created_at).toLocaleString()}
                        </Typography>
                        {drawing.recognition_results && (
                          <Typography variant="body2" color="text.secondary">
                            识别构件: {drawing.recognition_results.quantity_list?.length || 0} 个
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default DrawingList; 