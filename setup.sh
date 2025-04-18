#!/bin/zsh

# Cell Cover Generator 安装脚本
# 这个脚本用于安装必要的依赖并设置环境

echo "开始安装 Cell Cover Generator 依赖..."

# 检查Python是否已安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python 3。请先安装Python 3。"
    exit 1
fi

# 检查uv是否已安装
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到uv。请先安装uv包管理器。"
    echo "可以通过以下命令安装: curl -sSf https://install.ultraviolet.rs | sh"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR"

# 安装依赖
echo "使用uv安装Python依赖..."
uv pip install -r requirements.txt

# 设置执行权限
echo "设置脚本执行权限..."
chmod +x "$SCRIPT_DIR/cell_cover/generate_cover.py"
chmod +x "$SCRIPT_DIR/cell_cover/generate_cover.sh"

# 创建输出目录
echo "创建输出目录..."
mkdir -p "$SCRIPT_DIR/cell_cover/outputs"

echo "安装完成！"
echo ""
echo "使用方法:"
echo "  cd $SCRIPT_DIR/cell_cover"
echo "  ./generate_cover.sh help"