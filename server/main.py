"""
Cell Cover Generator HTTP Server - 主入口
"""
import os
import sys
import uvicorn
from contextlib import redirect_stdout, redirect_stderr
import logging
from io import StringIO

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.main import app, logger

if __name__ == "__main__":
    # 从环境变量或配置文件读取配置
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8888"))
    workers = int(os.getenv("SERVER_WORKERS", "1"))

    print("=" * 60)
    print("Cell Cover Generator HTTP Server")
    print("=" * 60)
    print(f"监听地址: {host}:{port}")
    print(f"工作进程: {workers}")
    print(f"项目路径: {project_root}")
    print("=" * 60)
    print("\n服务器启动中...")
    print(f"访问 API 文档: http://{host}:{port}/docs")
    print(f"健康检查: http://{host}:{port}/health")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 60)

    logger.info(f"启动服务器: http://{host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers,
        log_level="info"
    )
