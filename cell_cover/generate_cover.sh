#!/bin/zsh

# Cell封面生成脚本
# 这个脚本是Python脚本的简单包装器，提供了一些常用命令的快捷方式

# 获取脚本所在目录
SCRIPT_DIR=$(dirname "$0")
PYTHON_SCRIPT="$SCRIPT_DIR/generate_cover.py"
FETCH_SCRIPT="$SCRIPT_DIR/fetch_job_status.py" # 新增：fetch脚本路径

# 确保Python脚本是可执行的
chmod +x "$PYTHON_SCRIPT"
chmod +x "$FETCH_SCRIPT" # 新增：确保fetch脚本也可执行

# 显示帮助信息
show_help() {
  echo "Cell封面生成器与状态检查器 - 使用说明"
  echo "---------------------------------------"
  echo "用法:"
  echo "  ./generate_cover.sh [命令] [参数]" # 更新用法描述
  echo ""
  echo "生成相关命令:"
  echo "  list                  列出所有可用的创意概念"
  echo "  variations CONCEPT    列出指定概念的所有变体"
  echo "  generate CONCEPT      生成指定概念的提示词 (仅生成提示词，不提交任务)" # 更新描述
  echo ""
  echo "任务状态命令:" # 新增部分
  echo "  check JOB_ID          根据 Job ID 查询任务状态和结果"
  echo ""
  echo "其他命令:"
  echo "  help                  显示此帮助信息"
  echo ""
  echo "选项 (用于generate命令):"
  echo "  --variation VAR       指定要使用的变体"
  echo "  --aspect RATIO        指定宽高比 (默认: cell_cover)"
  echo "  --quality QUALITY     指定质量设置 (默认: high)"
  echo "  --version VERSION     指定Midjourney版本 (默认: v6)"
  echo "  --clipboard           将生成的提示词复制到剪贴板"
  # 移除了 generate 提交任务的功能，所以移除 --mode, --hook-url 等相关选项说明
  echo ""
  echo "示例:"
  echo "  ./generate_cover.sh list"
  echo "  ./generate_cover.sh variations concept_a"
  echo "  ./generate_cover.sh generate concept_a --variation scientific --clipboard"
  echo "  ./generate_cover.sh check 51c3b432-dcfa-493e-a50b-e367a3438ae4"
}

# 主函数
main() {
  case "$1" in
    list)
      python3 "$PYTHON_SCRIPT" --list
      ;;
    variations)
      if [ -z "$2" ]; then
        echo "错误: 必须指定一个概念。"
        echo "用法: ./generate_cover.sh variations CONCEPT"
        exit 1
      fi
      python3 "$PYTHON_SCRIPT" --list-variations "$2"
      ;;
    generate)
      # 注意：generate 命令现在只生成提示词，不调用 API 提交任务
      # 如果需要提交任务，可以直接使用 generate_cover.py
      if [ -z "$2" ]; then
        echo "错误: 必须指定一个概念。"
        echo "用法: ./generate_cover.sh generate CONCEPT [选项]" 
        exit 1
      fi

      # 构建Python命令 (只生成提示词和可选复制)
      CMD="python3 \"$PYTHON_SCRIPT\" --concept $2"

      # 处理其余参数 (仅处理 generate_cover.py 支持的生成提示词相关参数)
      shift 2
      while [ "$#" -gt 0 ]; do
        case "$1" in
          --variation|--aspect|--quality|--version)
            if [ -z "$2" ]; then
              echo "错误: 选项 $1 需要一个值"
              exit 1
            fi
            CMD="$CMD $1 $2"
            shift 2
            ;;
          --clipboard)
            CMD="$CMD $1"
            shift
            ;;
          *)
            echo "警告: generate 命令忽略未知选项 $1 (只支持提示词生成选项)"
            shift
            ;;
        esac
      done

      # 执行命令
      echo "正在生成提示词 (不提交任务)..."
      eval $CMD
      ;;
    check) # 新增 check 命令
      if [ -z "$2" ]; then
        echo "错误: 必须指定一个 Job ID。"
        echo "用法: ./generate_cover.sh check JOB_ID"
        exit 1
      fi
      echo "正在查询 Job ID: $2 ..."
      python3 "$FETCH_SCRIPT" --job-id "$2"
      ;;
    help|--help|-h)
      show_help
      ;;
    *)
      echo "未知命令: $1"
      echo "运行 './generate_cover.sh help' 获取帮助"
      exit 1
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