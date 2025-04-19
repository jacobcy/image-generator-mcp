#!/bin/zsh
# 设置ImgBB API密钥的脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

# 检查是否已有.env文件
ENV_FILE=".env"

echo "===== ImgBB API密钥设置 ====="
echo "此脚本将帮助您设置ImgBB API密钥到.env文件中"
echo ""
echo "请访问 https://api.imgbb.com/ 注册并获取API密钥"
echo ""

# 询问用户输入API密钥
read -p "请输入您的ImgBB API密钥: " API_KEY

if [ -z "$API_KEY" ]; then
    echo "错误：API密钥不能为空"
    exit 1
fi

# 检查.env文件是否存在
if [ -f "$ENV_FILE" ]; then
    # 检查文件中是否已有IMGBB_API_KEY
    if grep -q "IMGBB_API_KEY=" "$ENV_FILE"; then
        # 替换现有的API密钥
        sed -i '' "s/IMGBB_API_KEY=.*/IMGBB_API_KEY=$API_KEY/" "$ENV_FILE"
        echo "已更新.env文件中的IMGBB_API_KEY"
    else
        # 添加新的API密钥
        echo "IMGBB_API_KEY=$API_KEY" >> "$ENV_FILE"
        echo "已添加IMGBB_API_KEY到.env文件"
    fi
else
    # 创建新的.env文件
    echo "IMGBB_API_KEY=$API_KEY" > "$ENV_FILE"
    echo "已创建.env文件并添加IMGBB_API_KEY"
fi

echo ""
echo "设置完成！您现在可以使用upload_image.sh上传图片了"
echo "示例: ./upload_image.sh upload ./images/example.png"