#!/bin/zsh

# Cell Cover Generator 安装脚本
# 这个脚本用于安装必要的依赖，并创建一个全局 'crc' 命令来简化使用。

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

# --- 安装依赖 ---
# 获取脚本所在目录 (项目根目录)
PROJECT_ROOT=$(pwd)
# 切换到项目根目录以确保 requirements.txt 路径正确
cd "$PROJECT_ROOT" || exit 1

echo "使用uv安装Python依赖 (来自 requirements.txt)..."
if [ -f "requirements.txt" ]; then
    uv pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误：依赖安装失败。请检查 requirements.txt 和网络连接。"
        exit 1
    fi
else
    echo "警告：未找到 requirements.txt 文件。跳过依赖安装。"
fi

# --- 创建 crc 命令 --- #
INSTALL_DIR="$HOME/.local/bin"
CRC_CMD_PATH="$INSTALL_DIR/crc"

echo "准备创建全局 'crc' 命令..."
# 创建安装目录（如果不存在）
mkdir -p "$INSTALL_DIR"

# 生成 crc 脚本内容
# 注意: 使用 'heredoc' (<<EOF) 来方便地写入多行脚本内容
# 将 PROJECT_ROOT 的值嵌入到生成的脚本中
cat > "$CRC_CMD_PATH" <<EOF
#!/bin/zsh

# Cell Cover Generator - Wrapper Command ('crc')
# 由 setup.sh 自动生成

# --- 调试信息 ---
echo "Debug CRC: Received arguments: [\$@]"

# --- 项目根目录 (路径由 setup.sh 嵌入) ---
# PROJECT_ROOT="..." # 移除内部变量赋值

# --- 检查项目根目录是否存在 ---
# 直接在 cd 命令中使用路径
# if [ ! -d "$PROJECT_ROOT" ]; then ... # 移除检查，让 cd 失败即可

# --- 存储原始工作目录 ---
ORIGINAL_CWD=\$(pwd)

# --- 切换到项目根目录执行 ---
# 直接嵌入路径，并确保引号被正确写入 crc 文件
cd "${PROJECT_ROOT}" || exit 1

# --- 根据第一个参数决定执行哪个模块 ---
COMMAND="\$1"
echo "Debug CRC: COMMAND variable: [\$COMMAND]"
# if [ \$# -gt 0 ]; then
#   shift # 移除命令参数，保留后续选项
# fi

case "\$COMMAND" in
  create|generate|variations|recreate)
    echo "Debug CRC: Matched create/generate/variations/recreate branch"
    python3 -m cell_cover.generate_cover "\$@"
    ;;
  list|view|restore|upscale|variation|reroll|seed)
    echo "Debug CRC: Matched list/view/restore/upscale/variation/reroll/seed branch"
    python3 -m cell_cover.fetch_job_status "\$@"
    ;;
  help|--help|-h|'') # 处理帮助或无命令情况
    echo "Debug CRC: Matched help branch"
    echo "用法: crc <命令> [选项]"
    echo ""
    echo "可用命令:"
    echo "  --- Generation ---"
    echo "  create        基于概念/变体创建封面图像。"
    echo "  generate      基于自由格式提示词生成图像。"
    echo "  recreate      使用存储的 Prompt 和 Seed 重新生成图像 (用法: recreate <标识符>)"
    echo "  variations    列出指定概念的所有变体。"
    echo "  --- Management & Info ---"
    echo "  list          列出 TTAPI 历史任务。"
    echo "  view          查看指定 Job ID 的历史任务详情。"
    echo "  seed          获取指定任务的 Seed (用法: seed <标识符>)"
    echo "  restore       从 TTAPI 历史记录恢复本地元数据。"
    echo "  --- Actions ---"
    echo "  upscale       放大指定原始任务的图像 (用法: upscale <标识符> <1-4>)"
    echo ""
    echo "  <标识符> 可以是 6位Job ID前缀, 完整Job ID, 或初始生成的图像文件名 (无需 .png 后缀)。"
    echo ""
    echo "运行 'crc <命令> --help' 获取特定命令的帮助。"
    ;;
  *)
    echo "Debug CRC: Matched wildcard branch (*)"
    echo "错误: 未知命令 '\$COMMAND'"
    # 显示两个模块的帮助信息
    echo """'generate_cover' 模块帮助:"""
    python3 -m cell_cover.generate_cover --help >&2
    echo """'fetch_job_status' 模块帮助:"""
    python3 -m cell_cover.fetch_job_status --help >&2
    # 切换回原始目录
    cd "\$ORIGINAL_CWD"
    exit 1
    ;;
esac

# --- 获取 Python 脚本的退出码 --- #
EXIT_CODE=\$?
echo "Debug CRC: Python script exited with code: [\$EXIT_CODE]"

# --- 切换回原始工作目录 --- #
cd "\$ORIGINAL_CWD"

# --- 使用原始退出码退出包装脚本 --- #
exit \$EXIT_CODE

EOF
# EOF 必须单独一行且前面不能有空格

# --- 设置执行权限 --- #
chmod +x "$CRC_CMD_PATH"
if [ $? -ne 0 ]; then
    echo "错误：无法为 $CRC_CMD_PATH 设置执行权限。"
    # 可以尝试提示用户使用 sudo，但更安全的方式是让用户自己处理
    echo "请尝试手动执行: chmod +x $CRC_CMD_PATH"
    exit 1
fi
echo "'crc' 命令已创建于 $CRC_CMD_PATH"

# --- 检查 PATH --- #
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "警告：目录 '$INSTALL_DIR' 不在您的 PATH 环境变量中。"
    echo "为了能直接运行 'crc' 命令，您需要将它添加到 PATH。"
    echo "您可以将以下行添加到您的 shell 配置文件 (~/.zshrc, ~/.bashrc, ~/.bash_profile 等) 中:"
    echo ""
    echo "  export PATH=\"$INSTALL_DIR:$PATH\""
    echo ""
    echo "添加后，请重新打开终端或运行 'source ~/.your_shell_config_file'。"
fi

# --- 清理旧的执行权限和说明 --- #
# (可选) 移除旧脚本的执行权限，因为不再推荐直接运行
# chmod -x "$PROJECT_ROOT/cell_cover/generate_cover.py"
# chmod -x "$PROJECT_ROOT/cell_cover/generate_cover.sh" # 如果 generate_cover.sh 不再需要
# chmod -x "$PROJECT_ROOT/cell_cover/fetch_job_status.py"

echo ""
echo "安装完成！"
echo "现在您应该可以使用 'crc' 命令了 (如果 $INSTALL_DIR 在 PATH 中)。"
echo ""
echo "示例用法:"
echo "  crc create -c ca -var scientific --style focus"
# echo "  crc generate -p \"A stunning image of cells\""
# echo "  crc list --limit 20"
# echo "  crc view <job_id>"
# echo "  crc restore --limit 50"
# echo "  crc help"

exit 0