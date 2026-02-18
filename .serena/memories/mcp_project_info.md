# Cell Cover Generator MCP 项目

## MCP 服务器信息
- **主文件**: `mcp_server/__init__.py`
- **启动命令**: `uv run mcp_server` 或 `./scripts/start_mcp.sh`
- **框架**: FastMCP (>=3.0.0rc2)

## 可用的 MCP 工具

| 工具 | 功能 |
|------|------|
| `list_concepts` | 列出创意概念 |
| `list_variations` | 列出概念变体 |
| `create_image` | 创建图像生成任务 |
| `list_tasks` | 列出任务 |
| `view_task` | 查看任务详情 |
| `perform_action` | 执行操作（variation/upscale/reroll） |
| `describe_image` | 描述图片 |

## 可用的 MCP 资源

| 资源 | 说明 |
|------|------|
| `file://concepts.json` | 概念配置 |
| `file://tasks.json` | 任务列表 |

## Claude Desktop 配置

```json
{
  "name": "cell-cover-generator",
  "command": "uv",
  "args": [
    "run",
    "--directory",
    "/path/to/image-generator-mcp",
    "mcp_server"
  ]
}
```

## 文档位置
- `MCP_README.md` - 完整 MCP 服务器文档
- `MCP_QUICKSTART.md` - 5 分钟快速开始指南
- `mcp_server/__init__.py` - MCP 服务器实现
