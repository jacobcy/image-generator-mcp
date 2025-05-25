#!/bin/zsh

# Cell Cover Generator 安装脚本
# 这个脚本用于安装必要的依赖，并利用 uv 和 pyproject.toml 创建全局 'crc' 命令。

echo "开始安装 Cell Cover Generator ..."

# --- 辅助函数 ---
install_python() {
    echo "正在协助安装 Python..."

    # 检测操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "检测到 macOS 系统"
        if command -v brew &> /dev/null; then
            echo "使用 Homebrew 安装 Python 3.13..."
            brew install python@3.13
        else
            echo "未找到 Homebrew。请选择安装方式："
            echo "1. 安装 Homebrew 然后安装 Python: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "2. 从官网下载: https://www.python.org/downloads/"
            echo "3. 使用 pyenv: curl https://pyenv.run | bash"
            read -p "请选择 (1/2/3) 或按 Enter 跳过: " choice
            case $choice in
                1)
                    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                    brew install python@3.13
                    ;;
                2)
                    echo "请访问 https://www.python.org/downloads/ 下载并安装 Python 3.13+"
                    exit 1
                    ;;
                3)
                    curl https://pyenv.run | bash
                    echo "请重新启动终端并运行: pyenv install 3.13.0 && pyenv global 3.13.0"
                    exit 1
                    ;;
                *)
                    echo "跳过 Python 安装。请手动安装 Python 3.13+ 后重新运行此脚本。"
                    exit 1
                    ;;
            esac
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "检测到 Linux 系统"
        if command -v apt &> /dev/null; then
            echo "使用 apt 安装 Python 3.13..."
            sudo apt update
            sudo apt install -y python3.13 python3.13-venv python3.13-pip
        elif command -v yum &> /dev/null; then
            echo "使用 yum 安装 Python 3.13..."
            sudo yum install -y python3.13 python3.13-venv python3.13-pip
        else
            echo "请使用您的包管理器安装 Python 3.13+ 或访问 https://www.python.org/downloads/"
            exit 1
        fi
    else
        echo "不支持的操作系统。请手动安装 Python 3.13+ 后重新运行此脚本。"
        exit 1
    fi
}

install_uv() {
    echo "正在安装 uv 包管理器..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # 重新加载 shell 配置以使 uv 命令可用
    if [[ -f "$HOME/.cargo/env" ]]; then
        source "$HOME/.cargo/env"
    fi

    # 检查安装是否成功
    if ! command -v uv &> /dev/null; then
        echo "uv 安装失败。请手动安装后重新运行此脚本。"
        echo "安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    echo "uv 安装成功！"
}

# --- 前提检查和安装 ---
# 检查并安装 Python
echo "检查 Python 安装..."
if ! command -v python3 &> /dev/null; then
    echo "未找到 Python 3。"
    read -p "是否要自动安装 Python? (y/N): " install_py
    if [[ $install_py =~ ^[Yy]$ ]]; then
        install_python
    else
        echo "请先安装 Python 3.13+ 后重新运行此脚本。"
        exit 1
    fi
else
    # 检查 Python 版本
    PY_VERSION=$(python3 --version | cut -d' ' -f2)
    PY_MAJOR=$(echo $PY_VERSION | cut -d'.' -f1)
    PY_MINOR=$(echo $PY_VERSION | cut -d'.' -f2)

    if [[ $PY_MAJOR -lt 3 ]] || [[ $PY_MAJOR -eq 3 && $PY_MINOR -lt 13 ]]; then
        echo "找到 Python $PY_VERSION，但需要 Python 3.13+。"
        read -p "是否要安装更新的 Python 版本? (y/N): " upgrade_py
        if [[ $upgrade_py =~ ^[Yy]$ ]]; then
            install_python
        else
            echo "警告: 使用较旧的 Python 版本可能导致兼容性问题。"
        fi
    else
        echo "找到兼容的 Python: $PY_VERSION"
    fi
fi

# 检查并安装 uv
echo "检查 uv 包管理器..."
if ! command -v uv &> /dev/null; then
    echo "未找到 uv 包管理器。"
    read -p "是否要自动安装 uv? (Y/n): " install_uv_choice
    if [[ ! $install_uv_choice =~ ^[Nn]$ ]]; then
        install_uv
    else
        echo "请先安装 uv 包管理器后重新运行此脚本。"
        echo "安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
else
    echo "找到 uv 包管理器。"
fi

