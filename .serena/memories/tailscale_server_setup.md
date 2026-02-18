# Tailscale 服务器项目配置

## 网络架构
- **模式**: 用户模式 (User-space networking)
- **网关**: Karing 充当 Tailscale 节点
- **监听地址**: 0.0.0.0 (绑定所有接口)
- **默认端口**: 8888

## 关键特性
1. HTTP REST API 封装现有 CLI 命令
2. 异步任务支持
3. 文件上传和下载
4. API 认证
5. Tailscale 网络兼容

## 目录结构
```
image-generator-mcp/
├── server/
│   ├── __init__.py
│   ├── main.py           # FastAPI 服务器主文件
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py      # API 路由
│   │   └── models.py      # Pydantic 模型
│   └── requirements.txt    # 服务器依赖
├── scripts/
│   └── start_server.sh   # 启动脚本
└── server_config.yaml     # 服务器配置
```
