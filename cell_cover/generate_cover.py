#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cell Cover Generator using TTAPI
--------------------------------
这个脚本用于生成Cell杂志封面的Midjourney提示词，
并通过 TTAPI 调用 Midjourney API 来生成实际图像，
最终将图像保存到 images 目录。
"""

import json
import os
import argparse
import sys
import time
import logging
from datetime import datetime
import uuid

# 尝试导入必要的库
try:
    import requests
except ImportError:
    print("错误：缺少 'requests' 库。请使用 'uv pip install requests' 安装。")
    sys.exit(1)

# 检查 pyperclip 模块是否可用
try:
    import importlib.util
    PYPERCLIP_AVAILABLE = importlib.util.find_spec("pyperclip") is not None
except ImportError:
    PYPERCLIP_AVAILABLE = False

# 从 utils 导入重构后的函数
from utils.api import call_imagine_api, poll_for_result
from utils.config import load_config, get_api_key
from utils.log import setup_logging
from utils.prompt import generate_prompt_text, save_text_prompt, copy_to_clipboard
from utils.file_handler import ensure_directories, download_and_save_image

# --- 配置常量 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# CONFIG_PATH constructed in main
# OUTPUT_DIR, IMAGE_DIR, META_DIR, META_FILE moved to utils.file_handler

# 初始化日志记录器
# logger = setup_logging() # Logger setup moved to main, after parsing args
logger = None # Placeholder

# --- 辅助函数 (保留与主流程和配置交互相关的部分) ---

# load_config moved to utils.config

# get_api_key moved to utils.config

# setup_logging moved to utils.log

def list_concepts(config):
    """列出所有可用的创意概念"""
    logger.info("列出所有可用的创意概念")
    print("可用的创意概念:")
    concepts = config.get("concepts", {})
    if not concepts:
        logger.warning("配置文件中没有找到任何概念")
        print("  配置文件中没有找到任何概念。")
        return

    logger.debug(f"找到 {len(concepts)} 个概念")
    for key, concept in concepts.items():
        print(f"  - {key}: {concept.get('name', 'N/A')}")
        print(f"    {concept.get('description', '无描述')}")
        print()

def list_variations(config, concept_key):
    """列出指定概念的所有变体"""
    logger.info(f"列出概念 '{concept_key}' 的所有变体")
    concepts = config.get("concepts", {})
    if concept_key not in concepts:
        logger.error(f"找不到创意概念 '{concept_key}'")
        print(f"错误：找不到创意概念 '{concept_key}'")
        return

    concept = concepts[concept_key]
    variations = concept.get("variations", {})
    print(f"'{concept.get('name', concept_key)}'的可用变体:")
    if not variations:
        logger.warning(f"概念 '{concept_key}' 没有定义变体")
        print("  此概念没有定义变体。")
        return

    logger.debug(f"找到 {len(variations)} 个变体")
    for key, desc in variations.items():
        print(f"  - {key}: {desc}")
    print()

# generate_prompt_text moved to utils.prompt

# save_text_prompt moved to utils.prompt

# copy_to_clipboard moved to utils.prompt

# call_imagine_api moved to utils.api

# poll_for_result moved to utils.api

# save_image_metadata moved to utils.file_handler

# download_and_save_image moved to utils.file_handler

# ensure_directories moved to utils.file_handler

def main():
    parser = argparse.ArgumentParser(
        description="使用 TTAPI 生成 Cell 杂志封面图像",
        epilog="需要设置环境变量 TTAPI_API_KEY"
    )
    subparsers = parser.add_subparsers(dest='command', help='选择要执行的操作')
    subparsers.required = True # Ensure a command is provided

    # --- list 命令 ---
    parser_list = subparsers.add_parser('list', help='列出所有可用的创意概念')
    # Add verbose option to list command as well
    parser_list.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- variations 命令 ---
    parser_variations = subparsers.add_parser('variations', help='列出指定概念的所有变体')
    parser_variations.add_argument('concept_key', type=str, help='要查询变体的创意概念键')
    parser_variations.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- generate 命令 (仅生成提示词) ---
    parser_generate = subparsers.add_parser('generate', help='仅生成 Midjourney 提示词文本')
    parser_generate.add_argument("-c", "--concept", type=str, required=True, help="要使用的创意概念的键")
    parser_generate.add_argument("-var", "--variation", type=str, nargs='+', help="要使用的变体的键 (可选, 可指定多个)")
    parser_generate.add_argument("-ar", "--aspect", type=str, default="cell_cover", help="宽高比设置的键 (默认: cell_cover)")
    parser_generate.add_argument("-q", "--quality", type=str, default="high", help="质量设置的键 (默认: high)")
    parser_generate.add_argument("-ver", "--version", type=str, default="v6", help="Midjourney 版本的键 (默认: v6)")
    parser_generate.add_argument("--clipboard", action="store_true", help="将生成的提示词复制到剪贴板")
    parser_generate.add_argument("--save-prompt", action="store_true", help="同时保存生成的提示词文本到 outputs 目录")
    parser_generate.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    # --- create 命令 (生成并提交任务) ---
    parser_create = subparsers.add_parser('create', help='生成提示词并提交图像生成任务')
    parser_create.add_argument("-c", "--concept", type=str, required=True, help="要使用的创意概念的键")
    parser_create.add_argument("-var", "--variation", type=str, nargs='+', help="要使用的变体的键 (可选, 可指定多个)")
    parser_create.add_argument("-ar", "--aspect", type=str, default="cell_cover", help="宽高比设置的键 (默认: cell_cover)")
    parser_create.add_argument("-q", "--quality", type=str, default="high", help="质量设置的键 (默认: high)")
    parser_create.add_argument("-ver", "--version", type=str, default="v6", help="Midjourney 版本的键 (默认: v6)")
    parser_create.add_argument("-m", "--mode", type=str, default="fast", choices=["relax", "fast", "turbo"],
                      help="生成模式: relax(约120秒), fast(约60秒), turbo(约30秒) (默认: fast)")
    parser_create.add_argument("--clipboard", action="store_true", help="将生成的提示词复制到剪贴板 (也会在提交前显示)")
    parser_create.add_argument("--save-prompt", action="store_true", help="同时保存生成的提示词文本到 outputs 目录 (也会在提交前显示)")
    parser_create.add_argument("--hook-url", type=str, help="Webhook URL，用于接收任务完成通知（异步模式必需）")
    parser_create.add_argument("--notify-id", type=str, help="通知ID，用于识别回调请求（可选）")
    parser_create.add_argument("-v", "--verbose", action="store_true", help="显示详细的调试日志")

    args = parser.parse_args()

    # Setup logger after parsing args to get verbose flag
    # Note: args.verbose might not exist for all commands initially, handle this
    global logger
    verbose_flag = getattr(args, 'verbose', False)
    logger = setup_logging(SCRIPT_DIR, verbose_flag)
    logger.info(f"执行命令: {args.command}")

    # Load config and API key (needed for most commands)
    # Consider moving this inside command blocks if not always needed
    config_path = os.path.join(SCRIPT_DIR, "prompts_config.json")
    config = load_config(logger, config_path)
    api_key = get_api_key(logger, SCRIPT_DIR)

    # Ensure necessary directories exist (Needed for generate/create)
    # We can make this conditional based on command
    if args.command in ['generate', 'create']:
        if not ensure_directories(logger):
            logger.critical("无法创建必要的目录，脚本退出。")
            sys.exit(1)

    # --- Command Execution --- #

    if args.command == 'list':
        list_concepts(config)

    elif args.command == 'variations':
        list_variations(config, args.concept_key)

    elif args.command == 'generate' or args.command == 'create':
        # Common logic for generating prompt text
        prompt_data = generate_prompt_text(
            logger=logger,
            config=config,
            concept_key=args.concept,
            variation_keys=args.variation,
            aspect_ratio=args.aspect,
            quality=args.quality,
            version=args.version
        )

        if not prompt_data:
            sys.exit(1) # Error already logged by generate_prompt_text

        print("生成的 Midjourney 提示词:")
        print("-" * 80)
        print(prompt_data["prompt"])
        print("-" * 80)

        # Optional: Save prompt text
        if args.save_prompt:
            from utils.file_handler import OUTPUT_DIR # Import specifically for this call
            save_text_prompt(
                logger=logger,
                output_dir=OUTPUT_DIR,
                prompt_text=prompt_data["prompt"],
                concept_key=args.concept,
                variation_keys=args.variation
            )

        # Optional: Copy to clipboard
        if args.clipboard:
            if copy_to_clipboard(logger, prompt_data["prompt"]):
                print("提示词文本已复制到剪贴板")

        # --- create command specific logic ---
        if args.command == 'create':
            # Add mode from create args
            prompt_data["mode"] = args.mode

            # Check hook URL for async mode warning (only for create)
            if not args.hook_url:
                warning_msg = "警告：未指定 --hook-url，将使用同步模式。建议使用异步模式以提高可靠性。"
                logger.warning(warning_msg)
                print(warning_msg)
                print("如果任务生成时间过长，脚本可能会超时。")

            # Call API to create job
            job_id = call_imagine_api(
                logger=logger,
                prompt_data=prompt_data,
                api_key=api_key,
                hook_url=args.hook_url,
                notify_id=args.notify_id
            )

            if not job_id:
                print("未能提交图像生成任务。")
                sys.exit(1)

            # Handle sync/async response
            if args.hook_url:
                logger.info(f"任务已提交，任务ID: {job_id}")
                logger.info(f"使用异步模式，结果将发送到: {args.hook_url}")
                print(f"任务已提交，任务ID: {job_id}")
                print(f"任务完成后，结果将发送到: {args.hook_url}")
                if args.notify_id:
                    logger.debug(f"通知ID: {args.notify_id}")
                    print(f"通知ID: {args.notify_id}")
                print("脚本将退出，您可以关闭终端或继续其他操作。")
                # No return here, script exits naturally
            else:
                # Sync mode: poll for result
                logger.info("使用同步模式，开始轮询任务结果...")
                print("使用同步模式，开始轮询任务结果...")
                result_data = poll_for_result(logger=logger, job_id=job_id, api_key=api_key)

                if not result_data:
                    print("未能获取生成的图像 URL。")
                    sys.exit(1)

                image_url = result_data.get("cdnImage")
                if not image_url:
                    print("错误：任务成功但结果中未找到 cdnImage URL。")
                    sys.exit(1)

                components = result_data.get("components")
                seed = result_data.get("seed")

                # Download and save image
                saved_image_path = download_and_save_image(
                    logger=logger,
                    image_url=image_url,
                    job_id=job_id,
                    prompt=prompt_data["prompt"], # Use original prompt sent
                    concept_key=args.concept,
                    variation_keys=args.variation,
                    components=components,
                    seed=seed
                )
                if not saved_image_path:
                    print("未能成功下载或保存图像。")
                    sys.exit(1)

                print("图像生成和保存流程完成!")

    # No else needed, subparsers.required=True ensures a command is chosen

if __name__ == "__main__":
    main()