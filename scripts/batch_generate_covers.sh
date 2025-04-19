#!/bin/zsh

# 一键生成脚本：为每个概念生成多种变体和风格组合的封面
# 作者：[您的名字或Heidi]
# 日期：$(date +%Y-%m-%d)
#
# **重要：此脚本必须从项目根目录 (paper/) 执行**
# 例如: cd /path/to/paper && ./cell_cover/batch_generate_covers.sh

# --- 配置 ---
# 配置文件相对于项目根目录的路径
CONFIG_FILE="cell_cover/prompts_config.json"
# Python 模块路径
MODULE_PATH="cell_cover.generate_cover"

# 错误计数器上限
MAX_ERRORS=5

# 每次调用生成脚本后的等待时间（秒），防止API调用过于频繁
# SLEEP_DURATION=15 # 改为随机延迟

# --- 变量初始化 ---
error_count=0

# --- 前提检查 ---
echo "检查 jq 是否已安装..."
if ! command -v jq &> /dev/null
then
    echo "错误：需要 jq 来解析配置文件。请先安装 jq。"
    echo "(例如: brew install jq 或 sudo apt-get install jq)"
    exit 1
fi
echo "jq 已找到。"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误：配置文件未找到于 $CONFIG_FILE (请确保您在项目根目录运行此脚本)"
    exit 1
fi


echo "配置文件: $CONFIG_FILE"
echo "Python模块: $MODULE_PATH"
echo "调用间隔: 随机 (61-180秒)"
echo "---当前工作目录: $(pwd) ---"

# --- 主要逻辑 ---

# 使用 jq 获取所有概念的 key
concept_keys=$(jq -r '.concepts | keys[]' "$CONFIG_FILE")

if [ -z "$concept_keys" ]; then
    echo "错误：无法从配置文件中读取概念列表。"
    exit 1
fi

echo "将为以下概念生成图像组合："
echo $concept_keys
echo "---"

# 循环遍历每个概念 (使用 while read 确保正确处理每个 key)
echo "$concept_keys" | while IFS= read -r concept; do
    # 跳过空行
    if [ -z "$concept" ]; then
        continue
    fi

    # --- 添加跳过 ca 的逻辑 ---
    if [ "$concept" = "ca" ]; then
        echo "根据要求，跳过概念 'ca'..."
        continue
    fi
    # --- 结束跳过逻辑 ---

    echo "处理概念: $concept ..."

    # --- 为每个概念定义要组合的变体和风格 --- #
    # (根据 Cell 编辑视角选择，旨在提供对比)
    var1=""
    var2=""
    style1=""
    style2=""

    case "$concept" in
        ca) # 仍然定义，但会被上面的 if 跳过
            var1="scientific"
            var2="dramatic"
            style1="focus"
            style2="illustration"
            ;;
        ca2)
            var1="detailed"
            var2="dramatic"
            style1="electron_microscope"
            style2="palette_cool" # 更新：使用冷色调对比
            ;;
        ca3)
            var1="network"
            var2="depth"
            style1="cinematic"
            style2="dark_bg" # 保持
            ;;
        cb)
            var1="abstract"
            var2="dynamic"
            style1="focus"
            style2="palette_warm" # 更新：使用暖色调对比
            ;;
        cb2)
            var1="fluid"
            var2="wave"
            style1="dark_bg"
            style2="photorealistic" # 保持
            ;;
        cb3)
            var1="data"
            var2="fractal"
            style1="palette_bw_gold" # 更新：使用黑白金对比
            style2="cinematic"
            ;;
        *)
            echo "警告：概念 '$concept' 没有预定义的变体/风格组合，将跳过。"
            continue
            ;;
    esac

    echo "  选择的组合:"
    echo "    Variation 1: $var1"
    echo "    Variation 2: $var2"
    echo "    Style 1    : $style1"
    echo "    Style 2    : $style2"

    # --- 构建并执行命令 (每个概念生成 2 个组合) --- #
    commands_to_run=()
    # 组合 1: Var1 + Style1
    commands_to_run+=("python -m $MODULE_PATH create -c $concept -var "$var1" --style "$style1"")
    # 组合 2: Var2 + Style2
    commands_to_run+=("python -m $MODULE_PATH create -c $concept -var "$var2" --style "$style2"")

    for cmd in "${commands_to_run[@]}"; do
        echo "\n  即将执行: $cmd"
        # 实际执行命令
        eval $cmd
        exit_code=$?
        
        # 检查上一个命令的退出状态
        if [ $exit_code -ne 0 ]; then
            error_count=$((error_count + 1))
            echo "  警告：上一个命令执行失败 (退出码 $exit_code)。当前累计错误次数: $error_count / $MAX_ERRORS"
            
            # 检查是否达到错误上限
            if [ $error_count -ge $MAX_ERRORS ]; then
                echo "错误：累计错误次数达到上限 ($MAX_ERRORS)，脚本终止。请检查日志和API服务状态。"
                exit 1
            fi
        fi

        # 计算随机延迟时间 (61-180秒)
        random_sleep=$(( (RANDOM % 120) + 61 ))
        echo "  等待 ${random_sleep} 秒..."
        sleep $random_sleep
    done

    echo "概念 $concept 处理完毕。"
    echo "---"
done # End of while read loop

echo "所有概念处理完成！请检查 images 和 metadata 目录。"
exit 0 