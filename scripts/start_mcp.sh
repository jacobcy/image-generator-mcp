#!/bin/bash
# Cell Cover Generator MCP Server 启动脚本

# 需色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cell Cover Generator MCP Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  uv 未安装${NC}"
    echo -e "${YELLOW}安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓ uv 已安装${NC}"

# 检查初始化
if [ ! -d ".crc" ]; then
    echo -e "${YELLOW}⚠️  项目未初始化${NC}"
    echo -e "${YELLOW}运行命令: uv run crc init${NC}"
    echo ""
    read -p "是否现在初始化? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uv run crc init
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🚀 启动 MCP 服务器...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}使用方法：${NC}"
echo -e "  1. Claude Desktop: 在 Settings → Developer → MCP Servers 中配置"
echo -e "  2. 命令行: uv run mcp-server"
echo ""
echo -e "${YELLOW}提示:${NC}"
echo -e "  • 确保已设置 TTAPI_API_KEY 环境变量"
echo -e "  • 查看 README.md 了解详细配置说明"
echo -e "  • 使用 Ctrl+C 停止服务器"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""

# 启动 MCP 服务器
uv run mcp-server
