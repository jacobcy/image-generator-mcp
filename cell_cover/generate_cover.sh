#!/bin/zsh

# Cell封面生成脚本
# 这个脚本是Python脚本的简单包装器，提供了一些常用命令的快捷方式

# 获取脚本所在目录
SCRIPT_DIR=$(dirname "$0")
PYTHON_SCRIPT="$SCRIPT_DIR/generate_cover.py"
FETCH_SCRIPT="$SCRIPT_DIR/fetch_job_status.py"

# 确保Python脚本是可执行的
chmod +x "$PYTHON_SCRIPT"
chmod +x "$FETCH_SCRIPT"

# 显示帮助信息
show_help() {
  echo "Cell封面生成器与状态检查器 - 使用说明"
  echo "---------------------------------------"
  echo "用法:"
  echo "  ./generate_cover.sh [命令] [参数]"
  echo "  或者直接使用 python3 generate_cover.py <命令> --help 查看具体命令的选项"
  echo ""
  echo "可用命令:"
  echo "  list                  列出所有可用的创意概念"
  echo "  variations            列出指定概念的所有变体"
  echo "  generate              仅生成 Midjourney 提示词文本"
  echo "  create                生成提示词并提交图像生成任务"
  echo "  check                 根据 Job ID 查询任务状态和结果"
  echo "  help                  显示此帮助信息"
  echo ""
  echo "示例:"
  echo "  ./generate_cover.sh list"
  echo "  ./generate_cover.sh variations concept_a"
  echo "  ./generate_cover.sh generate -c concept_a -var scientific --clipboard"
  echo "  ./generate_cover.sh create -c concept_a -var dramatic -m relax"
  echo "  ./generate_cover.sh create -c concept_a --hook-url https://your-webhook.com/callback"
  echo "  ./generate_cover.sh check 51c3b432-dcfa-493e-a50b-e367a3438ae4"
}

# 主函数
main() {
  local command=$1
  shift # Remove the command from the arguments list

  case "$command" in
    list)
      python3 "$PYTHON_SCRIPT" list "$@"
      ;;
    variations)
      python3 "$PYTHON_SCRIPT" variations "$@" # Pass remaining args (concept_key)
      ;;
    generate)
      echo "正在生成提示词 (不提交任务)..."
      python3 "$PYTHON_SCRIPT" generate "$@" # Pass all remaining args to the generate subparser
      ;;
    create)
      echo "正在生成提示词并提交任务..."
      python3 "$PYTHON_SCRIPT" create "$@" # Pass all remaining args to the create subparser
      ;;
    check)
      # Check command still uses the separate fetch script
      if [ -z "$1" ]; then
        echo "错误: 必须指定一个 Job ID。"
        echo "用法: ./generate_cover.sh check JOB_ID"
        exit 1
      fi
      echo "正在查询 Job ID: $1 ..."
      python3 "$FETCH_SCRIPT" --job-id "$1"
      ;;
    help|--help|-h)
      show_help
      ;;
    *) # Handle direct pass-through for python script help etc.
       # Or handle cases where the first arg might be a python option
       if [[ "$command" == --* ]] || [[ "$command" == -* ]]; then
           # If the first arg looks like an option, assume user wants to call python directly
           echo "将参数直接传递给 Python 脚本..."
           # Put the command back in args
           set -- "$command" "$@"
           python3 "$PYTHON_SCRIPT" "$@"
       else
           echo "未知命令: $command"
           echo "运行 './generate_cover.sh help' 获取帮助"
           exit 1
       fi
      ;;
  esac
}

# 如果没有参数，显示帮助信息
if [ $# -eq 0 ]; then
  show_help
  exit 0
fi

# 执行主函数
main "$@"