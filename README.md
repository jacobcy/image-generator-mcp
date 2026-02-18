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

需要 Python 3.10+ 环境：

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install fastmcp
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

# 或者直接运行
uv run mcp-server
```

### 4. 连接到 Claude Desktop

在 Claude Desktop 的配置中添加：

```json
{
  "mcpServers": {
    "image-gen": {
      "command": "/path/to/image-gen-mcp/.venv/bin/mcp-server",
      "args": []
    }
  }
}
```

## 项目结构

```
image-generator-mcp/
├── image_gen_mcp/       # 核心源代码
│   ├── apps/           # 插件模块 (如 cell_cover)
│   ├── core/           # 核心框架代码
│   └── main.py         # 入口文件
├── scripts/            # 辅助脚本
├── tests/              # 测试用例
├── pyproject.toml      # 项目配置
└── README.md           # 项目文档
```

## 开发指南

### 添加新功能

1. 在 `image_gen_mcp/apps/` 下创建新的模块
2. 实现 `register(mcp)` 函数来注册工具和资源
3. 确保在系统启动时加载该模块

更多详细信息请参考 [MCP_README.md](MCP_README.md)。

## 许可证

MIT License