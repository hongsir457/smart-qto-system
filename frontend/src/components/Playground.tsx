import React, { useState, useEffect, useRef } from 'react';
import { Card, Input, Button, Select, Slider, message, Spin, Typography, Space, Tag, Tooltip, Switch } from 'antd';
import { SendOutlined, SettingOutlined, ClearOutlined, SaveOutlined, DownloadOutlined, ApiOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { playgroundApi } from '../services/api';
import styles from './Playground.module.css';

const { TextArea } = Input;
const { Option } = Select;
const { Title, Text } = Typography;

interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
  timestamp?: Date;
  isStreaming?: boolean;
}

interface PlaygroundSettings {
  model: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  stream: boolean;
}

interface Preset {
  name: string;
  description: string;
  system_message: string;
  temperature: number;
  max_tokens: number;
}

const Playground: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentInput, setCurrentInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [settings, setSettings] = useState<PlaygroundSettings>({
    model: 'gpt-4o',
    temperature: 0.7,
    max_tokens: 1000,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    stream: true,
  });
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [showSettings, setShowSettings] = useState(false);
  const [apiStatus, setApiStatus] = useState<{ valid: boolean; message: string }>({ valid: false, message: '' });
  const [streamingMessageIndex, setStreamingMessageIndex] = useState<number | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    loadModels();
    loadPresets();
    validateApiKey();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadModels = async () => {
    try {
      const response = await playgroundApi.getModels();
      setAvailableModels(response.models || []);
    } catch (error) {
      console.error('加载模型失败:', error);
      message.error('加载模型列表失败');
    }
  };

  const loadPresets = async () => {
    try {
      const response = await playgroundApi.getPresets();
      setPresets(response.presets || []);
    } catch (error) {
      console.error('加载预设失败:', error);
      message.error('加载预设模板失败');
    }
  };

  const validateApiKey = async () => {
    try {
      const response = await playgroundApi.validateApiKey();
      setApiStatus(response);
      if (!response.valid) {
        message.warning(response.message);
      }
    } catch (error) {
      console.error('API密钥验证失败:', error);
      setApiStatus({ valid: false, message: 'API密钥验证失败' });
    }
  };

  const applyPreset = (presetName: string) => {
    const preset = presets.find(p => p.name === presetName);
    if (preset) {
      setMessages([{ role: 'system', content: preset.system_message, timestamp: new Date() }]);
      setSettings(prev => ({
        ...prev,
        temperature: preset.temperature,
        max_tokens: preset.max_tokens,
      }));
      setSelectedPreset(presetName);
      message.success(`已应用预设: ${preset.name}`);
    }
  };

  const sendMessage = async () => {
    if (!currentInput.trim()) return;
    if (!apiStatus.valid) {
      message.error('API密钥无效，请检查配置');
      return;
    }

    const userMessage: Message = {
      role: 'user',
      content: currentInput.trim(),
      timestamp: new Date(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setCurrentInput('');

    if (settings.stream) {
      await sendStreamMessage(updatedMessages);
    } else {
      await sendNormalMessage(updatedMessages);
    }
  };

  const sendNormalMessage = async (updatedMessages: Message[]) => {
    setIsLoading(true);
    try {
      const response = await playgroundApi.chat({
        messages: updatedMessages.map(msg => ({ role: msg.role, content: msg.content })),
        model: settings.model,
        temperature: settings.temperature,
        max_tokens: settings.max_tokens,
        top_p: settings.top_p,
        frequency_penalty: settings.frequency_penalty,
        presence_penalty: settings.presence_penalty,
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.choices[0].message.content,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('发送消息失败:', error);
      message.error(error.response?.data?.detail || '发送消息失败');
    } finally {
      setIsLoading(false);
    }
  };

  const sendStreamMessage = async (updatedMessages: Message[]) => {
    setIsStreaming(true);
    
    // 创建一个新的助手消息用于流式显示
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    const messageIndex = updatedMessages.length; // 助手消息的索引
    setStreamingMessageIndex(messageIndex);

    // 创建 AbortController 用于取消请求
    abortControllerRef.current = new AbortController();

    try {
      const response = await playgroundApi.streamChat({
        messages: updatedMessages.map(msg => ({ role: msg.role, content: msg.content })),
        model: settings.model,
        temperature: settings.temperature,
        max_tokens: settings.max_tokens,
      }, abortControllerRef.current);

      if (!response.body) {
        throw new Error('流式响应不可用');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            
            if (data === '[DONE]') {
              // 流式响应结束
              setMessages(prev => prev.map((msg, idx) => 
                idx === messageIndex 
                  ? { ...msg, isStreaming: false }
                  : msg
              ));
              setStreamingMessageIndex(null);
              setIsStreaming(false);
              return;
            }
            
            try {
              const parsed = JSON.parse(data);
              
              if (parsed.error) {
                throw new Error(parsed.error.message);
              }
              
              if (parsed.choices && parsed.choices[0]?.delta?.content) {
                const deltaContent = parsed.choices[0].delta.content;
                accumulatedContent += deltaContent;
                
                // 实时更新消息内容
                setMessages(prev => prev.map((msg, idx) => 
                  idx === messageIndex 
                    ? { ...msg, content: accumulatedContent }
                    : msg
                ));
              }
            } catch (parseError) {
              // 忽略解析错误，继续处理下一行
              console.warn('解析流式数据失败:', parseError);
            }
          }
        }
      }
    } catch (error: any) {
      // 检查是否是用户主动取消
      if (error.name === 'AbortError') {
        console.log('用户取消了流式响应');
        return;
      }
      
      console.error('流式消息发送失败:', error);
      message.error(error.message || '流式消息发送失败');
      
      // 移除失败的消息
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsStreaming(false);
      setStreamingMessageIndex(null);
      abortControllerRef.current = null;
    }
  };

  const stopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setStreamingMessageIndex(null);
      
      // 标记当前流式消息为完成状态
      if (streamingMessageIndex !== null) {
        setMessages(prev => prev.map((msg, idx) => 
          idx === streamingMessageIndex 
            ? { ...msg, isStreaming: false }
            : msg
        ));
      }
      
      message.info('已停止生成');
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSelectedPreset('');
    message.success('对话已清空');
  };

  const exportChat = () => {
    const chatData = {
      timestamp: new Date().toISOString(),
      settings,
      messages: messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp?.toISOString(),
      })),
    };

    const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `playground-chat-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    message.success('对话已导出');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'system': return '#722ed1';
      case 'user': return '#1890ff';
      case 'assistant': return '#52c41a';
      default: return '#666';
    }
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'system': return '系统';
      case 'user': return '用户';
      case 'assistant': return 'AI助手';
      default: return role;
    }
  };

  const getMessageBubbleClass = (role: string) => {
    switch (role) {
      case 'user': return styles.messageBubbleUser;
      case 'assistant': return styles.messageBubbleAssistant;
      case 'system': return styles.messageBubbleSystem;
      default: return styles.messageBubble;
    }
  };

  return (
    <div className={styles.playgroundContainer}>
      <Card>
        <div style={{ marginBottom: '24px' }}>
          <Title level={2} style={{ marginBottom: '8px' }}>
            <ApiOutlined style={{ marginRight: '8px' }} />
            AI Playground
          </Title>
          <Space>
            <Tag color={apiStatus.valid ? 'green' : 'red'}>
              API状态: {apiStatus.valid ? '正常' : '异常'}
            </Tag>
            <Text type="secondary">{apiStatus.message}</Text>
            {isStreaming && (
              <Tag color="processing" icon={<ThunderboltOutlined />}>
                实时生成中...
              </Tag>
            )}
          </Space>
        </div>

        <div style={{ display: 'flex', gap: '24px', height: '70vh' }}>
          {/* 主聊天区域 */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* 工具栏 */}
            <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Select
                  style={{ width: 200 }}
                  placeholder="选择预设模板"
                  value={selectedPreset}
                  onChange={applyPreset}
                >
                  {presets.map(preset => (
                    <Option key={preset.name} value={preset.name}>
                      <Tooltip title={preset.description}>
                        {preset.name}
                      </Tooltip>
                    </Option>
                  ))}
                </Select>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ThunderboltOutlined style={{ color: settings.stream ? '#1890ff' : '#999' }} />
                  <Switch
                    checked={settings.stream}
                    onChange={(checked) => setSettings(prev => ({ ...prev, stream: checked }))}
                    size="small"
                  />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    实时流式
                  </Text>
                </div>
              </Space>
              <Space>
                <Button icon={<SettingOutlined />} onClick={() => setShowSettings(!showSettings)}>
                  {showSettings ? '隐藏' : '显示'}设置
                </Button>
                <Button icon={<ClearOutlined />} onClick={clearChat}>
                  清空对话
                </Button>
                <Button icon={<DownloadOutlined />} onClick={exportChat}>
                  导出对话
                </Button>
                {isStreaming && (
                  <Button danger onClick={stopStreaming}>
                    停止生成
                  </Button>
                )}
              </Space>
            </div>

            {/* 消息列表 */}
            <div className={styles.chatMessages}>
              {messages.length === 0 ? (
                <div style={{ textAlign: 'center', color: '#999', marginTop: '50px' }}>
                  <Text type="secondary">开始你的AI对话吧！选择一个预设模板或直接输入消息。</Text>
                </div>
              ) : (
                messages.map((message, index) => (
                  <div key={index} style={{ marginBottom: '16px' }}>
                    <div style={{ marginBottom: '4px' }}>
                      <Tag color={getRoleColor(message.role)} style={{ marginRight: '8px' }}>
                        {getRoleLabel(message.role)}
                      </Tag>
                      {message.timestamp && (
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {message.timestamp.toLocaleTimeString()}
                        </Text>
                      )}
                      {message.isStreaming && (
                        <Tag color="processing" style={{ marginLeft: '8px', fontSize: '12px' }}>
                          生成中...
                        </Tag>
                      )}
                    </div>
                    <div className={getMessageBubbleClass(message.role)}>
                      {message.content}
                      {message.isStreaming && (
                        <span className={styles.streamingCursor} />
                      )}
                    </div>
                  </div>
                ))
              )}
              {(isLoading && !settings.stream) && (
                <div style={{ textAlign: 'center', padding: '20px' }}>
                  <Spin size="large" />
                  <div style={{ marginTop: '8px' }}>
                    <Text type="secondary">AI正在思考中...</Text>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div style={{ marginTop: '16px' }}>
              <Space.Compact style={{ width: '100%' }}>
                <TextArea
                  value={currentInput}
                  onChange={(e) => setCurrentInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="输入你的消息... (按 Enter 发送，Shift+Enter 换行)"
                  autoSize={{ minRows: 2, maxRows: 6 }}
                  disabled={isLoading || isStreaming || !apiStatus.valid}
                />
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={sendMessage}
                  loading={isLoading && !settings.stream}
                  disabled={!currentInput.trim() || !apiStatus.valid || isStreaming}
                  style={{ height: 'auto' }}
                >
                  {isStreaming ? '生成中...' : '发送'}
                </Button>
              </Space.Compact>
            </div>
          </div>

          {/* 设置面板 */}
          {showSettings && (
            <Card style={{ width: '300px' }} title="模型设置" size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong>模型</Text>
                  <Select
                    style={{ width: '100%', marginTop: '4px' }}
                    value={settings.model}
                    onChange={(value) => setSettings(prev => ({ ...prev, model: value }))}
                  >
                    {availableModels.map(model => (
                      <Option key={model.id} value={model.id}>
                        {model.id}
                      </Option>
                    ))}
                  </Select>
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <Text strong>流式响应</Text>
                    <Switch
                      checked={settings.stream}
                      onChange={(checked) => setSettings(prev => ({ ...prev, stream: checked }))}
                    />
                  </div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    启用后将实时显示AI的回答过程
                  </Text>
                </div>

                <div>
                  <Text strong>温度 (Temperature): {settings.temperature}</Text>
                  <Slider
                    min={0}
                    max={2}
                    step={0.1}
                    value={settings.temperature}
                    onChange={(value) => setSettings(prev => ({ ...prev, temperature: value }))}
                    tooltip={{ formatter: (value) => `${value}` }}
                  />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    控制回答的随机性和创造性
                  </Text>
                </div>

                <div>
                  <Text strong>最大长度: {settings.max_tokens}</Text>
                  <Slider
                    min={100}
                    max={4000}
                    step={100}
                    value={settings.max_tokens}
                    onChange={(value) => setSettings(prev => ({ ...prev, max_tokens: value }))}
                  />
                </div>

                <div>
                  <Text strong>Top P: {settings.top_p}</Text>
                  <Slider
                    min={0}
                    max={1}
                    step={0.1}
                    value={settings.top_p}
                    onChange={(value) => setSettings(prev => ({ ...prev, top_p: value }))}
                  />
                </div>

                <div>
                  <Text strong>频率惩罚: {settings.frequency_penalty}</Text>
                  <Slider
                    min={-2}
                    max={2}
                    step={0.1}
                    value={settings.frequency_penalty}
                    onChange={(value) => setSettings(prev => ({ ...prev, frequency_penalty: value }))}
                  />
                </div>

                <div>
                  <Text strong>存在惩罚: {settings.presence_penalty}</Text>
                  <Slider
                    min={-2}
                    max={2}
                    step={0.1}
                    value={settings.presence_penalty}
                    onChange={(value) => setSettings(prev => ({ ...prev, presence_penalty: value }))}
                  />
                </div>
              </Space>
            </Card>
          )}
        </div>
      </Card>
    </div>
  );
};

export default Playground; 