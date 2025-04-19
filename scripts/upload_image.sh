#!/bin/zsh
# 图片上传脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

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

# 执行上传命令
python -c "from cell_cover.utils.image_uploader import main; main()" "$@"

# 如果激活了虚拟环境，则退出
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi