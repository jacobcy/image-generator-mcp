#!/bin/zsh

# 一键生成脚本：为提供的一系列自定义提示词生成封面
# 作者：[您的名字或Heidi]
# 日期：$(date +%Y-%m-%d)
#
# **重要：此脚本必须从项目根目录执行**
# 例如: cd /path/to/project/root && ./scripts/batch_generate_prompts.sh "Prompt 1" "Another prompt with spaces" "Third prompt"

# --- 配置 ---
# crc 命令
CRC_COMMAND="crc"

# 错误计数器上限
MAX_ERRORS=5

# --- 变量初始化 ---
error_count=0
# 将所有参数视为提示词列表
prompts_list=("$@")

# --- 函数定义 ---
usage() {
    echo "用法: $0 <"提示词1"> ["提示词2" ...]"
    echo "  为每个提供的自定义提示词生成一张图像。"
    echo "  如果提示词包含空格，请使用引号将其括起来。"
    echo "示例:"
    echo "  $0 "A photorealistic image of a cell" "Abstract representation of data network""
    exit 1
}

# --- 前提检查 ---

# 检查是否提供了至少一个提示词
if [ ${#prompts_list[@]} -eq 0 ]; then
    echo "错误：未提供任何提示词。"
    usage
fi

echo "检查 crc 命令是否可用..."
if ! command -v $CRC_COMMAND &> /dev/null
then
    echo "错误：'$CRC_COMMAND' 命令未找到。请确保项目已正确安装并通过 'uv pip install .' 创建了命令。"
    exit 1
fi
echo "'$CRC_COMMAND' 命令已找到。"

echo "将为以下 ${#prompts_list[@]} 个提示词生成图像："
# 打印提示词（为简洁起见，只打印前几个）
printf "  - %s\n" "${prompts_list[@]:0:5}" 
if [ ${#prompts_list[@]} -gt 5 ]; then
    echo "  ... (还有更多)"
fi
echo "调用间隔: 随机 (61-180秒)"
echo "---当前工作目录: $(pwd) ---"

# --- 主要逻辑 ---

prompt_index=1
for prompt in "${prompts_list[@]}"; do
    echo "处理提示词 $prompt_index / ${#prompts_list[@]} ..."
    echo "  提示词: "$prompt""

    # --- 构建命令 ---
    # 使用 crc 命令的 -p 选项
    cmd_parts=("$CRC_COMMAND" "create" "-p" "$prompt")
    
    # 为了清晰显示和安全执行，避免直接使用 eval
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

    # 如果不是最后一个提示词，则等待
    if [ $prompt_index -lt ${#prompts_list[@]} ]; then
        # 计算随机延迟时间 (61-180秒)
        random_sleep=$(( (RANDOM % 120) + 61 ))
        echo "  等待 ${random_sleep} 秒..."
        sleep $random_sleep
    fi
    
    echo "提示词 $prompt_index 处理完毕。"
    echo "---"
    prompt_index=$((prompt_index + 1))

done # End of for loop

echo "所有提供的提示词处理完成！请检查 outputs/images 和 cell_cover/metadata 目录。"
exit 0 