# Tailscale 服务器使用指南

## 概述

将 Cell Cover Generator 转换为 HTTP 服务器，通过 Tailscale 网络让其他电脑访问。

## 网络架构

```
┌─────────────────┐         Tailscale VPN          ┌─────────────────┐
│   客户端电脑     │ ◄──────────────────────────► │   服务器电脑     │
│   (任意位置）    │                            │   (运行此项目）   │
└─────────────────┘                            └─────────────────┘
```

**特点:**
- 使用 **用户模式** (User-space networking)
- 通过 **Karing 网关** 路由 Tailscale 流量
- 监听 **0.0.0.0:8888**，自动绑定 Tailscale 接口

## 快速开始

### 1. 服务器端设置

```bash
# 进入项目目录
cd /Users/jacobcy/Public/image-generator-mcp

# 初始化项目（如果还没有）
crc init

# 安装服务器依赖（如果尚未安装）
uv pip install fastapi uvicorn python-multipart

# 方式1：使用启动脚本（推荐）
./scripts/start_server.sh

# 方式2：使用简化启动脚本（备用）
python3 scripts/start_server_simple.py
```

服务器启动后，你会看到：
```
========================================
Cell Cover Generator HTTP Server
========================================

📋 配置信息:
   监听地址: 0.0.0.0:8888
   工作进程: 1
   项目路径: /path/to/project

========================================
🚀 启动服务器...

📱 API 文档:  http://0.0.0.0:8888/docs
❤️  健康检查:  http://0.0.0.0:8888/health

提示:
  1. 通过 Tailscale 访问使用 http://<tailscale-ip>:8888
  2. 使用 Ctrl+C 停止服务器
  3. 查看 .crc/logs/ 目录获取详细日志
```

### 2. 获取 Tailscale IP

在服务器电脑上运行：
```bash
tailscale ip -4
```

输出类似：`100.x.y.z`，这是你的 Tailscale IPv4 地址。

### 3. 客户端测试

在任意连接到同一 Tailscale 网络的电脑上：

```bash
# 安装依赖
pip install requests

# 测试连接
python scripts/client.py http://<tailscale-ip>:8888 --test
```

示例：
```bash
python scripts/client.py http://100.100.100.1:8888 --test
```

### 4. 使用客户端

```bash
# 交互模式
python scripts/client.py http://100.100.100.1:8888

# 命令示例
> health           # 健康检查
> concepts        # 列出概念
> tasks           # 列出任务
> create "实验室场景"  # 创建任务
> view abc-123     # 查看任务
> action abc-123 variation1  # 执行变体操作
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | API 信息 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger UI 文档 |
| `/api/v1/concepts` | GET | 列出创意概念 |
| `/api/v1/create` | POST | 创建图像任务 |
| `/api/v1/tasks` | GET | 列出任务 |
| `/api/v1/tasks/{id}` | GET | 查看任务详情 |
| `/api/v1/tasks/{id}/action` | POST | 执行操作 |
| `/api/v1/describe` | POST | 描述图像 |

## 配置选项

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_HOST` | `0.0.0.0` | 监听地址 |
| `SERVER_PORT` | `8888` | 监听端口 |
| `SERVER_WORKERS` | `1` | 工作进程数 |
| `SERVER_API_KEY` | `None` | API 密钥（可选） |

### 设置 API 密钥

```bash
# 服务器端
export SERVER_API_KEY="your-secure-key-here"
./scripts/start_server.sh

# 客户端
python scripts/client.py http://<ip>:8888 --api-key your-secure-key-here
```

## Python 代码示例

```python
from scripts.client import CellCoverClient

# 创建客户端
client = CellCoverClient("http://100.100.100.1:8888")

# 创建图像任务
result = client.create_image(
    prompt="实验室显微镜下的细胞结构",
    concept="cell_membrane",
    aspect_ratio="16:9",
    mode="relax"
)

print(f"任务已创建: {result['job_id']}")

# 查看任务
task = client.view_task(result['job_id'])
print(task['data'])
```

## 故障排除

### 无法连接服务器

1. **检查服务器是否运行**
   ```bash
   # 服务器端
   curl http://localhost:8888/health
   ```

2. **检查 Tailscale 连接**
   ```bash
   # 客户端和服务器端都要检查
   tailscale status

   # 确保两台设备在同一个 Tailnet 中
   ```

3. **检查防火墙**
   - macOS: 系统偏好设置 → 安全性与隐私 → 防火墙
   - 确保允许 Python 或端口 8888

### 端口冲突

如果 8888 端口被占用，可以修改：

```bash
export SERVER_PORT=9999
./scripts/start_server.sh
```

### API 调用失败

1. 检查 API 密钥配置
   ```bash
   # 服务器端
   echo $TTAPI_API_KEY

   # 确保已设置
   export TTAPI_API_KEY="your-key"
   ```

2. 查看服务器日志
   ```bash
   tail -f .crc/logs/server.log
   ```

## 安全建议

1. **使用 API 密钥** - 在生产环境中设置 `SERVER_API_KEY`
2. **限制访问** - 如果可能，使用 Tailscale ACL 限制访问
3. **使用 HTTPS** - 在生产环境中考虑添加 SSL/TLS
4. **定期更新** - 保持依赖库最新版本

## 生产部署

对于生产环境，建议：

1. 使用 `gunicorn` 或 `uvicorn` 的多进程模式
2. 配置 `supervisord` 或 `systemd` 守护进程
3. 使用 Nginx 作为反向代理
4. 配置日志轮转
5. 设置监控和告警

示例生产启动命令：
```bash
gunicorn server.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8888 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```
