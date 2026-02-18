# Tailscale 网络配置

## 项目场景
- **模式**: 用户模式 (User-space networking)
- **网关**: Karing 作为 Tailscale 路由网关
- **监听**: 0.0.0.0:8888（绑定所有接口，包括 Tailscale）

## 关键差异
| 模式 | 性能 | 权限 | 适用场景 |
|------|--------|--------|----------|
| 用户模式 | 较低（应用层） | 无需 root | Karing 网关、受限环境 |
| TUN 模式 | 高（内核层） | 需要 sudo | 高性能 VPN |

## 常用命令
```bash
tailscale up --auth-key=tskey-xxxxx    # 连接
tailscale status                            # 查看状态
tailscale ip -4                           # 获取 IPv4 地址
tailscale ping <name>                      # 测试连接
```

## 文档位置
- `/Users/jacobcy/Public/image-generator-mcp/TAILSCALE_GUIDE.md` - 完整使用指南
- `/Users/jacobcy/Public/image-generator-mcp/SERVER_GUIDE.md` - 服务器配置指南
