# 项目架构说明

## 📖 项目概述

**Cell Cover Generator MCP** 是一个多层架构项目，提供通过多种方式访问 Cell Reports Medicine 杂志封面生成功能的能力。

```
┌─────────────────────────────────────────────────────────────────┐
│                     Cell Cover Generator                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────┐
│  │  CLI 命令    │  │  HTTP 服务器   │  │  MCP 服务器      │
│  │              │  │                │  │                  │
│  │ • create    │  │ • FastAPI     │  │ • FastMCP         │
│  │ • generate   │  │ • REST API    │  │ • Tools           │
│  │ • view      │  │ • Swagger UI   │  │ • Resources        │
│  │ • action    │  │                │  │                  │
│  │ ...         │  │                │  │                  │
│  └──────────────┘  └───────────────┘  └───────────────────┘
│         │                │                  │
└─────────┼────────────────┼──────────────────┘
          │                │
    ┌─────▼────┐  ┌─────▼─────┐
    │ Tailscale  │  │   LLM     │
    │   网络    │  │  (Claude)  │
    └───────────┘  └────────────┘
```

## 🏗️ 架构层级

### 第 1 层：核心功能层 (cell_cover/)

**职责**：实现 Cell Cover Generator 的核心业务逻辑

| 模块 | 功能 |
|------|------|
| `cli.py` | 命令行接口 |
| `commands/` | 命令处理器（create, view, action 等） |
| `utils/` | 工具函数（配置、API 客户端、日志等） |
| `constants.py` | 常量定义（操作代码、参数等） |

**数据流**：
```
用户输入 → CLI 解析 → 命令处理器 → API 调用 → 结果输出
```

### 第 2 层：HTTP 服务器层 (server/api.py)

**职责**：将 CLI 功能封装为 HTTP REST API

| 组件 | 说明 |
|------|------|
| FastAPI | Web 框架 |
| CORS 中间件 | 跨域支持 |
| 端点封装 | /api/v1/create, /api/v1/tasks 等 |
| 文件上传处理 | 图像上传、下载 |

**数据流**：
```
HTTP 请求 → FastAPI → 捕获 CLI 输出 → JSON 响应
```

**适用场景**：
- 通过 Tailscale 网络远程访问
- 集成到其他 Web 应用
- 需要标准 REST API 的场景

### 第 3 层：MCP 协议层 (mcp_server/)

**职责**：将功能封装为 MCP (Model Context Protocol) 工具和资源

| 组件 | 说明 |
|------|------|
| FastMCP | MCP 框架 |
| `@mcp.tool` | 工具装饰器 |
| `@mcp.resource` | 资源装饰器 |
| stdio 传输 | 标准 I/O 传输 |

**数据流**：
```
LLM 请求 → MCP 协议 → 调用工具函数 → CLI 执行 → 返回结果
```

**适用场景**：
- 集成到 Claude Desktop
- 集成到其他支持 MCP 的 LLM 应用
- 需要上下文感知的 AI 应用

## 🔄 数据流架构

### 核心数据流向

```
┌─────────────────────────────────────────────────────────────────┐
│                         核心数据流                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. 配置层                                                  │
│     ┌─────────────┐                                          │
│     │ ~/.crc/    │ ← 全局配置（概念、风格）        │
│     │ .crc/        │ ← 项目配置（状态、元数据）   │
│     │ .env         │ ← API 密钥                            │
│     └─────────────┘                                          │
│                                                                 │
│  2. 业务逻辑层                                              │
│     ┌─────────────┐                                          │
│     │ cell_cover/ │ ← 核心功能实现                  │
│     │             │                                          │
│     │  • CLI 命令  │                                      │
│     │  • API 调用  │                                      │
│     │  • 文件处理  │                                      │
│     └─────────────┘                                          │
│                                                                 │
│  3. 接口层（多接口模式）                                  │
│     ┌───────────────────────────────────┐                        │
│     │ 接口类型 │  客户端   │  使用场景              │
│     ├────────────┼──────────┼────────────────┤             │
│     │ CLI 命令  │  Terminal  │  命令行使用          │
│     │ HTTP API   │  浏览器/cURL│ Tailscale 远程访问  │
│     │ MCP        │  LLM 应用  │  Claude Desktop 等    │
│     └────────────┴──────────┴────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
image-generator-mcp/
│
├── 📄 核心代码 (cell_cover/)
│   ├── __init__.py
│   ├── cli.py              # CLI 入口
│   ├── constants.py         # 常量定义
│   ├── prompts_config.json   # 默认配置
│   │
│   ├── commands/            # 命令处理器
│   │   ├── __init__.py
│   │   ├── create.py      # 创建任务
│   │   ├── generate.py     # 生成提示词
│   │   ├── view.py        # 查看任务
│   │   ├── action.py       # 执行操作
│   │   ├── list_cmd.py     # 列出概念
│   │   ├── list_tasks.py   # 列出任务
│   │   ├── describe.py     # 描述图像
│   │   └── ...
│   │
│   └── utils/              # 工具函数
│       ├── __init__.py
│       ├── config.py       # 配置管理
│       ├── api_client.py    # API 客户端
│       ├── api.py          # API 封装
│       ├── log.py          # 日志管理
│       ├── image_handler.py # 图像处理
│       └── ...
│
├── 🌐 HTTP 服务器 (server/api.py)
│   └── api.py            # FastAPI 服务器（Tailscale 用途）
│
├── 🔌 MCP 服务器 (mcp_server/)
│   └── __init__.py       # FastMCP 服务器（LLM 集成）
│
├── 🔧 脚本 (scripts/)
│   ├── start_server.sh       # HTTP 服务器启动脚本
│   ├── start_mcp.sh        # MCP 服务器启动脚本
│   ├── start_server_simple.py # 简化启动脚本
│   └── client.py           # HTTP 测试客户端
│
├── 📚 文档
│   ├── README.md                    # 项目主文档
│   ├── README_IMAGE_UPLOADER.md   # 图像上传器文档
│   ├── SERVER_GUIDE.md             # HTTP 服务器指南
│   ├── TAILSCALE_GUIDE.md          # Tailscale 配置指南
│   ├── MCP_README.md              # MCP 服务器文档
│   ├── MCP_QUICKSTART.md          # MCP 快速开始
│   └── ARCHITECTURE.md            # 本文件
│
├── ⚙️ 配置
│   ├── pyproject.toml              # Python 项目配置
│   ├── .env                       # 环境变量（本地）
│   ├── .env-sample                 # 环境变量示例
│   └── uv.lock                    # 依赖锁文件
│
├── 📦 数据
│   ├── .crc/                      # 项目数据目录
│   │   ├── logs/                 # 日志文件
│   │   ├── state/                # 状态文件
│   │   ├── metadata/              # 元数据
│   │   └── output/               # 输出文件
│   ├── images/                     # 生成的图片
│   └── prompts/                    # 保存的提示词
│
└── 🔬 其他
    ├── .gitignore
    ├── comfyui_colab.ipynb
    └── ...
```

