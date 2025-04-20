#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import logging

# Adjust import paths to be relative since cli.py is now inside cell_cover
from .utils.config import load_config, get_api_key
from .utils.log import setup_logging
from .utils.filesystem_utils import check_and_create_directories, read_last_job_id, write_last_job_id, read_last_succeed_job_id

# Import command handlers using relative paths
from .commands.create import handle_create
from .commands.generate import handle_generate
from .commands.blend import handle_blend
from .commands.describe import handle_describe
from .commands.list_cmd import handle_list_concepts, handle_list_variations
from .commands.recreate import handle_recreate
from .commands.select import handle_select
from .commands.view import handle_view
from .commands.action import handle_action

# Import the new handler (will be created next)
# from .commands.list-tasks import handle_list_tasks

# Define the base directory for cell_cover relative to this script
# This script is now inside cell_cover, so the script's directory IS the cell_cover dir
CELL_COVER_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Cell Cover CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List concepts command with alias
    list_parser = subparsers.add_parser(
        "list-concepts",
        help="列出所有可用的创意概念"
    )
    
    # Help command
    help_parser = subparsers.add_parser(
        "help",
        help="显示帮助信息"
    )
    
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
    parser_select.add_argument("image_path", type=str, nargs='?', default=None, help="要切割的图片路径。如果省略，则尝试使用上次提交的任务结果。")
    parser_select.add_argument('--last-job', action='store_true', help='明确使用上次提交的任务 ID 查找图片路径。')
    parser_select.add_argument('--last-succeed', action='store_true', help='使用上次成功完成的任务 ID 查找图片路径。')
    parser_select.add_argument("-s", "--select", type=str, required=True, nargs='+', choices=['u1', 'u2', 'u3', 'u4'], help="选择要保存的部分 (必须提供)")
    parser_select.add_argument("-o", "--output-dir", type=str, help="输出目录 (默认基于原图位置)")
    parser_select.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- view 命令 ---
    view_parser = subparsers.add_parser('view', help='查看指定任务的状态和结果',
                                        description='查看指定任务的状态和结果')
    view_group = view_parser.add_mutually_exclusive_group()
    view_group.add_argument('identifier', nargs='?', help='任务 ID 或图像文件路径')
    view_group.add_argument('--last-job', action='store_true', help='使用上一个提交的任务 ID')
    view_group.add_argument('--last-succeed', action='store_true', help='使用上一个成功的任务 ID')
    view_parser.add_argument('--remote', action='store_true', help='直接从API获取最新任务状态')
    view_parser.add_argument('--local-only', action='store_true', help='仅查看本地任务信息，不从API获取')
    view_parser.add_argument('--save', action='store_true', help='如果可用，下载并保存结果图像')
    view_parser.add_argument('--history', action='store_true', help='显示任务历史链')

    # --- blend 命令 ---
    blend_parser = subparsers.add_parser('blend', help='混合多个图像', description='混合多个图像')
    blend_parser.add_argument('identifiers', nargs='+', help='要混合的图像文件路径或任务 ID（最多3个）')
    blend_parser.add_argument('--title', help='图像标题，用于元数据')
    blend_parser.add_argument('--weights', help='混合权重，如"0.6,0.2,0.2"')
    blend_parser.add_argument('-i', '--interactive', action='store_true', help='交互模式：查看结果并选择是否保存')

    # --- describe 命令 ---
    describe_parser = subparsers.add_parser('describe', help='从图像生成描述', description='从图像生成描述')
    describe_parser.add_argument('identifier', nargs='?', help='任务 ID 或图像文件路径')
    describe_parser.add_argument('--last-job', action='store_true', help='使用上一个提交的任务 ID')
    describe_parser.add_argument('--last-succeed', action='store_true', help='使用上一个成功的任务 ID')
    describe_parser.add_argument('--text-only', action='store_true', help='仅输出文本描述，不使用JSON格式')
    describe_parser.add_argument('--components', action='store_true', help='检测图像组件')
    describe_parser.add_argument('--save', action='store_true', help='将描述保存到元数据文件')
    describe_parser.add_argument('--language', help='描述的语言，例如"zh-CN"')

    # --- list-tasks 命令 (NEW) ---
    list_tasks_parser = subparsers.add_parser('list-tasks', 
                                         aliases=["list"], 
                                         help='列出最近的生成任务', 
                                         description='列出最近的生成任务')
    list_tasks_parser.add_argument('-n', '--num', type=int, default=10, help='要显示的任务数量（默认：10）')
    list_tasks_parser.add_argument('--status', choices=['all', 'success', 'failed', 'pending'], default='all', help='筛选任务状态')
    list_tasks_parser.add_argument('--sort', choices=['time', 'status', 'concept'], default='time', help='排序标准')
    list_tasks_parser.add_argument('--concept', help='按概念名称筛选任务')
    list_tasks_parser.add_argument('--action', help='按动作代码筛选任务')
    list_tasks_parser.add_argument('--image-only', action='store_true', help='仅显示成功生成了图像的任务')
    list_tasks_parser.add_argument('--sync', action='store_true', help='自动同步本地数据库中状态不确定的任务')
    list_tasks_parser.add_argument('-v', '--verbose', action='store_true', help='显示详细的调试日志')

    # --- action 命令 (NEW) ---
    # Based on ttapi.md section 2: /action
    ACTION_CHOICES = [
        'upsample1', 'upsample2', 'upsample3', 'upsample4',
        'variation1', 'variation2', 'variation3', 'variation4',
        'high_variation', 'low_variation',
        'upscale2', 'upscale4',
        'zoom_out_2', 'zoom_out_1_5',
        'pan_left', 'pan_right', 'pan_up', 'pan_down',
        'upscale_creative', 'upscale_subtle',
        'reroll',
        'redo_upscale2', 'redo_upscale4',
        'make_square',
        'redo_upscale_subtle', 'redo_upscale_creative'
    ]
    # Add descriptions based on ttapi.md
    ACTION_DESCRIPTIONS = {
        'upsample1': '放大第 1 张图像 (U1)',
        'upsample2': '放大第 2 张图像 (U2)',
        'upsample3': '放大第 3 张图像 (U3)',
        'upsample4': '放大第 4 张图像 (U4)',
        'variation1': '基于第 1 张图像生成变体 (V1)',
        'variation2': '基于第 2 张图像生成变体 (V2)',
        'variation3': '基于第 3 张图像生成变体 (V3)',
        'variation4': '基于第 4 张图像生成变体 (V4)',
        'reroll': '基于相同提示词重新生成一组图像 (Reroll)',
        'high_variation': '对放大后的图像进行大幅度变化 (Vary Strong)',
        'low_variation': '对放大后的图像进行小幅度变化 (Vary Subtle)',
        'upscale_creative': '使用创意模式放大图像 (Upscale Creative)',
        'upscale_subtle': '使用微妙模式放大图像 (Upscale Subtle)',
        'make_square': '将非方形图像裁剪/扩展为方形 (Make Square)',
        'upscale2': '将放大后的图像再放大 2 倍 (v5版本)',
        'upscale4': '将放大后的图像再放大 4 倍 (v5版本)',
        'zoom_out_2': '将放大后的图像缩小 2 倍 (Zoom Out 2x)',
        'zoom_out_1_5': '将放大后的图像缩小 1.5 倍 (Zoom Out 1.5x)',
        'pan_left': '向左平移扩展图像 (Pan Left)',
        'pan_right': '向右平移扩展图像 (Pan Right)',
        'pan_up': '向上平移扩展图像 (Pan Up)',
        'pan_down': '向下平移扩展图像 (Pan Down)'
    }

    action_parser = subparsers.add_parser('action', help='对现有结果应用操作（变体、放大等）',
                                        description='对现有结果应用操作（变体、放大等）')
    action_parser.add_argument('action_code', help='要应用的操作，例如 "variation1"')
    action_group = action_parser.add_mutually_exclusive_group()
    action_group.add_argument('identifier', nargs='?', help='任务 ID 或图像文件路径')
    action_group.add_argument('--last-job', action='store_true', help='使用上一个提交的任务 ID')
    action_group.add_argument('--last-succeed', action='store_true', help='使用上一个成功的任务 ID')
    action_parser.add_argument("--hook-url", type=str, help="Webhook URL 用于异步通知（可选）")
    action_parser.add_argument("--wait", action="store_true", help="提交操作后等待任务完成并下载结果 (如果适用)。")
    action_parser.add_argument("-m", "--mode", type=str, default="fast", choices=["relax", "fast", "turbo"],
                      help="生成模式 (默认: fast)")
    action_parser.add_argument("--list", action="store_true", help="列出所有可用的操作代码并退出。")
    action_parser.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging with verbose flag
    logger = setup_logging(CELL_COVER_DIR, args.verbose)
    
    # Handle help command or no command
    if args.command == "help" or args.command is None:
        parser.print_help()
        return
    
    # Handle list-concepts command
    if args.command == "list-concepts":
        config_path = os.path.join(CELL_COVER_DIR, 'prompts_config.json')
        config = load_config(logger, config_path)
        if config:
            handle_list_concepts(config)
        else:
            logger.error("无法加载配置文件")
            sys.exit(1)
        return
    
    # --- Initialization ---
    config_path = os.path.join(CELL_COVER_DIR, 'prompts_config.json')
    config = load_config(logger, config_path)
    if not config:
        logger.critical(f"无法加载配置文件: {config_path}")
        sys.exit(1)

    api_key = get_api_key(logger)
    commands_requiring_api_key = ['create', 'recreate', 'view', 'blend', 'describe', 'action']
    if not api_key and args.command in commands_requiring_api_key:
        logger.critical(f"命令 '{args.command}' 需要 TTAPI_API_KEY 环境变量或 .env 文件中的条目。")
        sys.exit(1)

    if not check_and_create_directories(logger):
        logger.critical("无法创建必要的应用程序目录，程序退出。")
        sys.exit(1)
    else:
        logger.info("必要的应用程序目录已检查/创建。")

    # --- Command Dispatch ---
    exit_code = 1  # Default exit code
    job_id_for_action = None  # Variable to hold the determined job ID for action command

    try:
        if args.command == 'variations':
            exit_code = handle_list_variations(config, args)
        elif args.command == 'generate':
            exit_code = handle_generate(args, config, logger)
        elif args.command == 'create':
            exit_code = handle_create(args, config, logger, api_key)
        elif args.command == 'recreate':
            exit_code = handle_recreate(args, config, logger, api_key)
        elif args.command == 'select':
            # --- Select Command Identifier/Path Resolution ---
            identifier_or_path = None
            source_description = ""
            if args.image_path:
                identifier_or_path = args.image_path
                source_description = "提供的路径"
            elif args.last_succeed:
                logger.info("使用 --last-succeed 参数，尝试读取上一个成功 Job ID...")
                identifier_or_path = read_last_succeed_job_id(logger)
                source_description = "上一个成功任务 ID"
                if not identifier_or_path:
                    logger.error("错误：无法读取上一个成功 Job ID (last_succeed.json)。")
                    sys.exit(1)
            else:  # Default or --last-job
                logger.info("未提供路径或 --last-succeed，尝试读取上一个提交的 Job ID...")
                identifier_or_path = read_last_job_id(logger)
                source_description = "上一个提交任务 ID"
                if not identifier_or_path:
                    logger.error("错误：必须提供 图片路径 或明确指定 --last-succeed，或者确保之前有成功的提交记录。")
                    sys.exit(1)

            logger.info(f"将使用 {source_description}: {identifier_or_path} 来查找图片")
            # Pass the determined identifier/path to handle_select
            # handle_select needs adjustment to accept this instead of args directly?
            # Let's modify handle_select signature later if needed, for now pass args
            # But we need to potentially override args.image_path for the handler
            args.image_path = identifier_or_path  # Overwrite args for the handler

            from .commands.select import handle_select
            exit_code = handle_select(args, logger)
        elif args.command == 'view':
            # --- View Command Identifier Resolution ---
            identifier_to_use = None
            source_description = ""
            if args.identifier:
                identifier_to_use = args.identifier
                source_description = "提供的标识符"
            elif args.last_succeed:
                logger.info("使用 --last-succeed 参数，尝试读取上一个成功 Job ID...")
                identifier_to_use = read_last_succeed_job_id(logger)
                source_description = "上一个成功任务 ID"
                if not identifier_to_use:
                    logger.error("错误：无法读取上一个成功 Job ID (last_succeed.json)。")
                    sys.exit(1)
            else:  # Default or --last-job
                logger.info("未提供标识符或 --last-succeed，尝试读取上一个提交的 Job ID...")
                identifier_to_use = read_last_job_id(logger)
                source_description = "上一个提交任务 ID"
                if not identifier_to_use:
                    logger.error("错误：必须提供 任务标识符 或明确指定 --last-succeed，或者确保之前有成功的提交记录。")
                    sys.exit(1)

            logger.info(f"将查看 {source_description}: {identifier_to_use}")
            # Overwrite args.identifier for the handler
            args.identifier = identifier_to_use

            from .commands.view import handle_view
            exit_code = handle_view(args, logger, api_key)
        elif args.command == 'blend':
            exit_code = handle_blend(args, config, logger, api_key)
        elif args.command == 'describe':
            exit_code = handle_describe(args, logger, api_key)
        elif args.command == 'list-tasks' or args.command == 'list':
            from .commands.list_tasks import handle_list_tasks
            exit_code = handle_list_tasks(args, logger)
        elif args.command == 'action':
            # --- Action Command Identifier Resolution ---
            identifier_to_use = None
            source_description = ""
            if args.identifier:
                identifier_to_use = args.identifier
                source_description = "提供的标识符"
            elif args.last_succeed:
                logger.info("使用 --last-succeed 参数，尝试读取上一个成功 Job ID...")
                identifier_to_use = read_last_succeed_job_id(logger)
                source_description = "上一个成功任务 ID"
                if not identifier_to_use:
                    logger.error("错误：无法读取上一个成功 Job ID (last_succeed.json)。")
                    action_parser.print_help()
                    sys.exit(1)
            else:  # Default or --last-job
                logger.info("未提供标识符或 --last-succeed，尝试读取上一个提交的 Job ID...")
                identifier_to_use = read_last_job_id(logger)
                source_description = "上一个提交任务 ID"
                if not identifier_to_use:
                    logger.error("错误：必须提供 任务标识符 或明确指定 --last-succeed，或者确保之前有成功的提交记录。")
                    action_parser.print_help()
                    sys.exit(1)

            logger.info(f"使用 {source_description}: {identifier_to_use}")

            from .commands.action import handle_action
            exit_code = handle_action(
                args.action_code,
                identifier_to_use,
                args.hook_url,
                args.wait,
                args.mode,
                logger,
                api_key
            )
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

