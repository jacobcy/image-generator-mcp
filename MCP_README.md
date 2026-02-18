# Cell Cover Generator MCP Server

通过 **Model Context Protocol (MCP)** 提供的 Cell 杂志封面生成工具。

## 📖 概述

将 Cell Cover Generator 的所有功能封装为 MCP 工具和资源，使 LLM（如 Claude）能够直接调用图像生成、任务管理等能力。

## ✨ 功能

### MCP 工具 (Tools)

| 工具 | 说明 |
|------|------|
| `list_concepts` | 列出所有可用的创意概念 |
| `list_variations` | 列出指定概念的所有变体 |
| `create_image` | 创建新的 Midjourney 图像生成任务 |
| `list_tasks` | 列出任务列表 |
| `view_task` | 查看任务详情 |
| `perform_action` | 对任务执行操作（variation, upscale, reroll） |
| `describe_image` | 根据图片生成提示词 |

### MCP 资源 (Resources)

| 资源 | 说明 |
|------|------|
| `file://concepts.json` | 创意概念配置 JSON 文件 |
| `file://tasks.json` | 任务列表 JSON 文件 |

## 🚀 安装

### 1. 安装依赖

```bash
# 使用 uv
uv pip install fastmcp

# 或使用 pip
pip install fastmcp
```

### 2. 验证安装

```bash
# 检查 fastmcp 是否安装
fastmcp --version
```

## 🎯 使用

### 启动 MCP 服务器

#### 方式 1：使用 FastMCP CLI（推荐）

```bash
# 进入项目目录
cd /path/to/image-generator-mcp

# 启动 MCP 服务器（使用 stdio 传输）
fastmcp run mcp_server/mcp_server.py:mcp
```

#### 方式 2：使用 uv run

```bash
uv run mcp-server
```

#### 方式 3：使用 HTTP 传输

```bash
fastmcp run mcp_server/mcp_server.py:mcp --transport http --port 8000
```

### 在 Claude Desktop 中配置

1. 打开 **Claude Desktop**
2. 进入 **Settings** → **Developer**
3. 点击 **MCP Servers** 旁的 "+" 按钮
4. 选择 **Command** 方式
5. 配置如下：

```json
{
  "name": "cell-cover-generator",
  "command": "uv",
  "args": [
    "run",
    "--directory",
    "/path/to/image-generator-mcp",
    "mcp-server"
  ]
}
```

或使用 FastMCP CLI：

```json
{
  "name": "cell-cover-generator",
  "command": "fastmcp",
  "args": [
    "run",
    "/path/to/image-generator-mcp/mcp_server/mcp_server.py:mcp"
  ]
}
```

6. 保存并重启 Claude

## 💡 LLM 对话示例

### 场景 1：查看可用概念

```
用户：有哪些可用的创意概念？

Claude：[调用 list_concepts 工具]

[Cell Cover Generator 返回]
可用概念：
- cell_membrane: 细胞膜结构与功能
- cell_nucleus: 细胞核与遗传信息
- mitochondria: 线粒体与能量代谢
...
```

### 场景 2：生成图像

```
用户：帮我生成一张细胞膜的封面图，16:9 比例，使用现代科学风格。

Claude：[调用 create_image 工具]
参数：
  - concept: "cell_membrane"
  - aspect_ratio: "16:9"
  - prompt: "现代科学风格，高清显微镜下的细胞膜结构"
  - style: "raw"

[Cell Cover Generator 返回]
任务创建成功！
Job ID: abc-123-def-456
...
```

### 场景 3：查看任务状态

```
用户：刚才的任务完成了吗？

Claude：[调用 view_task 工具]
参数：
  - task_id: "abc-123-def-456"

[Cell Cover Generator 返回]
任务详情：
- 状态: completed
- 图像 URL: https://...
- 提示词: ...
```

### 场景 4：执行变体操作

```
用户：我想要第一个变体版本。

Claude：[调用 perform_action 工具]
参数：
  - task_id: "abc-123-def-456"
  - action_code: "variation1"
  - mode: "fast"

[Cell Cover Generator 返回]
操作 variation1 已执行
新的 Job ID: xyz-789-ghi-012
...
```

