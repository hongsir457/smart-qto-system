# DWG文件支持说明

## 概述

我们的智能工程量计算系统现在支持DWG文件的多图框处理，包括：
- 自动检测多个图框
- 按图号排序识别
- 构件识别和工程量计算
- 多种DWG文件格式兼容

## DWG文件处理方法

系统采用多层级的DWG文件处理策略，确保最大的兼容性：

### 方法1: ODA File Converter (推荐)

**优点：**
- 支持所有AutoCAD版本的DWG文件
- 转换质量最高
- 官方支持的转换工具

**安装指导：**
1. 访问官方网站：https://www.opendesign.com/guestfiles/oda_file_converter
2. 下载适合你操作系统的版本（Windows/Linux/macOS）
3. 安装到默认位置（Windows: `C:\Program Files\ODA\ODAFileConverter\`）
4. 确保命令行可以访问 `ODAFileConverter.exe`

**Windows安装步骤：**
```bash
# 下载并安装ODA File Converter
# 安装后验证
ODAFileConverter.exe --help
```

### 方法2: ezdxf DWG加载器 (实验性)

**适用情况：**
- 较新版本的DWG文件
- 不需要ODA File Converter的情况

**限制：**
- 支持的DWG版本有限
- 可能无法处理复杂的DWG文件

### 方法3: 手动转换 (备用)

**说明：**
- 用户可以手动将DWG文件转换为DXF格式
- 支持任何能生成DXF的CAD软件

## 支持的文件格式

| 格式 | 支持程度 | 说明 |
|------|----------|------|
| .dxf | ✅ 完全支持 | 原生支持，无需转换 |
| .dwg | ✅ 完全支持 | 通过ODA File Converter或ezdxf |
| .dwt | ⚠️ 部分支持 | DWG模板文件，需要转换 |

## 功能特性

### 1. 多图框自动检测
- 自动识别图纸中的图框
- 支持不同尺寸的图框（A0-A4）
- 智能过滤无效图框

### 2. 图纸信息提取
- 图纸编号识别
- 图纸标题提取
- 比例信息获取

### 3. 按图号排序
- 自然排序算法（A-01, A-02, A-10...）
- 支持多种编号格式
- 智能处理编号异常

### 4. 构件识别
- 墙体检测
- 柱子识别
- 梁、板、基础识别
- 工程量自动计算

## 错误处理

### 常见错误及解决方案

#### 1. "File is not a DXF file"
**原因：** DWG文件无法直接解析
**解决：** 安装ODA File Converter

#### 2. "ODA File Converter not installed"
**原因：** 系统未找到ODA File Converter
**解决：** 
- 安装ODA File Converter
- 确保安装路径正确
- 检查环境变量

#### 3. "Unknown DWG version"
**原因：** DWG文件版本过新或损坏
**解决：**
- 使用较新版本的AutoCAD保存为较低版本
- 检查文件是否损坏

## API使用示例

### 启动DWG多图框处理
```bash
POST /api/v1/drawings/{drawing_id}/process-dwg-multi-sheets
```

### 获取处理状态
```bash
GET /api/v1/drawings/{drawing_id}/dwg-multi-sheets-status
```

### 获取图纸列表
```bash
GET /api/v1/drawings/{drawing_id}/dwg-drawings-list
```

## 性能优化建议

### 1. 文件大小优化
- 建议DWG文件大小不超过50MB
- 复杂文件可能需要更长处理时间
- 考虑清理无用图层和实体

### 2. 图框设计建议
- 使用标准图框格式
- 确保图号清晰可读
- 避免图框重叠或变形

### 3. 系统配置
- 确保足够的临时存储空间
- 定期清理临时文件
- 监控内存使用情况

## 故障排除

### 日志查看
```bash
# 查看处理日志
tail -f logs/dwg_processing.log

# 查看错误日志
tail -f logs/error.log
```

### 调试模式
```bash
# 启用详细日志
export DWG_DEBUG=true

# 保留临时文件用于调试
export DWG_KEEP_TEMP_FILES=true
```

## 技术支持

如果遇到DWG文件处理问题，请提供以下信息：
1. DWG文件版本和来源软件
2. 文件大小和复杂程度
3. 错误信息和日志
4. 系统环境信息

## 未来功能计划

### 短期（1-3个月）
- 支持更多DWG版本
- 优化处理性能
- 增强错误恢复能力

### 中期（3-6个月）
- 支持3D DWG文件
- 增加图块识别
- 自定义图框模板

### 长期（6-12个月）
- 实时协作编辑
- 云端DWG处理
- AI增强识别算法 