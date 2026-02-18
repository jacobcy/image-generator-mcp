# Tailscale 使用指南

## 📖 概述

Tailscale 是一个零信任网络安全平台，使用 WireGuard 创建安全加密网络，提供远程访问、VPN 功能和基础架构连接能力。

**你的场景特点：**
- ✅ 使用 **用户模式** (User-space networking)
- ✅ 通过 **Karing** 网关进行路由
- ✅ 无需 root 权限
- ✅ 适合应用层网络代理

---

## 🚀 安装

### macOS (推荐）

```bash
# 方式1: 使用 Homebrew（推荐）
brew install --cask tailscale

# 方式2: 从官网下载安装包
# 访问 https://tailscale.com/download
```

安装完成后，Tailscale 会自动启动并在菜单栏显示图标。

### Linux

```bash
# 下载安装脚本
curl -fsSL https://tailscale.com/install.sh | sh

# 启动 Tailscale
sudo tailscale up
```

### Windows

```powershell
# 从官网下载安装程序
# 访问 https://tailscale.com/download
# 或使用 PowerShell
irm https://tailscale.com/install.ps1 | iex
```

---

## 🔐 配置与连接

### 1. 获取认证密钥 (Auth Key)

访问 [Tailscale Admin Console](https://login.tailscale.com/admin/settings/keys)，创建新的 Auth Key：

```
tskey-auth-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2. 连接到 Tailnet

```bash
# 基本连接（交互式）
tailscale up

# 使用 Auth Key 连接（无交互，适合脚本）
tailscale up --auth-key=tskey-auth-xxxxx

# 从文件读取 Auth Key
tailscale up --auth-key=file:/path/to/authkey

# 设置自定义主机名
tailscale up --hostname=my-image-server --auth-key=tskey-xxxxx
```

**macOS 用户：** 首次连接可能需要授权：
1. 菜单栏点击 Tailscale 图标
2. 选择 "Log in"
3. 完成浏览器认证

---

## 📡 查看 IP 地址

连接成功后，可以查看你的 Tailscale IP：

```bash
# 查看 IPv4 地址
tailscale ip -4
# 输出：100.100.100.1

# 查看 IPv6 地址
tailscale ip -6
# 输出：fd7a:115c:a1e1:482:1001:0:0:1

# 查看所有地址
tailscale ip
```

**重要：**
- `100.x.x.x` 是分配的 Tailscale IPv4 地址
- 这个地址在所有连接到同一 Tailnet 的设备上可达

---

## 🔍 查看状态

```bash
# 基本状态
tailscale status

# 仅显示当前设备
tailscale status --self=true --peers=false

# 仅显示活跃的对等设备
tailscale status --active

# JSON 格式输出（便于脚本解析）
tailscale status --json

# 在浏览器中查看状态
tailscale status --web
# 然后访问 http://127.0.0.1:8384
```

**输出示例：**
```
100.100.100.1  my-image-server  user@example.com  macos  -
100.100.100.2  my-laptop       user@example.com  linux   active; direct 192.168.1.10:41641
```

---

## 🌐 测试连接

```bash
# Ping 其他设备（按主机名）
tailscale ping my-laptop

# Ping 其他设备（按 IP）
tailscale ping 100.100.100.2

# 持续 ping直到建立直连
tailscale ping --until-direct my-laptop

# 限制 ping 次数
tailscale ping -c 5 my-laptop

# 设置超时
tailscale ping --timeout=10s my-laptop

# TSMP ping（通过 WireGuard）
tailscale ping --tsmp my-laptop

# ICMP ping（通过 WireGuard）
tailscale ping --icmp my-laptop
```

**输出示例：**
```
pong from my-laptop (100.100.100.2) via DERP(nyc) in 45ms
pong from my-laptop (100.100.100.2) via 192.168.1.10:41641 in 2ms
```

---

## 🔧 Karing 网关配置

你使用 Karing 作为 Tailscale 网关，这属于 **用户模式网络** 场景。

### 用户模式 vs TUN 模式

| 特性 | 用户模式 (User-mode) | TUN 模式 (Kernel-mode) |
|------|---------------------|---------------------|
| **性能** | 较低（应用层代理） | 高（内核层） |
| **权限** | 无需 root | 需要 sudo/root |
| **兼容性** | 更好（所有平台） | 有限（需要内核支持） |
| **路由** | Karing 处理路由 | 内核路由表 |
| **适合** | 网关、代理、受限环境 | 高性能 VPN |

### 你的场景优势

1. **Karing 自动路由** - 不需要手动配置路由
2. **无需特殊权限** - 在受限环境中更安全
3. **应用层灵活性** - 更容易集成到现有系统
4. **自动重连** - Karing 会管理连接状态

### 使用服务器

由于 Karing 处理路由，你的 HTTP 服务器只需监听所有接口：

```python
# Python 示例
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "running"}

# 监听 0.0.0.0 会自动绑定到 Tailscale 接口
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
```

客户端访问：
```bash
# 使用 Tailscale IP 访问
curl http://100.100.100.1:8888/
```

---

## 🌐 高级配置

### 退出节点 (Exit Node)

如果需要通过 Tailscale 路由互联网流量：

```bash
# 广告为退出节点
tailscale up --advertise-exit-node

