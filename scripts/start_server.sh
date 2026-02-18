#!/bin/bash
# Cell Cover Generator HTTP Server 启动脚本

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cell Cover Generator HTTP Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查是否已初始化
if [ ! -d ".crc" ]; then
    echo -e "${YELLOW}⚠️  项目未初始化，正在初始化...${NC}"
    python -m cell_cover init
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}❌ 初始化失败，请检查错误${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ 初始化完成${NC}"
    echo ""
fi

# 设置环境变量（可修改）
export SERVER_HOST="${SERVER_HOST:-0.0.0.0}"
export SERVER_PORT="${SERVER_PORT:-8888}"
export SERVER_WORKERS="${SERVER_WORKERS:-1}"

# 可选：设置 API 密钥
# export SERVER_API_KEY="your-secure-api-key-here"

echo -e "${GREEN}📋 配置信息:${NC}"
echo -e "   监听地址: ${BLUE}${SERVER_HOST}:${SERVER_PORT}${NC}"
echo -e "   工作进程: ${BLUE}${SERVER_WORKERS}${NC}"
echo -e "   项目路径: ${BLUE}${PROJECT_ROOT}${NC}"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🚀 启动服务器...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}📱 API 文档:${NC}  http://${SERVER_HOST}:${SERVER_PORT}/docs"
echo -e "${GREEN}❤️  健康检查:${NC}  http://${SERVER_HOST}:${SERVER_PORT}/health"
echo ""
echo -e "${YELLOW}提示:${NC}"
echo -e "  1. 通过 Tailscale 访问使用 http://<tailscale-ip>:8888"
echo -e "  2. 使用 Ctrl+C 停止服务器"
echo -e "  3. 查看 .crc/logs/ 目录获取详细日志"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""

# 启动服务器
python -m server.api