## 🔧 配置

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TTAPI_API_KEY` | TTAPI API 密钥（必需） | - |
| `OPENAI_API_KEY` | OpenAI API 密钥（可选，用于概念生成） | - |

### 配置文件

MCP 服务器使用现有的 Cell Cover Generator 配置：

- **全局配置**: `~/.crc/prompts_config.json`
- **项目配置**: `./.crc/`
- **元数据**: `./.crc/metadata/images_metadata.json`

## 🌐 网络配置

### Tailscale 集成

如果通过 Tailscale 访问，参考以下文档：

- [TAILSCALE_GUIDE.md](../TAILSCALE_GUIDE.md) - Tailscale 使用指南
- [SERVER_GUIDE.md](../SERVER_GUIDE.md) - HTTP 服务器配置

### MCP 传输模式

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| **stdio** | 标准 I/O 传输，适合 Claude Desktop | 本地开发 |
| **HTTP** | HTTP 传输，适合远程访问 | 网络服务 |

## 🧪 工具参数详解

### create_image

```python
{
    "prompt": "string",           # 必需：提示词
    "concept": "string",         # 可选：概念键名
    "aspect_ratio": "string",     # 可选：16:9, 1:1, 9:16
    "style": "string",            # 可选：raw, cute, expressive
    "version": "string",          # 可选：v6, v7, niji
    "mode": "string",             # 可选：relax, fast, turbo（默认：relax）
    "chaos": "integer",           # 可选：0-100
    "stylize": "integer",          # 可选：0-1000
    "seed": "integer",            # 可选：任意整数
    "quality": "string"           # 可选：0.25, 0.5, 1, 2
}
```

### list_tasks

```python
{
    "limit": "integer",            # 可选：返回数量（默认：20）
    "status": "string",           # 可选：按状态过滤
    "concept": "string",          # 可选：按概念过滤
    "sort_by": "string"           # 可选：排序字段（默认：created_at）
}
```

### perform_action

```python
{
    "task_id": "string",           # 必需：任务 ID
    "action_code": "string",       # 必需：操作代码
    "mode": "string",             # 可选：relax, fast, turbo（默认：fast）
    "wait": "boolean"             # 可选：是否等待完成（默认：false）
}
```

**可用操作代码：**
- `upsample1`, `upsample2`, `upsample3`, `upsample4` - 放大指定部分
- `variation1`, `variation2`, `variation3`, `variation4` - 创建变体
- `reroll` - 重新生成

## 🔍 故障排除

### 无法导入 cell_cover 模块

```bash
# 确保在项目根目录
cd /path/to/image-generator-mcp

# 或使用 PYTHONPATH
export PYTHONPATH="/path/to/image-generator-mcp:$PYTHONPATH"
```

### TTAPI API 密钥未设置

```bash
# 设置环境变量
export TTAPI_API_KEY="your-api-key-here"

# 或创建 .env 文件
echo "TTAPI_API_KEY=your-api-key" > .env
```

### MCP 服务器无法启动

```bash
# 检查 fastmcp 是否安装
fastmcp --version

# 检查 Python 版本
python --version  # 需要 >= 3.10

# 查看详细错误
fastmcp run mcp_server/mcp_server.py:mcp --verbose
```

### Claude Desktop 无法连接

1. **检查命令路径** - 确保 `uv` 和 `fastmcp` 在 PATH 中
2. **查看日志** - Claude Desktop 的 Developer 控制台会显示错误
3. **测试工具调用** - 使用 Claude Desktop 的 MCP 测试功能

## 📚 相关文档

- [README.md](../README.md) - Cell Cover Generator 原项目文档
- [SERVER_GUIDE.md](../SERVER_GUIDE.md) - HTTP 服务器配置
- [TAILSCALE_GUIDE.md](../TAILSCALE_GUIDE.md) - Tailscale 网络配置
- [FastMCP 文档](https://gofastmcp.com) - FastMCP 框架文档
- [MCP 规范](https://modelcontextprotocol.io) - Model Context Protocol 规范

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

与 Cell Cover Generator 主项目相同
