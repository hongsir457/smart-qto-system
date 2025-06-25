# 文件数据流一致性代码审查检查清单

## 概述
本检查清单用于确保Smart QTO系统中文件上传、存储、下载流程的数据一致性。

## 🔍 核心检查项目

### 1. 文件命名策略一致性
- [ ] **统一使用 `FileNamingStrategy`**
  - 所有文件上传都使用 `file_naming_strategy.generate_storage_key()`
  - 避免硬编码文件路径或文件名
  - 检查文件：`upload.py`, `s3_service.py`, `advanced_ocr_engine.py`

- [ ] **S3键名格式标准化**
  - 格式：`{folder}/{uuid}{extension}`
  - 避免使用原始文件名作为存储键名
  - 确保支持中文文件名和特殊字符

- [ ] **文件类型验证统一**
  - 使用 `file_naming_strategy.validate_file_type()`
  - 避免重复定义支持的文件类型列表
  - MIME类型映射集中管理

### 2. 存储操作一致性
- [ ] **上传流程标准化**
  ```python
  # ✅ 正确方式
  storage_info = file_naming_strategy.generate_storage_key(original_filename)
  s3_result = s3_service.upload_file(
      file_obj=file_obj,
      file_name=storage_info['storage_filename'],
      content_type=storage_info['content_type'],
      folder=storage_info['folder']
  )
  ```

- [ ] **下载流程使用s3_key**
  ```python
  # ✅ 正确方式
  download_success = s3_service.download_file(
      s3_key=drawing.s3_key,  # 使用数据库中的s3_key
      local_path=local_file_path
  )
  ```

- [ ] **删除操作完整性**
  - 使用 `FileLifecycleManager.delete_file_completely()`
  - 确保删除S3文件、本地文件和数据库记录
  - 避免只删除数据库记录而遗留文件

### 3. 数据库字段使用规范
- [ ] **优先使用s3_key字段**
  - 文件下载：使用 `drawing.s3_key`
  - 文件删除：使用 `drawing.s3_key`
  - 避免使用 `drawing.filename` 构造文件路径

- [ ] **file_path字段逐步废弃**
  - 新代码不应依赖 `drawing.file_path`
  - 仅在兼容性需要时使用
  - 计划在未来版本中移除

- [ ] **S3相关字段完整性**
  - `s3_key`: 必须字段，用于文件操作
  - `s3_url`: 可选，用于直接访问
  - `s3_bucket`: 可选，用于跨桶操作

### 4. 错误处理和回滚
- [ ] **上传失败处理**
  - S3上传失败时清理数据库记录
  - 提供明确的错误信息
  - 避免产生孤儿记录

- [ ] **下载失败处理**
  - 检查文件是否存在于S3
  - 提供本地存储回退机制
  - 记录详细的错误日志

- [ ] **删除操作原子性**
  - 部分删除失败时的处理策略
  - 记录删除操作的详细结果
  - 支持重试机制

## 🧪 测试要求

### 1. 单元测试
- [ ] **文件命名策略测试**
  - 测试各种文件名格式
  - 验证特殊字符处理
  - 检查路径解析正确性

- [ ] **S3操作测试**
  - 上传-下载-删除完整流程
  - 文件内容一致性验证
  - 错误情况处理测试

### 2. 集成测试
- [ ] **端到端流程测试**
  - 文件上传到处理完成
  - 多用户并发操作
  - 大文件处理测试

- [ ] **数据一致性测试**
  - 数据库记录与实际文件的一致性
  - 跨服务重启的数据持久性
  - 异常情况下的数据完整性

### 3. 性能测试
- [ ] **批量操作测试**
  - 批量上传性能
  - 批量删除完整性
  - 并发操作稳定性

## 🔧 常见问题和修复

### 1. 文件路径构造错误
```python
# ❌ 错误方式
file_path = f"drawings/{drawing.filename}"

# ✅ 正确方式
s3_key = drawing.s3_key
```

### 2. 删除操作不完整
```python
# ❌ 错误方式 - 只删除数据库
db.delete(drawing)
db.commit()

# ✅ 正确方式 - 完整删除
file_manager = FileLifecycleManager(s3_service, db)
result = await file_manager.delete_file_completely(drawing_id, user_id)
```

### 3. 文件类型验证重复
```python
# ❌ 错误方式 - 重复定义
allowed_extensions = {'.pdf', '.dwg', '.dxf'}

# ✅ 正确方式 - 统一验证
if not file_naming_strategy.validate_file_type(filename):
    raise ValueError("不支持的文件类型")
```

## 📋 审查检查点

### 代码提交前检查
1. [ ] 所有文件操作使用统一的命名策略
2. [ ] 没有硬编码的文件路径或文件名
3. [ ] 删除操作包含完整的清理逻辑
4. [ ] 错误处理覆盖所有异常情况
5. [ ] 添加了相应的单元测试

### 功能测试检查
1. [ ] 上传-下载流程正常工作
2. [ ] 中文文件名正确处理
3. [ ] 特殊字符文件名安全处理
4. [ ] 批量操作稳定可靠
5. [ ] 错误情况优雅处理

### 性能和安全检查
1. [ ] 文件大小限制正确实施
2. [ ] 文件类型验证严格执行
3. [ ] 用户权限检查完整
4. [ ] 临时文件及时清理
5. [ ] 敏感信息不泄露

## 🚀 持续改进

### 监控指标
- 文件上传成功率
- 文件下载成功率
- 删除操作完整性
- 存储空间使用效率

### 定期审查
- 每月检查孤儿文件
- 季度性能优化评估
- 年度架构设计审查

---

**注意**: 本检查清单应在每次涉及文件操作的代码变更时使用，确保系统的数据流一致性和可靠性。 