# 客户端使用退出节点
tailscale up --exit-node=100.100.100.1
```

### 子网路由 (Subnet Routes)

让本地网络可通过 Tailscale 访问：

```bash
# 广告本地子网
tailscale up --advertise-routes=10.0.0.0/8,192.168.1.0/24

# 接受其他设备的路由
tailscale up --accept-routes
```

### SSH 访问

```bash
# 在服务器上启用 SSH
tailscale up --ssh

# 从客户端通过 Tailscale 连接 SSH
ssh user@my-server
# 或使用 IP
ssh user@100.100.100.1
```

### ACL 标签

```bash
# 广告标签（用于 ACL 策略）
tailscale up --advertise-tags=tag:server,tag:prod
```

---

## 📝 管理 ACL (Access Control Lists)

ACL 用于控制设备间的访问权限。

### ACL 示例

```json
// tailscale/acl.json
{
  "groups": {
    "group:admin": ["user@example.com"],
    "group:developer": ["dev@example.com"]
  },
  "acls": [
    // 允许 admin 访问所有设备
    {
      "action": "accept",
      "src": ["group:admin"],
      "dst": ["*"]
    },
    // 允许 developer 访问服务器标签的设备
    {
      "action": "accept",
      "src": ["group:developer"],
      "dst": ["tag:server"]
    },
    // 拒绝其他所有访问
    {
      "action": "reject",
      "src": ["*"],
      "dst": ["*"]
    }
  ]
}
```

---

## 🔧 故障排除

### 无法连接

```bash
# 检查 Tailscale 状态
tailscale status

# 重启 Tailscale
macOS: 菜单栏 → 停止并启动
Linux: sudo systemctl restart tailscaled
Windows: 服务管理器 → 重启 Tailscale

# 查看日志
macOS: 菜单栏 → Open Logs
Linux: sudo journalctl -u tailscaled
```

### 无法访问服务

```bash
# 1. 检查服务器是否监听
# 服务器端
netstat -an | grep 8888

# 2. 测试本地访问
curl http://localhost:8888/health

# 3. 测试 Tailscale 连接
tailscale ping <server-name>

# 4. 检查防火墙
# macOS: 系统偏好设置 → 安全性与隐私
# Linux: sudo iptables -L
```

### 路由问题

如果 Karing 路由有问题：

```bash
# 检查 Karing 状态（取决于具体实现）
# 通常 Karing 会处理路由，但可以检查：

# 测试直接连接
ping <server-ip>

# 检查 Tailscale 状态
tailscale status --json
```

---

## 📚 完整使用流程

### 场景：远程访问 Cell Cover Generator

#### 1. 服务器端设置

```bash
# 服务器电脑（运行服务器的设备）

# 确保 Tailscale 运行
tailscale status

# 获取 Tailscale IP
SERVER_IP=$(tailscale ip -4)
echo "Server Tailscale IP: $SERVER_IP"

# 启动你的服务器
cd /path/to/image-generator-mcp
python3 scripts/start_server_simple.py
```

#### 2. 客户端访问

```bash
# 任意连接到同一 Tailnet 的电脑

# 替换 <server-ip> 为实际 IP
curl http://<server-ip>:8888/health

# 或使用 Python 客户端
python3 scripts/client.py http://<server-ip>:8888 --test
```

#### 3. 持续使用

```bash
# 交互式使用
python3 scripts/client.py http://<server-ip>:8888

> health        # 健康检查
> concepts      # 列出概念
> create "提示词"  # 创建任务
```

---

## 🔐 安全最佳实践

1. **使用 Auth Key** - 不要重复使用 Auth Key
2. **配置 ACL** - 限制设备间访问权限
3. **定期审查** - 查看 Admin Console 中连接的设备
4. **使用标签** - 通过 ACL 标签简化管理
5. **监控日志** - 注意可疑连接活动
6. **更新密钥** - 定期轮换 Auth Key

---

## 📖 参考资源

- [Tailscale 官方文档](https://tailscale.com/kb/)
- [Tailscale GitHub](https://github.com/tailscale/tailscale)
- [Tailscale API 文档](https://github.com/tailscale/tailscale/blob/main/api.md)
- [WireGuard 文档](https://www.wireguard.com/)
- [Karing 文档](https://github.com/your/karing-repo) # 替换为实际链接

---

## 💡 常用命令速查表

| 命令 | 说明 |
|------|------|
| `tailscale up` | 连接到 Tailnet |
| `tailscale status` | 查看连接状态 |
| `tailscale ip -4` | 获取 IPv4 地址 |
| `tailscale ping <name>` | 测试到其他设备的连接 |
| `tailscale down` | 断开连接 |
| `tailscale up --ssh` | 启用 SSH 访问 |
| `tailscale up --advertise-exit-node` | 配置为退出节点 |

---

**Karing 用户模式配置完成！** 你的服务器现在可以通过 Tailscale 网络访问。记得检查 `SERVER_GUIDE.md` 了解如何测试和使用服务器。
