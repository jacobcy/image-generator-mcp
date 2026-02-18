# Image Generator MCP Server

基于 Model Context Protocol (MCP) 的图像生成服务，专注于高质量的图像生成和处理。

## 主要功能

- **MCP 协议支持**: 完全兼容 Model Context Protocol，可与 Claude Desktop 等客户端无缝集成
- **Midjourney 集成**: 
  - 支持文生图 (Imagine)
  - 图像变换 (Variation)
  - 图像放大 (Upscale)
  - 局部重绘 (Inpaint)
  - 图片描述 (Describe)
- **概念管理系统**:
  - 预设风格和概念库
  - 灵活的提示词组合
- **多平台支持**: 
  - 支持 macOS/Linux/Windows
  - 可通过 Tailscale 进行远程访问

## 快速开始

### 1. 安装依赖

本项目使用 `uv` 进行包管理。

```bash
# 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步依赖
uv sync

# 或者直接安装到当前环境
uv pip install -e .
```

### 2. 配置环境

复制示例配置文件并填入必要的 API 密钥：

```bash
cp .env-sample .env
```

编辑 `.env` 文件，填入 `TTAPI_API_KEY` (Midjourney API密钥)。

### 3. 启动服务

```bash
# 使用辅助脚本启动
./scripts/start_mcp.sh

# 或者使用 uv 直接运行
uv run mcp-server
```

### 4. 连接到 Claude Desktop

在 Claude Desktop 的配置中添加：

```json
{
  "mcpServers": {
    "image-gen": {
      "command": "/usr/local/bin/uv",
      "args": [
        "--directory",
        "/path/to/image-generator-mcp",
        "run",
        "mcp-server"
      ]
    }
  }
}
```

## 项目结构

```
image-generator-mcp/
├── image_gen_mcp/       # 核心源代码
│   ├── apps/            # 插件模块 (如 cell_cover)
│   ├── core/            # 核心框架代码 (MCP Server)
│   └── main.py          # 入口文件
├── scripts/             # 辅助脚本
├── tests/               # 测试用例
├── AGENTS.md            # Agent 文档
├── ARCHITECTURE.md      # 架构文档
├── pyproject.toml       # 项目配置
└── README.md            # 项目文档
```

## 开发指南

### 添加新功能

1. 在 `image_gen_mcp/apps/` 下创建新的模块
2. 实现 `register(mcp)` 函数来注册工具和资源
3. 确保在系统启动时加载该模块

## 许可证

MIT License