#!/bin/zsh

# Cell Cover Generator 安装脚本
# 这个脚本用于安装必要的依赖，并利用 pyproject.toml 创建全局 'crc' 命令。

echo "开始安装 Cell Cover Generator ..."

# --- 前提检查 ---
# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python 3。请先安装Python 3。"
    exit 1
fi
PY_VERSION=$(python3 --version)
echo "找到 Python: $PY_VERSION"

# 检查uv
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到uv。请先安装uv包管理器。"
    echo "可以通过以下命令安装: curl -sSf https://install.ultraviolet.rs | sh"
    exit 1
fi
echo "找到 uv 包管理器。"

# --- 安装项目和依赖 --- #
# 获取脚本所在目录的上级目录 (假定脚本在 'scripts' 子目录中)
# 或者直接使用 pwd 如果脚本就是在项目根目录运行
PROJECT_ROOT=$(pwd)
# 切换到项目根目录以确保 pyproject.toml 路径正确
cd "$PROJECT_ROOT" || exit 1

echo "使用 uv 安装项目及其依赖 (来自 pyproject.toml)..."
if [ -f "pyproject.toml" ]; then
    # 使用 'uv pip install .' 安装当前项目
    # 这会自动读取 pyproject.toml, 安装依赖，并创建 [project.scripts] 中定义的命令
    uv pip install .
    if [ $? -ne 0 ]; then
        echo "错误：项目安装失败。请检查 pyproject.toml 和网络连接。"
        exit 1
    fi
else
    echo "错误：未找到 pyproject.toml 文件。无法安装项目。"
    exit 1
fi

# --- 移除旧的 crc 命令创建逻辑 --- #
# INSTALL_DIR="$HOME/.local/bin"
# CRC_CMD_PATH="$INSTALL_DIR/crc"
# echo "准备创建全局 'crc' 命令..."
# mkdir -p "$INSTALL_DIR"
# cat > "$CRC_CMD_PATH" <<EOF
# ... (removed content) ...
# EOF
# chmod +x "$CRC_CMD_PATH"
# echo "'crc' 命令已创建于 $CRC_CMD_PATH"

# --- 移除旧的 PATH 检查逻辑 --- #
# if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
#    echo ""
#    echo "警告：目录 '$INSTALL_DIR' 不在您的 PATH 环境变量中。"
#    echo "为了能直接运行 'crc' 命令，您需要将它添加到 PATH。"
#    echo "您可以将以下行添加到您的 shell 配置文件 (~/.zshrc, ~/.bashrc, ~/.bash_profile 等) 中:"
#    echo ""
#    echo "  export PATH="$INSTALL_DIR:$PATH""
#    echo ""
#    echo "添加后，请重新打开终端或运行 'source ~/.your_shell_config_file'。"
# fi

# --- 清理旧的执行权限和说明 --- #
# (可选) 移除旧脚本的执行权限
# chmod -x "$PROJECT_ROOT/cell_cover/generate_cover.py"
# chmod -x "$PROJECT_ROOT/cell_cover/fetch_job_status.py"

echo ""
echo "安装完成！"
echo "现在您应该可以使用 'crc' 命令了。"
echo "如果命令未找到，请确保 Python 环境的可执行路径已添加到您的系统 PATH 中。"
echo "(通常在虚拟环境中会自动处理，全局安装可能需要手动配置 PATH)"
echo ""
echo "示例用法:"
echo "  crc create -c ca -var scientific --style focus"
# echo "  crc generate -p "A stunning image of cells""
# echo "  crc list --limit 20"
# echo "  crc view <job_id>"
# echo "  crc restore --limit 50"
# echo "  crc help"

exit 0