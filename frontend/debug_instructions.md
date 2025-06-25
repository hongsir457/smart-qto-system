# 前端数据问题调试指南

## 问题描述
- URL: `localhost:3000/drawings/3`
- 后端API正确返回ID=3的数据（加固柱）
- 前端页面却显示ID=2的数据（主梁、次梁）

## 调试步骤

### 1. 检查浏览器开发者工具

打开浏览器开发者工具（F12），执行以下检查：

#### Console 日志检查
查找以下日志：
```
🔍 [processOcrData] 开始处理OCR数据
🔍 [processOcrData] extractRealOcrData结果
✅ [handleRecognitionResults] 发现简单测试数据结构，直接处理
```

#### Network 请求检查
1. 刷新页面
2. 查看是否有对 `/api/v1/drawings/3` 的请求
3. 检查响应数据是否正确

#### Application 存储检查
1. 打开 Application 标签页
2. 检查 Local Storage 中是否有缓存的错误数据
3. 清理 localStorage: `localStorage.clear()`

### 2. 浏览器控制台调试命令

在Console中执行以下命令：

```javascript
// 检查当前页面的图纸ID
console.log('当前URL:', window.location.href);
console.log('图纸ID:', window.location.pathname.split('/').pop());

// 检查localStorage中的缓存
console.log('localStorage内容:', localStorage.getItem('token'));

// 清理缓存并刷新
localStorage.clear();
location.reload();
```

### 3. 临时解决方案

如果问题持续存在，请：

1. **硬刷新页面**: Ctrl+F5 或 Ctrl+Shift+R
2. **清理浏览器缓存**: 设置 > 清除浏览数据
3. **尝试无痕模式**: 新开无痕窗口访问

### 4. 检查数据流

API数据流应该是：
```
URL: /drawings/3 
→ useDrawingDetail.fetchDrawingDetail() 
→ fetch('/api/v1/drawings/3')
→ processOcrData() 
→ extractRealOcrData() 
→ handleRecognitionResults() 
→ createSimpleOcrResult()
→ setReadableOcrResults()
```

如果在某个环节出现问题，会有相应的console日志。 