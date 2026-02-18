#!/usr/bin/env python3
"""
简单服务器启动脚本 - 用于测试
"""
import os
import sys
import uvicorn

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 直接导入 server/api 模块
from server import api as server_module

if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8888"))

    print("=" * 60)
    print("Cell Cover Generator HTTP Server (简化版)")
    print("=" * 60)
    print(f"监听: http://{host}:{port}")
    print(f"文档: http://{host}:{port}/docs")
    print("")

    uvicorn.run(
        server_module.app,
        host=host,
        port=port,
        log_level="info"
    )