## 🎯 使用场景映射

### 场景 1：本地开发/日常使用

**方式**: CLI 命令

```bash
crc create --concept cell_membrane -p "添加荧光效果"
```

**特点**：
- ✅ 最直接的使用方式
- ✅ 完整的功能支持
- ✅ 适合交互式使用

### 场景 2：远程访问（Tailscale）

**方式**: HTTP 服务器

```bash
# 服务器端
./scripts/start_server_simple.py

# 客户端（通过 Tailscale）
curl http://100.100.100.1:8888/api/v1/concepts
```

**特点**：
- ✅ 通过 VPN 安全访问
- ✅ 适合远程团队协作
- ✅ 无需在每台机器安装

### 场景 3：AI 集成（Claude Desktop）

**方式**: MCP 服务器

```
Claude 对话中：
"帮我生成一张细胞膜图"

Claude 自动：
1. 调用 list_concepts 查看可用概念
2. 调用 create_image 创建任务
3. 调用 view_task 查看结果
```

**特点**：
- ✅ 深度上下文理解
- ✅ 自然语言交互
- ✅ LLM 可以自主规划任务

## 🔧 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **核心功能** | Python 3.13+ | 主要编程语言 |
| | Typer | CLI 框架 |
| | Requests | HTTP 客户端 |
| | Pillow | 图像处理 |
| **HTTP 服务器** | FastAPI | Web 框架 |
| | Uvicorn | ASGI 服务器 |
| | CORS | 跨域支持 |
| **MCP 服务器** | FastMCP | MCP 框架 |
| | Python types | 类型提示 |
| **网络** | Tailscale | 安全 VPN |
| | Karing | 网关（用户模式） |
| **包管理** | uv | 快速 Python 包管理器 |

## 🔒 安全考虑

### 1. API 密钥管理

```bash
# TTAPI API 密钥（图像生成必需）
export TTAPI_API_KEY="sk-xxx..."

# OpenAI API 密钥（概念生成可选）
export OPENAI_API_KEY="sk-xxx..."

# 服务器 API 密钥（可选）
export SERVER_API_KEY="your-secure-key"
```

### 2. 网络安全

- ✅ Tailscale 提供端到端加密
- ✅ 用户模式无需 root 权限
- ✅ Karing 网关处理路由

### 3. 访问控制

- 使用 `SERVER_API_KEY` 保护 HTTP 服务器
- 配置 Tailscale ACL 限制设备访问
- 定期审查连接的设备

## 🚀 扩展性

### 添加新 CLI 命令

1. 在 `cell_cover/commands/` 中创建新文件
2. 在 `cell_cover/cli.py` 中注册新命令
3. 更新 `ARCHITECTURE.md`

### 添加新的 HTTP 端点

1. 在 `server/api.py` 中添加新的 `@app.route` 装饰器
2. 更新 `SERVER_GUIDE.md`

### 添加新的 MCP 工具

1. 在 `mcp_server/__init__.py` 中添加 `@mcp.tool` 函数
2. 更新 `MCP_README.md`

## 📊 性能考虑

| 操作 | 预期时间 |
|------|----------|
| CLI 命令执行 | < 1s |
| HTTP API 调用 | < 2s（含网络） |
| MCP 工具调用 | < 3s（含协议开销） |
| 图像生成 | 10-60s（取决于 API） |

## 🔄 状态管理

### 任务状态流转

```
pending (提交中)
    ↓
in_progress (生成中)
    ↓
completed (已完成)
    ↓
failed (失败)
```

### 状态持久化

- **last_job.json**: 最近任务 ID（CRC_BASE_DIR/state/）
- **images_metadata.json**: 所有任务元数据（CRC_BASE_DIR/metadata/）
- **日志文件**: 详细执行日志（CRC_BASE_DIR/logs/）

## 🎓 总结

**Cell Cover Generator MCP** 采用三层架构设计：

1. **核心功能层** - 可重用的业务逻辑
2. **接口层** - 多种访问方式（CLI、HTTP、MCP）
3. **网络层** - 安全的远程访问（Tailscale）

这种设计实现了：
- ✅ 关注点分离
- ✅ 多接口支持
- ✅ 安全的网络访问
- ✅ AI 深度集成
- ✅ 灵活的扩展性

**关键优势**：
- 一套代码，多种使用方式
- 无缝集成到 Claude Desktop
- 通过 Tailscale 安全远程访问
- 保持 CLI 的直接性和高效性
