# AI Analyzer 重构计划

## 当前状态
- 文件：`app/services/ai_analyzer.py`
- 行数：2178行
- 主要问题：单一文件过大，功能耦合严重

## 重构目标
将单一大文件按功能拆分为多个专门的模块，提高代码可维护性和可测试性。

## 拆分方案

### 1. AIAnalyzerService (核心类) - `ai_analyzer_core.py`
**保留功能：**
- `__init__()` - 初始化
- `is_available()` - 服务可用性检查
- `generate_qto_from_data()` - 主要入口方法
- `_ensure_interaction_logger()` - 交互记录器管理

**预计行数：** ~200行

### 2. PromptBuilder - `ai_prompt_builder.py`
**迁移功能：**
- `_build_system_prompt()` - 构建系统提示词
- `_build_enhanced_system_prompt()` - 构建增强系统提示词
- `_build_user_prompt()` - 构建用户提示词
- 所有提示词模板和构建逻辑

**预计行数：** ~400行

### 3. MockDataDetector - `ai_mock_detector.py`
**迁移功能：**
- `_check_for_mock_data_patterns()` - 检查模拟数据模式
- `_enhance_mock_data_detection()` - 增强模拟数据检测
- `_validate_response_authenticity()` - 验证响应真实性
- 所有模拟数据检测相关逻辑

**预计行数：** ~300行

### 4. VisionAnalyzer - `ai_vision_analyzer.py`
**迁移功能：**
- `generate_qto_from_local_images()` - 从本地图片生成QTO
- `generate_qto_from_encoded_images()` - 从编码图片生成QTO
- `_execute_multi_turn_analysis()` - 执行多轮分析
- `_prepare_images()` - 图片预处理
- 所有单步Vision分析方法（step1-5）

**预计行数：** ~600行

### 5. ContextualAnalyzer - `ai_contextual_analyzer.py`
**迁移功能：**
- `generate_qto_from_local_images_v2()` - V2版本图片分析
- `_execute_multi_turn_analysis_with_context()` - 带上下文的多轮分析
- 所有上下文相关的step方法
- `_build_step*_context()` - 构建步骤上下文
- `_make_contextual_api_call()` - 上下文API调用

**预计行数：** ~500行

### 6. ResponseSynthesizer - `ai_response_synthesizer.py`
**迁移功能：**
- `_synthesize_qto_data()` - 合成QTO数据
- `_determine_component_type()` - 确定构件类型
- `_generate_quantity_summary()` - 生成数量汇总
- 所有响应处理和数据合成逻辑

**预计行数：** ~200行

### 7. AsyncAnalyzer - `ai_async_analyzer.py`
**迁移功能：**
- `analyze_text_async()` - 异步文本分析
- 所有异步相关方法
- 会话管理相关方法

**预计行数：** ~100行

## 重构步骤

### 第一步：创建基础结构
1. 创建新的模块文件
2. 定义各模块的接口和基础类结构
3. 建立模块间的依赖关系

### 第二步：迁移独立功能
1. 先迁移最独立的功能（如MockDataDetector）
2. 逐步迁移其他模块
3. 保持原有接口不变

### 第三步：重构核心类
1. 将AIAnalyzerService改为组合模式
2. 注入各个专门的服务类
3. 保持对外接口兼容

### 第四步：测试和优化
1. 运行现有测试确保功能正常
2. 优化模块间的依赖关系
3. 清理重复代码

## 模块依赖关系

```
AIAnalyzerService (核心)
├── PromptBuilder (提示词构建)
├── MockDataDetector (模拟数据检测)
├── VisionAnalyzer (视觉分析)
├── ContextualAnalyzer (上下文分析)
├── ResponseSynthesizer (响应合成)
└── AsyncAnalyzer (异步分析)
```

## 接口设计

### AIAnalyzerService
```python
class AIAnalyzerService:
    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.mock_detector = MockDataDetector()
        self.vision_analyzer = VisionAnalyzer()
        self.contextual_analyzer = ContextualAnalyzer()
        self.response_synthesizer = ResponseSynthesizer()
        self.async_analyzer = AsyncAnalyzer()
```

## 重构优势

1. **可维护性提升**：每个模块职责单一，易于理解和修改
2. **可测试性增强**：可以对每个模块单独进行单元测试
3. **可扩展性改善**：新功能可以作为新模块添加
4. **代码复用**：各模块可以在不同场景下复用
5. **并行开发**：团队可以并行开发不同模块

## 注意事项

1. **向后兼容**：确保重构后的接口与现有代码兼容
2. **渐进式重构**：分步骤进行，每步都要确保系统可运行
3. **测试覆盖**：重构过程中要保持测试覆盖率
4. **文档更新**：重构完成后更新相关文档

## 预期效果

- 主文件行数从2178行降低到200行左右
- 每个专门模块控制在500行以内
- 代码结构更加清晰，易于维护
- 提高开发效率和代码质量 