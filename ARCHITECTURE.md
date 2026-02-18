# 项目架构说明

## 📖 项目概述

**Cell Cover Generator MCP** 是一个多层架构项目，提供通过多种方式访问 Cell Reports Medicine 杂志封面生成功能的能力。

```
┌─────────────────────────────────────────────────────────────────┐
│                     Cell Cover Generator                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐   ┌───────────────────┐
│  │  CLI 命令    │   │  MCP 服务器      │
│  │              │   │                  │
│  │ • create    │   │ • FastMCP         │
│  │ • generate   │   │ • Tools           │
│  │ • view      │   │ • Resources        │
│  │ • action    │   │                  │
│  │ ...         │   │                  │
│  └──────────────┘   └───────────────────┘
│         │                   │
└─────────┼───────────────────┘
          │                │
    ┌─────▼─────┐
    │   LLM     │
    │  (Claude)  │
    └───────────┘
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
├── 🔌 MCP 服务器 (mcp_server/)
│   └── __init__.py       # FastMCP 服务器（LLM 集成）
│
├── 🔧 脚本 (scripts/)
│   ├── start_mcp.sh        # MCP 服务器启动脚本
│   └── upload_image.sh     # 图片上传脚本
│
├── 📚 文档
│   ├── README.md                    # 项目主文档
│   ├── AGENTS.md                  # Agent 文档
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
| **MCP 服务器** | FastMCP | MCP 框架 |
| | Python types | 类型提示 |
| **包管理** | uv | 快速 Python 包管理器 |

## 🔒 安全考虑

### 1. API 密钥管理

```bash
# TTAPI API 密钥（图像生成必需）
export TTAPI_API_KEY="sk-xxx..."

# OpenAI API 密钥（概念生成可选）
export OPENAI_API_KEY="sk-xxx..."
```

## 🚀 扩展性

### 添加新 CLI 命令

1. 在 `cell_cover/commands/` 中创建新文件
2. 在 `cell_cover/cli.py` 中注册新命令
3. 更新 `ARCHITECTURE.md`

### 添加新的 MCP 工具

1. 在 `mcp_server/__init__.py` 中添加 `@mcp.tool` 函数
2. 更新 `README.md`

## 📊 性能考虑

| 操作 | 预期时间 |
|------|----------|
| CLI 命令执行 | < 1s |
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

**Cell Cover Generator MCP** 采用简洁的架构设计：

1. **核心功能层** - 可重用的业务逻辑
2. **MCP 接口层** - 为 LLM 提供的 standardized 接口
3. **CLI 接口层** - 为开发者提供的命令行工具

这种设计实现了：
- ✅ 关注点分离
- ✅ AI 深度集成
- ✅ 灵活的扩展性

**关键优势**：
- 无缝集成到 Claude Desktop
- 保持 CLI 的直接性和高效性
