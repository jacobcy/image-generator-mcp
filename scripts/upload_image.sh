#!/bin/zsh
# 图片上传脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.." # Assuming script is in scripts/ folder
cd "$SCRIPT_DIR" || exit 1

# --- Argument Check ---
if [ "$#" -eq 0 ]; then
    echo "错误：请提供图片文件路径作为参数。"
    echo "用法: $0 <image_path>"
    exit 1
fi
# --- End Argument Check ---

# 检查Python环境
if [ -d ".venv" ]; then
    # 激活虚拟环境
    source .venv/bin/activate
fi

# 检查依赖
if ! python -c "import requests" &> /dev/null; then
    echo "正在安装必要的依赖..."
    uv pip install requests
fi

# 执行上传命令 - 修改为调用 process_cref_image
python -c "
import sys
import os
from cell_cover.utils.image_uploader import process_cref_image
from cell_cover.utils.log import setup_logging # Assuming setup_logging exists

# Get image path argument (already checked in shell)
image_path = sys.argv[1]

# Setup logger - Use project root passed from shell
# Note: setup_logging needs to be robust enough or adjusted if this path isn't right
logger = setup_logging('$PROJECT_ROOT', verbose=False) # Pass PROJECT_ROOT from shell

# Call processing function
image_url = process_cref_image(logger, image_path)

# Output result
if image_url:
    print(image_url)
else:
    print('错误：图片上传失败或未返回URL。', file=sys.stderr)
    sys.exit(1)
" "$@" # Pass arguments to Python script

# 如果激活了虚拟环境，则退出
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi