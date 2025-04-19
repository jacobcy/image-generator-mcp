\
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import logging

# Adjust import paths to be relative since cli.py is now inside cell_cover
from .utils.config import load_config, get_api_key
from .utils.log import setup_logging
from .utils.file_handler import ensure_directories

# Import command handlers using relative paths
from .commands.create import handle_create
from .commands.generate import handle_generate
from .commands.blend import handle_blend
from .commands.describe import handle_describe
from .commands.list_cmd import handle_list_concepts, handle_list_variations
from .commands.recreate import handle_recreate
from .commands.select import handle_select
from .commands.view import handle_view

# Define the base directory for cell_cover relative to this script
# This script is now inside cell_cover, so the script's directory IS the cell_cover dir
CELL_COVER_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    parser = argparse.ArgumentParser(
        description="Cell Cover Generator CLI",
        epilog="需要设置环境变量 TTAPI_API_KEY")
    subparsers = parser.add_subparsers(dest='command', help='选择要执行的操作', required=True)

    # --- list_concepts 命令 ---
    parser_list = subparsers.add_parser('list_concepts', help='列出所有可用的创意概念')
    parser_list.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- variations 命令 ---
    parser_variations = subparsers.add_parser('variations', help='列出指定概念的所有变体')
    parser_variations.add_argument('concept_key', type=str, help='要查询变体的创意概念键')
    parser_variations.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- generate 命令 ---
    parser_generate = subparsers.add_parser('generate', help='仅生成 Midjourney 提示词文本')
    parser_generate.add_argument("-c", "--concept", type=str, help="要使用的创意概念的键")
    parser_generate.add_argument("-p", "--prompt", type=str, help="自由格式的提示词")
    parser_generate.add_argument("-var", "--variation", type=str, nargs='+', help="要使用的变体的键")
    parser_generate.add_argument("-ar", "--aspect", type=str, default="cell_cover", help="宽高比设置的键")
    parser_generate.add_argument("-q", "--quality", type=str, default="high", help="质量设置的键")
    parser_generate.add_argument("-ver", "--version", type=str, default="v6", help="Midjourney 版本的键")
    parser_generate.add_argument("--cref", type=str, help="图像参考 URL")
    parser_generate.add_argument("--style", type=str, nargs='+', help="应用全局风格修饰词")
    parser_generate.add_argument("--clipboard", action="store_true", help="将生成的提示词复制到剪贴板")
    parser_generate.add_argument("--save-prompt", action="store_true", help="同时保存生成的提示词文本到 outputs 目录")
    parser_generate.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- create 命令 ---
    parser_create = subparsers.add_parser('create', help='生成提示词并提交图像生成任务')
    parser_create.add_argument("-c", "--concept", type=str, help="要使用的创意概念的键")
    parser_create.add_argument("-p", "--prompt", type=str, help="自由格式的提示词")
    parser_create.add_argument("-var", "--variation", type=str, help="要使用的变体的键 (只支持一个)")
    parser_create.add_argument("-ar", "--aspect", type=str, default="cell_cover", help="宽高比设置的键")
    parser_create.add_argument("-q", "--quality", type=str, default="high", help="质量设置的键")
    parser_create.add_argument("-ver", "--version", type=str, default="v6", help="Midjourney 版本的键")
    parser_create.add_argument("-m", "--mode", type=str, default="relax", choices=["relax", "fast", "turbo"],
                      help="生成模式 (默认: relax)")
    parser_create.add_argument("--cref", type=str, help="图像参考 URL 或本地文件路径")
    parser_create.add_argument("--style", type=str, help="应用全局风格修饰词 (只支持一个)")
    parser_create.add_argument("--clipboard", action="store_true", help="将生成的提示词复制到剪贴板")
    parser_create.add_argument("--save-prompt", action="store_true", help="同时保存生成的提示词文本到 outputs 目录")
    parser_create.add_argument("--hook-url", type=str, help="Webhook URL")
    parser_create.add_argument("--notify-id", type=str, help="通知ID")
    parser_create.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- recreate 命令 ---
    parser_recreate = subparsers.add_parser("recreate", help="使用原始 Prompt 和 Seed 重新生成图像")
    parser_recreate.add_argument("identifier", type=str, help="要重新生成的原始任务标识符")
    parser_recreate.add_argument("--hook-url", type=str, help="Webhook URL")
    parser_recreate.add_argument("--cref", type=str, help="图像参考 URL 或本地文件路径")
    parser_recreate.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- select 命令 ---
    parser_select = subparsers.add_parser('select', help='切割并选择放大后的图片')
    parser_select.add_argument("image_path", type=str, help="要切割的图片路径")
    parser_select.add_argument("-s", "--select", type=str, nargs='+', choices=['u1', 'u2', 'u3', 'u4'], help="选择要保存的部分")
    parser_select.add_argument("-o", "--output-dir", type=str, help="输出目录")
    parser_select.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- view 命令 ---
    parser_view = subparsers.add_parser('view', help='查看特定任务的详细信息')
    parser_view.add_argument("identifier", type=str, help="要查看的任务标识符")
    parser_view.add_argument("--remote", action="store_true", help="强制从 API 获取最新信息")
    parser_view.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- blend 命令 ---
    parser_blend = subparsers.add_parser('blend', help='将 2-5 张图片混合成一张新图')
    parser_blend.add_argument("image_paths", nargs='+', help="要混合的本地图片路径")
    parser_blend.add_argument("--dimensions", choices=['PORTRAIT', 'SQUARE', 'LANDSCAPE'], default='SQUARE', help="生成图像的比例")
    parser_blend.add_argument("--mode", choices=['relax', 'fast', 'turbo'], default='fast', help="生成模式")
    parser_blend.add_argument("--hook-url", type=str, help="Webhook URL")
    parser_blend.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- describe 命令 ---
    parser_describe = subparsers.add_parser('describe', help='根据图像生成提示词')
    parser_describe.add_argument("image_path_or_url", type=str, help="用于生成提示词的本地图像路径或 URL")
    parser_describe.add_argument("--hook-url", type=str, help="Webhook URL")
    parser_describe.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # Parse arguments from sys.argv
    args = parser.parse_args()

    # --- Initialization ---
    # Setup logger (use CELL_COVER_DIR for log file placement - this is now correct)
    verbose_flag = getattr(args, 'verbose', False)
    logger = setup_logging(CELL_COVER_DIR, verbose_flag)

    # Load config (config file path is now directly in CELL_COVER_DIR)
    config_path = os.path.join(CELL_COVER_DIR, 'prompts_config.json')
    config = load_config(logger, config_path)
    if not config:
        logger.critical(f"无法加载配置文件: {config_path}")
        sys.exit(1)

    # Get API key
    api_key = get_api_key(logger)
    if not api_key and args.command not in ['list_concepts', 'variations', 'generate', 'select']:
        logger.critical("需要 TTAPI_API_KEY 环境变量或 .env 文件中的条目才能执行此命令。")
        sys.exit(1)

    # Ensure directories exist (base_dir is now CELL_COVER_DIR)
    ensure_directories(logger, base_dir=CELL_COVER_DIR)

    # --- Command Dispatch --- 
    exit_code = 1 # Default exit code

    try:
        if args.command == 'list_concepts':
            exit_code = handle_list_concepts(config)
        elif args.command == 'variations':
            exit_code = handle_list_variations(config, args)
        elif args.command == 'generate':
            exit_code = handle_generate(args, config, logger)
        elif args.command == 'create':
            exit_code = handle_create(args, config, logger, api_key)
        elif args.command == 'recreate':
            exit_code = handle_recreate(args, config, logger, api_key)
        elif args.command == 'select':
            exit_code = handle_select(args, logger)
        elif args.command == 'view':
            exit_code = handle_view(args, logger, api_key)
        elif args.command == 'blend':
            exit_code = handle_blend(args, config, logger, api_key)
        elif args.command == 'describe':
            exit_code = handle_describe(args, logger, api_key)
        else:
            logger.error(f"未知的命令: {args.command}")
            parser.print_help()
            exit_code = 1
    except Exception as e:
        logger.exception(f"执行命令 '{args.command}' 时发生意外错误: {e}")
        print(f"错误：执行命令时发生意外错误。请检查日志文件 {os.path.join(CELL_COVER_DIR, 'logs', 'app.log')} 获取详细信息。")
        exit_code = 1

    sys.exit(exit_code)

if __name__ == "__main__":
    main()

