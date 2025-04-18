# 常用Mcp工具

## 1. 文件系统操作工具

### 基础文件操作
- `mcp_filesystem_read_file`: 读取单个文件内容
  ```python
  # 示例:读取README.md
  {"path": "README.md"}
  ```

- `mcp_filesystem_write_file`: 创建或覆写文件
  ```python
  # 示例:创建新文件
  {
    "path": "new-file.txt",
    "content": "文件内容"
  }
  ```

- `mcp_filesystem_edit_file`: 编辑现有文件
  ```python
  # 示例:修改文件内容
  {
    "path": "config.json",
    "edits": [
      {
        "oldText": "旧内容",
        "newText": "新内容"
      }
    ]
  }
  ```

### 目录操作
- `mcp_filesystem_create_directory`: 创建目录
  ```python
  # 示例:创建新目录
  {"path": "src/components"}
  ```

- `mcp_filesystem_list_directory`: 列出目录内容
  ```python
  # 示例:查看src目录
  {"path": "src"}
  ```

- `mcp_filesystem_directory_tree`: 获取目录树结构
  ```python
  # 示例:查看项目结构
  {"path": "."}
  ```

### 文件管理
- `mcp_filesystem_move_file`: 移动/重命名文件
  ```python
  # 示例:移动文件
  {
    "source": "old/path.txt",
    "destination": "new/path.txt"
  }
  ```

- `mcp_filesystem_search_files`: 搜索文件
  ```python
  # 示例:搜索.ts文件
  {
    "path": "src",
    "pattern": "*.ts"
  }
  ```

- `mcp_filesystem_get_file_info`: 获取文件信息
  ```python
  # 示例:获取文件元数据
  {"path": "package.json"}
  ```

## 2. 知识库工具(Basic Memory)

- `mcp_basic_memory_write_note`: 创建/更新笔记
  ```python
  # 示例:创建开发日志
  {
    "title": "开发日志-20240321",
    "content": "今日完成...",
    "folder": "dev-logs"
  }
  ```

- `mcp_basic_memory_read_note`: 读取笔记
  ```python
  # 示例:读取笔记
  {"identifier": "开发日志-20240321"}
  ```

- `mcp_basic_memory_search_notes`: 搜索笔记
  ```python
  # 示例:搜索相关笔记
  {"query": "API设计"}
  ```

## 3. Git操作工具

- `mcp_git_git_status`: 查看仓库状态
  ```python
  {"repo_path": "/Users/chenyi/Public/VibeCopilot"}
  ```

- `mcp_git_git_commit`: 提交更改
  ```python
  {
    "repo_path": "/Users/chenyi/Public/VibeCopilot",
    "message": "feat: 添加新功能"
  }
  ```

- `mcp_git_git_diff`: 查看差异
  ```python
  {
    "repo_path": "/Users/chenyi/Public/VibeCopilot",
    "target": "main"
  }
  ```

## 4. 时间工具

- `mcp_time_get_current_time`: 获取当前时间
  ```python
  {"timezone": "Asia/Shanghai"}
  ```

- `mcp_time_convert_time`: 时区转换
  ```python
  {
    "time": "14:30",
    "source_timezone": "Asia/Shanghai",
    "target_timezone": "America/New_York"
  }
  ```

## 5. 思维链工具

- `mcp_sequential_thinking_sequentialthinking`: 用于复杂问题分析
  ```python
  {
    "thought": "分析问题第一步...",
    "thoughtNumber": 1,
    "totalThoughts": 5,
    "nextThoughtNeeded": true
  }
  ```

## 使用建议

1. **路径使用**:
   - 优先使用绝对路径
   - 确保路径在允许的目录范围内

2. **错误处理**:
   - 操作前检查文件/目录是否存在
   - 注意权限问题

3. **最佳实践**:
   - 文件操作前先备份
   - Git操作前检查状态
   - 大文件操作时注意性能

4. **安全考虑**:
   - 不在代码中保存敏感信息
   - 使用环境变量存储密钥

这些工具能帮助我们更高效地进行开发工作。根据具体场景选择合适的工具,并注意遵循项目的规范和最佳实践。
