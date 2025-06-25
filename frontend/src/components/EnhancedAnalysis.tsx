import React, { useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  TrendingUp,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Assessment,
} from '@mui/icons-material';

interface AnalysisParams {
  projectType: string;
  drawingType: string;
  confidenceThreshold: number;
}

interface AnalysisResult {
  id: string;
  component_name: string;
  component_type: string;
  quantity: number;
  unit: string;
  confidence: number;
  ai_remark: string;
}

interface QualityReport {
  overall_score: number;
  high_confidence_count: number;
  medium_confidence_count: number;
  low_confidence_count: number;
  total_components: number;
}

const EnhancedAnalysis: React.FC = () => {
  const [params, setParams] = useState<AnalysisParams>({
    projectType: '',
    drawingType: '',
    confidenceThreshold: 0.8,
  });

  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [optimizationDialogOpen, setOptimizationDialogOpen] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');

  const handleParamChange = (field: keyof AnalysisParams, value: any) => {
    setParams(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const startAnalysis = async () => {
    setAnalysisRunning(true);
    setProgress(0);
    setError(null);

    try {
      // 模拟API调用
      const response = await fetch('/api/v1/enhanced-analysis/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        throw new Error('分析失败');
      }

      const data = await response.json();
      setResults(data.results || []);
      setQualityReport(data.quality_report || null);
      setProgress(100);
    } catch (err) {
      setError('分析失败，请重试');
    } finally {
      setAnalysisRunning(false);
    }
  };

  const getConfidenceColor = (confidence: number): "success" | "warning" | "error" => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircle color="success" />;
    if (confidence >= 0.6) return <Warning color="warning" />;
    return <ErrorIcon color="error" />;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        增强版AI分析
      </Typography>

      {/* 参数配置区域 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            分析参数配置
          </Typography>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>项目类型</InputLabel>
                <Select
                  value={params.projectType}
                  label="项目类型"
                  onChange={(e) => handleParamChange('projectType', e.target.value)}
                >
                  <MenuItem value="residential">住宅建筑</MenuItem>
                  <MenuItem value="commercial">商业建筑</MenuItem>
                  <MenuItem value="industrial">工业建筑</MenuItem>
                  <MenuItem value="infrastructure">基础设施</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>图纸类型</InputLabel>
                <Select
                  value={params.drawingType}
                  label="图纸类型"
                  onChange={(e) => handleParamChange('drawingType', e.target.value)}
                >
                  <MenuItem value="plan">平面图</MenuItem>
                  <MenuItem value="elevation">立面图</MenuItem>
                  <MenuItem value="section">剖面图</MenuItem>
                  <MenuItem value="detail">详图</MenuItem>
                  <MenuItem value="structural">结构图</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid size={12}>
              <Typography gutterBottom>
                置信度阈值: {params.confidenceThreshold}
              </Typography>
              <Slider
                value={params.confidenceThreshold}
                onChange={(_, value) => handleParamChange('confidenceThreshold', value)}
                min={0.1}
                max={1.0}
                step={0.05}
                marks={[
                  { value: 0.1, label: '0.1' },
                  { value: 0.5, label: '0.5' },
                  { value: 1.0, label: '1.0' },
                ]}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              startIcon={analysisRunning ? <Stop /> : <PlayArrow />}
              onClick={startAnalysis}
              disabled={analysisRunning || !params.projectType || !params.drawingType}
            >
              {analysisRunning ? '停止分析' : '开始增强分析'}
            </Button>

            {results.length > 0 && (
              <Button
                variant="outlined"
                startIcon={<TrendingUp />}
                onClick={() => setOptimizationDialogOpen(true)}
              >
                迭代优化
              </Button>
            )}
          </Box>

          {analysisRunning && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress variant="determinate" value={progress} />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                分析进度: {progress}%
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* 结果展示区域 */}
      {results.length > 0 && (
        <Card>
          <CardContent>
            <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
              <Tab label="分析结果" />
              <Tab label="质量报告" />
            </Tabs>

            {/* 分析结果标签页 */}
            {activeTab === 0 && (
              <Box sx={{ mt: 3 }}>
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>构件名称</TableCell>
                        <TableCell>类型</TableCell>
                        <TableCell>数量</TableCell>
                        <TableCell>单位</TableCell>
                        <TableCell>置信度</TableCell>
                        <TableCell>AI分析说明</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {results.map((result) => (
                        <TableRow key={result.id}>
                          <TableCell>{result.component_name}</TableCell>
                          <TableCell>{result.component_type}</TableCell>
                          <TableCell>{result.quantity}</TableCell>
                          <TableCell>{result.unit}</TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {getConfidenceIcon(result.confidence)}
                              <Chip
                                label={`${(result.confidence * 100).toFixed(1)}%`}
                                color={getConfidenceColor(result.confidence)}
                                size="small"
                              />
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {result.ai_remark}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {/* 质量报告标签页 */}
            {activeTab === 1 && qualityReport && (
              <Box sx={{ mt: 3 }}>
                <Grid container spacing={3}>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          <Assessment sx={{ mr: 1 }} />
                          整体质量评分
                        </Typography>
                        <Typography variant="h3" color="primary">
                          {qualityReport.overall_score.toFixed(1)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          /100
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid size={{ xs: 12, md: 6 }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          置信度分布
                        </Typography>
                        <List>
                          <ListItem>
                            <ListItemIcon>
                              <CheckCircle color="success" />
                            </ListItemIcon>
                            <ListItemText 
                              primary={`高置信度: ${qualityReport.high_confidence_count} 个`}
                            />
                          </ListItem>
                          <ListItem>
                            <ListItemIcon>
                              <Warning color="warning" />
                            </ListItemIcon>
                            <ListItemText 
                              primary={`中等置信度: ${qualityReport.medium_confidence_count} 个`}
                            />
                          </ListItem>
                          <ListItem>
                            <ListItemIcon>
                              <ErrorIcon color="error" />
                            </ListItemIcon>
                            <ListItemText 
                              primary={`低置信度: ${qualityReport.low_confidence_count} 个`}
                            />
                          </ListItem>
                        </List>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* 迭代优化对话框 */}
      <Dialog 
        open={optimizationDialogOpen} 
        onClose={() => setOptimizationDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>迭代优化反馈</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={6}
            label="请详细描述需要改进的问题"
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="例如：第3行的梁构件识别错误，应该是钢筋混凝土梁而不是钢梁..."
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOptimizationDialogOpen(false)}>
            取消
          </Button>
          <Button 
            variant="contained"
            disabled={!feedbackText.trim()}
          >
            开始优化
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EnhancedAnalysis; 