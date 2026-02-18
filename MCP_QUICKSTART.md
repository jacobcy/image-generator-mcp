# Cell Cover Generator MCP - 快速开始

## 🚀 5 分钟快速开始

### 1. 安装依赖

```bash
cd /path/to/image-generator-mcp

# 安装 MCP 依赖
uv pip install fastmcp
```

### 2. 配置 API 密钥（必需）

```bash
# 设置 TTAPI API 密钥
export TTAPI_API_KEY="your-ttapi-key-here"

# 或创建 .env 文件
echo "TTAPI_API_KEY=your-ttapi-key-here" > .env
```

### 3. 初始化项目（首次使用）

```bash
# 初始化 Cell Cover Generator
uv run crc init
```

### 4. 启动 MCP 服务器

#### 方式 A：使用启动脚本（推荐）

```bash
./scripts/start_mcp.sh
```

#### 方式 B：直接运行

```bash
uv run mcp_server
```

### 5. 在 Claude Desktop 中配置

1. 打开 Claude Desktop
2. 进入 **Settings** → **Developer**
3. 点击 **MCP Servers** 旁的 "+" 按钮
4. 选择 **Command** 配置
5. 添加以下配置：

```json
{
  "name": "cell-cover-generator",
  "command": "uv",
  "args": [
    "run",
    "--directory",
    "/path/to/image-generator-mcp",
    "mcp_server"
  ],
  "env": {}
}
```

6. 点击 **Save** 保存配置
7. 重启 Claude Desktop

## ✅ 测试连接

重启 Claude Desktop 后，你可以在对话中直接使用 Cell Cover Generator 功能：

```
用户：帮我查看有哪些创意概念可用。

Claude：[自动调用 list_concepts 工具]

[返回结果]
可用概念：
- cell_membrane: 细胞膜结构与功能
- cell_nucleus: 细胞核与遗传信息
- mitochondria: 线粒体与能量代谢
...
```

## 📚 可用的 MCP 工具

| 工具 | 说明 | 示例 |
|------|------|------|
| `list_concepts` | 列出所有创意概念 | "有什么概念？" |
| `list_variations` | 列出概念的变体 | "这个概念有哪些变体？" |
| `create_image` | 创建图像生成任务 | "生成一张细胞膜图" |
| `list_tasks` | 列出任务 | "显示最近的任务" |
| `view_task` | 查看任务详情 | "任务 abc-123 完成了吗？" |
| `perform_action` | 执行操作 | "对第一个变体做 upscale" |
| `describe_image` | 描述图片 | "这张图是什么？" |

## 💡 对话示例

### 创建封面图

```
你：帮我为 Cell Reports Medicine 杂志生成一张封面。

Claude：[调用 list_concepts]

有哪些可用的创意概念？
- cell_membrane: 细胞膜结构与功能
- cell_nucleus: 细胞核与遗传信息
- mitochondria: 线粒体与能量代谢
- ...

你：用 cell_membrane 这个概念，16:9 比例。

Claude：[调用 create_image]
✓ 任务已创建
Job ID: abc-123-def-456
```

### 查看任务状态

```
你：之前的任务完成了吗？

Claude：[调用 view_task]
任务 abc-123-def-456
状态: completed
图像: https://...
```

### 执行变体操作

```
你：我想要第一张图的变体版本。

Claude：[调用 perform_action]
操作 variation1 已执行
新 Job ID: xyz-789-ghi-012
```

## 🧩 故障排除

### Claude Desktop 无法连接 MCP 服务器

1. **检查 MCP 服务器是否运行**
   ```bash
   # MCP 服务器应该正在运行
   # 查看启动脚本的输出
   ```

2. **检查 Claude Desktop 日志**
   - Claude Desktop → Help → Developer → Open Logs
   - 查找 MCP 相关的错误信息

3. **验证配置**
   - 确认 "command" 路径正确
   - 确认 "args" 中的目录路径正确

### MCP 工具调用失败

1. **检查 API 密钥**
   ```bash
   echo $TTAPI_API_KEY
   ```

2. **检查项目初始化**
   ```bash
   # 确认 .crc 目录存在
   ls -la .crc
   ```

3. **查看详细错误**
   ```bash
   # 在启动脚本中启用详细模式
   fastmcp run mcp_server --verbose
   ```

## 📖 更多信息

- [MCP_README.md](./MCP_README.md) - 完整的 MCP 文档
- [README.md](./README.md) - Cell Cover Generator 项目文档
- [FastMCP 文档](https://gofastmcp.com) - FastMCP 框架文档

## 🎉 完成！

现在你可以在 Claude Desktop 中直接使用 Cell Cover Generator 的所有功能了！
