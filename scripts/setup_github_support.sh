#!/bin/zsh
# 设置GitHub令牌的脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

# 检查是否已有.env文件
ENV_FILE=".env"

echo "===== GitHub令牌设置 ====="
echo "此脚本将帮助您设置GitHub个人访问令牌到.env文件中"
echo ""
echo "请访问 https://github.com/settings/tokens 生成个人访问令牌"
echo "确保选择至少包含'repo'权限"
echo ""

# 询问用户输入GitHub令牌
read -p "请输入您的GitHub个人访问令牌: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "错误：GitHub令牌不能为空"
    exit 1
fi

# 询问用户输入仓库名称
read -p "请输入您要用于存储图片的GitHub仓库名称 (默认: image-hosting): " REPO_NAME
REPO_NAME=${REPO_NAME:-image-hosting}

echo ""
echo "您需要确保已创建名为 $REPO_NAME 的公开仓库"
read -p "是否已创建该仓库? (y/n): " REPO_CREATED

if [[ "$REPO_CREATED" != "y" && "$REPO_CREATED" != "Y" ]]; then
    echo ""
    echo "请先创建仓库，步骤如下："
    echo "1. 访问 https://github.com/new"
    echo "2. 仓库名称设置为: $REPO_NAME"
    echo "3. 确保仓库为'Public'"
    echo "4. 初始化仓库（添加README）"
    echo "5. 创建完成后再运行此脚本"
    exit 1
fi

# 检查.env文件是否存在
if [ -f "$ENV_FILE" ]; then
    # 检查文件中是否已有GITHUB_TOKEN
    if grep -q "GITHUB_TOKEN=" "$ENV_FILE"; then
        # 替换现有的令牌
        sed -i '' "s/GITHUB_TOKEN=.*/GITHUB_TOKEN=$GITHUB_TOKEN/" "$ENV_FILE"
        echo "已更新.env文件中的GITHUB_TOKEN"
    else
        # 添加新的令牌
        echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> "$ENV_FILE"
        echo "已添加GITHUB_TOKEN到.env文件"
    fi
else
    # 创建新的.env文件
    echo "GITHUB_TOKEN=$GITHUB_TOKEN" > "$ENV_FILE"
    echo "已创建.env文件并添加GITHUB_TOKEN"
fi

echo ""
echo "设置完成！您现在可以使用upload_image.sh上传图片到GitHub了"
echo "示例: ./upload_image.sh upload -s github --repo $REPO_NAME ./images/example.png"