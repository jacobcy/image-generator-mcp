#!/bin/zsh

# 一键生成脚本：为匹配模式的概念生成随机变体/风格组合的封面
# 作者：[您的名字或Heidi]
# 日期：$(date +%Y-%m-%d)
#
# **重要：此脚本必须从项目根目录执行**
# 例如: cd /path/to/project/root && ./scripts/batch_generate_covers.sh <pattern>
# 生成的图片将保存在当前项目目录下的 ./images/{concept}/ 子目录中

# --- 配置 ---
# 配置文件路径 (全局配置文件)
CONFIG_FILE="$HOME/.crc/prompts_config.json"
# Python 模块路径 (使用 crc 命令简化)
# MODULE_PATH="cell_cover.generate_cover"
CRC_COMMAND="crc" # 使用 crc 命令

# 错误计数器上限
MAX_ERRORS=5

# --- 变量初始化 ---
error_count=0
filter_pattern="$1" # 获取第一个参数作为过滤模式

# --- 函数定义 ---
usage() {
    echo "用法: $0 <过滤模式>"
    echo "  <过滤模式>: 用于匹配概念键的模式 (例如 'c*', 'cb*', 'ca[23]')。"
    echo "             使用 '**' 匹配所有概念。"
    echo "示例:"
    echo "  $0 'c*'      # 处理所有以 'c' 开头的概念"
    echo "  $0 '**'      # 处理所有概念"
    exit 1
}

# --- 前提检查 ---

# 检查是否提供了参数
if [ -z "$filter_pattern" ]; then
    echo "错误：未提供过滤模式。"
    usage
fi

echo "检查 jq 是否已安装..."
if ! command -v jq &> /dev/null
then
    echo "错误：需要 jq 来解析配置文件。请先安装 jq。"
    echo "(例如: brew install jq 或 sudo apt-get install jq)"
    exit 1
fi
echo "jq 已找到。"

echo "检查 crc 命令是否可用..."
if ! command -v $CRC_COMMAND &> /dev/null
then
    echo "错误：'$CRC_COMMAND' 命令未找到。请确保项目已正确安装并通过 'uv pip install .' 创建了命令。"
    exit 1
fi
echo "'$CRC_COMMAND' 命令已找到。"


if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误：配置文件未找到于 $CONFIG_FILE"
    echo "请确保已运行 'crc init' 初始化系统，或检查 ~/.crc/ 目录是否存在"
    exit 1
fi

echo "配置文件: $CONFIG_FILE"
echo "过滤模式: $filter_pattern"
echo "调用间隔: 随机 (61-180秒)"
echo "---当前工作目录: $(pwd) ---"

# --- 获取概念和风格列表 ---

# 获取所有概念的 key
all_concept_keys=$(jq -r '.concepts | keys[]' "$CONFIG_FILE")
if [ -z "$all_concept_keys" ]; then
    echo "错误：无法从配置文件中读取概念列表。"
    exit 1
fi

# 获取所有全局风格的 key，存储到 Zsh 数组
local -a global_styles_list
while IFS= read -r style; do
    if [[ -n "$style" ]]; then # 跳过空行
        global_styles_list+=("$style")
    fi
done < <(jq -r '.global_styles | keys[]' "$CONFIG_FILE")

if [ ${#global_styles_list[@]} -eq 0 ]; then
    echo "警告：未在配置文件中找到全局风格。"
fi
echo "找到 ${#global_styles_list[@]} 个全局风格。"


# --- 主要逻辑 ---

matched_concepts=0
# 循环遍历每个概念，根据模式进行过滤
echo "$all_concept_keys" | while IFS= read -r concept; do
    # 跳过空行
    if [ -z "$concept" ]; then
        continue
    fi

    # 检查是否匹配模式 (使用 Zsh 的 [[ ]] 和模式匹配)
    # 或者如果模式是 '**' 则始终匹配
    if [[ "$filter_pattern" == "**" || "$concept" == $filter_pattern ]]; then
        echo "匹配概念: $concept ..."
        matched_concepts=$((matched_concepts + 1))

        # --- 获取此概念的变体 ---
        local -a concept_variations_list
        while IFS= read -r variation; do
            if [[ -n "$variation" ]]; then # 跳过空行
                concept_variations_list+=("$variation")
            fi
        done < <(jq -r --arg concept "$concept" '.concepts[$concept].variations | keys[] // empty' "$CONFIG_FILE") # 使用 // empty 处理 null

        # --- 随机选择变体 (如果存在) ---
        local random_var=""
        if [ ${#concept_variations_list[@]} -gt 0 ]; then
            random_var_index=$(( (RANDOM % ${#concept_variations_list[@]}) + 1 )) # Zsh array index starts at 1
            random_var=${concept_variations_list[$random_var_index]}
            echo "  随机选择变体: $random_var"
        else
            echo "  概念 '$concept' 没有定义变体，将不使用 -var。"
        fi

        # --- 随机选择全局风格 (如果存在) ---
        local random_style=""
        if [ ${#global_styles_list[@]} -gt 0 ]; then
            random_style_index=$(( (RANDOM % ${#global_styles_list[@]}) + 1 ))
            random_style=${global_styles_list[$random_style_index]}
            echo "  随机选择风格: $random_style"
        else
             echo "  没有可用的全局风格，将不使用 --style。"
        fi

        # --- 构建命令 ---
        # 使用 crc 命令替代直接调用 python 模块
        cmd_parts=("$CRC_COMMAND" "create" "-c" "$concept")
        if [[ -n "$random_var" ]]; then
            cmd_parts+=("-var" "$random_var")
        fi
        if [[ -n "$random_style" ]]; then
             cmd_parts+=("--style" "$random_style")
        fi

        # 为了清晰显示和安全执行，避免直接使用 eval，将参数数组传递给命令
        echo "
  即将执行: ${(j: :)cmd_parts}" # 显示将要执行的命令

        # 实际执行命令
        "${cmd_parts[@]}" # 直接执行数组形式的命令
        exit_code=$?

        # 检查上一个命令的退出状态
        if [ $exit_code -ne 0 ]; then
            error_count=$((error_count + 1))
            echo "  警告：上一个命令执行失败 (退出码 $exit_code)。当前累计错误次数: $error_count / $MAX_ERRORS"

            # 检查是否达到错误上限
            if [ $error_count -ge $MAX_ERRORS ]; then
                echo "错误：累计错误次数达到上限 ($MAX_ERRORS)，脚本终止。请检查日志和API服务状态。"
                exit 1 # 强制退出整个脚本
            fi
        fi

        # 计算随机延迟时间 (61-180秒)
        random_sleep=$(( (RANDOM % 120) + 61 ))
        echo "  等待 ${random_sleep} 秒..."
        sleep $random_sleep
        echo "概念 $concept 处理完毕。"
        echo "---"
    # else
        # echo "跳过概念: $concept (不匹配模式 '$filter_pattern')" # 可选：显示被跳过的概念
    fi

done # End of while read loop

if [ $matched_concepts -eq 0 ]; then
     echo "警告：没有概念匹配模式 '$filter_pattern'。"
fi

echo "所有匹配的概念处理完成！"
echo "生成的图片保存在: ./images/{concept}/ 目录下"
echo "任务元数据保存在: ~/.crc/metadata/images_metadata.json"
echo "使用 'crc list-tasks' 查看所有任务状态"
exit 0