# --- 项目环境设置和安装 ---
# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "项目根目录: $PROJECT_ROOT"
cd "$PROJECT_ROOT" || exit 1

# 检查 pyproject.toml 文件
if [ ! -f "pyproject.toml" ]; then
    echo "错误：未找到 pyproject.toml 文件。请确保在正确的项目目录中运行此脚本。"
    exit 1
fi

echo "使用 uv 创建环境并安装项目依赖..."

# 方法1: 使用 uv sync (推荐，如果有 uv.lock 文件)
if [ -f "uv.lock" ]; then
    echo "找到 uv.lock 文件，使用 uv sync 同步环境..."
    uv sync
    if [ $? -ne 0 ]; then
        echo "错误：uv sync 失败。请检查 pyproject.toml 和网络连接。"
        exit 1
    fi
else
    # 方法2: 创建虚拟环境并安装依赖
    echo "创建虚拟环境..."
    uv venv
    if [ $? -ne 0 ]; then
        echo "错误：创建虚拟环境失败。"
        exit 1
    fi

    echo "安装项目依赖..."
    uv pip install -e .
    if [ $? -ne 0 ]; then
        echo "错误：安装项目依赖失败。请检查 pyproject.toml 和网络连接。"
        exit 1
    fi
fi

echo "环境设置完成！"

# --- 全局工具安装 ---
echo "使用 uv tool install 将 crc 命令安装到全局..."

# 使用 uv tool install 安装当前项目为全局工具
uv tool install .
if [ $? -ne 0 ]; then
    echo "警告：全局工具安装失败，尝试使用 --force 选项重新安装..."
    uv tool install --force .
    if [ $? -ne 0 ]; then
        echo "错误：全局工具安装失败。"
        echo "您仍然可以在项目环境中使用 'uv run crc' 命令。"
        GLOBAL_INSTALL_FAILED=true
    else
        echo "全局工具安装成功！"
        GLOBAL_INSTALL_FAILED=false
    fi
else
    echo "全局工具安装成功！"
    GLOBAL_INSTALL_FAILED=false
fi

# --- 验证安装 ---
echo ""
echo "验证安装..."

if [ "$GLOBAL_INSTALL_FAILED" = false ]; then
    # 测试全局 crc 命令
    if command -v crc &> /dev/null; then
        echo "✅ 全局 crc 命令安装成功！"
        echo "测试命令版本:"
        crc --help | head -3 2>/dev/null || echo "  (命令可用，但可能需要配置)"
    else
        echo "⚠️  全局 crc 命令未在 PATH 中找到。"
        echo "您可能需要重新启动终端或添加 uv 工具路径到 PATH。"
        echo "uv 工具通常安装在: ~/.local/bin/ 或 ~/.cargo/bin/"
    fi
else
    echo "⚠️  全局安装失败，但您仍可以使用项目环境中的命令。"
fi

echo ""
echo "=== 安装完成！==="
echo ""

if [ "$GLOBAL_INSTALL_FAILED" = false ]; then
    echo "🎉 Cell Cover Generator 已成功安装！"
    echo ""
    echo "使用方式："
    echo "  方式1 (推荐): 直接使用全局命令"
    echo "    crc create -c ca -var scientific --style focus"
    echo "    crc --help"
    echo ""
    echo "  方式2: 如果全局命令不可用，在项目目录中使用"
    echo "    cd $PROJECT_ROOT"
    echo "    uv run crc create -c ca -var scientific --style focus"
else
    echo "🔧 Cell Cover Generator 环境已设置完成！"
    echo ""
    echo "由于全局安装失败，请使用以下方式运行："
    echo "  cd $PROJECT_ROOT"
    echo "  uv run crc create -c ca -var scientific --style focus"
    echo "  uv run crc --help"
fi

echo ""
echo "更多使用示例："
echo "  crc create -c ca -var scientific --style focus"
echo "  crc list --limit 20"
echo "  crc view <job_id>"
echo "  crc --help"
echo ""

if [ "$GLOBAL_INSTALL_FAILED" = false ]; then
    echo "💡 提示: 如果 'crc' 命令不可用，请尝试："
    echo "  1. 重新启动终端"
    echo "  2. 或运行: source ~/.zshrc (或您的 shell 配置文件)"
    echo "  3. 或检查 PATH 中是否包含 uv 工具目录"
fi

echo ""
echo "安装日志已完成。享受使用 Cell Cover Generator！"

exit 0