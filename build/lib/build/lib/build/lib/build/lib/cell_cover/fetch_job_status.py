#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TTAPI Job Status Fetcher & Manager
---------------------------------
这个脚本用于:
- 查询 TTAPI Midjourney 任务的当前状态 (`view`)
- 获取历史任务列表 (`list`)
- 从历史记录恢复本地元数据 (`restore`)
"""

import json
import os
import argparse
import sys
import time
from datetime import datetime
import logging # Import logging
from pprint import pprint # For nice printing of lists/dicts
import uuid # Import uuid for potential validation?

# 尝试导入必要的库
try:
    import requests
except ImportError:
    print("错误：缺少 'requests' 库。请使用 'uv pip install requests' 安装。")
    sys.exit(1)

# --- 配置常量 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 引入项目根目录以便导入 utils (假设此脚本在 cell_cover/ 下)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

# Define metadata paths relative to project root
META_DIR = os.path.join(PROJECT_ROOT, "cell_cover", "metadata")
IMAGES_METADATA_FILENAME = os.path.join(META_DIR, "images_metadata.json")

# --- 从 utils 导入函数 ---
try:
    from cell_cover.utils.api import fetch_job_list_from_ttapi, poll_for_result, call_action_api, fetch_seed_from_ttapi # Added fetch_seed_from_ttapi
    from cell_cover.utils.file_handler import restore_metadata_from_job_list, download_and_save_image, find_initial_job_info, ensure_directories, update_job_metadata, upsert_job_metadata, save_image_metadata
    # Need ensure_directories if we load metadata here, or handle its absence
    # from cell_cover.utils.file_handler import ensure_directories # Already imported above
except ImportError as e:
    print(f"错误：无法导入必要的 utils 模块: {e}")
    print("请确保您在项目根目录下运行，并且 cell_cover/utils 路径正确且包含 __init__.py 文件。")
    sys.exit(1)

# --- 日志设置 ---
# 配置日志记录器
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# --- 辅助函数 ---

def get_api_key():
    """从环境变量或 .env 文件获取TTAPI密钥"""
    api_key = os.environ.get("TTAPI_API_KEY") # Prefer env var first

    # Fallback to .env (optional, less secure for production)
    if not api_key:
        env_path = os.path.join(PROJECT_ROOT, ".env") # Look for .env in project root
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key == "TTAPI_API_KEY":
                                api_key = value
                                break
                if api_key:
                    logger.info("从 .env 文件加载了 TTAPI_API_KEY。")
            except Exception as e:
                logger.warning(f"警告：无法从 .env 文件加载 API 密钥: {e}")

    if not api_key:
        logger.critical("错误：未设置 TTAPI_API_KEY 环境变量，且在项目根目录 .env 文件中也未找到。")
        print("错误：未设置 TTAPI_API_KEY 环境变量，且在项目根目录 .env 文件中也未找到。")
        sys.exit(1)

    return api_key

def display_job_details(result_dict):
    """格式化并显示单个任务详情字典 (带颜色)"""
    if not result_dict or not isinstance(result_dict, dict):
        print("未能获取或解析任务详情。")
        return

    print("\n\033[1m--- 任务详情 ---\033[0m") # Bold header
    # ANSI color codes: [96m (Cyan), [0m (Reset), [1m (Bold)
    for key, value in result_dict.items():
        # Print key in Cyan, bold
        print(f"  \033[96m\033[1m{key}:\033[0m", end=" ")

        # Special handling for list values (like components)
        if isinstance(value, list):
            print() # Start list on new line
            if not value: # Handle empty list
                 print("    []")
            else:
                 for i, item in enumerate(value):
                     print(f"    - {item}")
        # Special handling for potentially long prompt string
        elif key == 'prompt' and isinstance(value, str) and len(value) > 100:
             print() # Start prompt on new line
             # Indent the prompt for readability
             lines = value.split(' ')
             current_line = "    "
             for word in lines:
                 if len(current_line) + len(word) + 1 > 100: # Simple word wrap
                     print(current_line)
                     current_line = "    " + word
                 else:
                     current_line += " " + word
             if current_line.strip() != "    ":
                  print(current_line) # Print last line
        else:
            # Print other values normally
            print(f"{value}")

    print("\033[1m----------------\033[0m") # Bold footer

# --- 主逻辑 ---

def main(argv=None):
    # 如果 argv 为 None，则使用 sys.argv[1:]
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="使用 TTAPI 查询和管理 Midjourney 任务",
        epilog="需要设置环境变量 TTAPI_API_KEY 或在项目根目录有 .env 文件"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="可用子命令", required=True)

    # --- View 子命令 (已移至 generate_cover.py) ---
    # parser_view = subparsers.add_parser("view", help="查看指定 Job ID 的历史任务详情 (从最近列表获取)")
    # parser_view.add_argument("job_id", type=str, help="要查看的任务的 Job ID")

    # --- List 子命令 ---
    parser_list = subparsers.add_parser("list", help="获取任务列表 (默认本地, 使用 --remote 获取远程)")
    parser_list.add_argument("--page", type=int, default=1, help="远程列表页码 (仅当使用 --remote 时有效)")
    parser_list.add_argument("--limit", type=int, default=10, help="每页数量 (默认本地最多显示50条，远程默认10条)")
    parser_list.add_argument("--remote", action="store_true", help="从 TTAPI 服务器获取远程任务列表")

    # --- Restore 子命令 ---
    parser_restore = subparsers.add_parser("restore", help="从 TTAPI 历史记录恢复缺失的本地元数据")
    parser_restore.add_argument("--limit", type=int, default=100, help="尝试一次恢复的最大记录数 (默认: 100)")

    # --- Action 子命令 (通用) ---
    parser_action = subparsers.add_parser("action", help="执行指定的 Action 操作")
    parser_action.add_argument("job_id", type=str, help="要执行操作的任务的 Job ID")
    parser_action.add_argument("action_code", type=str, help="要执行的 Action Code (例如: upsample1, variation2, reroll0)")
    parser_action.add_argument("--hook-url", type=str, help="Webhook URL 用于异步通知（可选）")

    # --- Seed 子命令 ---
    parser_seed = subparsers.add_parser("seed", help="获取指定任务的 Seed 值")
    parser_seed.add_argument("identifier", type=str, help="要获取 Seed 的任务标识符 (Job ID 前缀/完整 ID/文件名)")

    # 修改 parse_args 调用以使用传入的 argv
    args = parser.parse_args(argv)
    api_key = get_api_key()

    # --- 初始化后续处理所需变量 ---
    job_id = None
    prompt_text = None
    concept_key = None
    seed = None
    action_code_for_save = None # 用于传递 action_code 到后续处理

    # --- 执行子命令 --- 
    # if args.subcommand == "view":
    #     # View logic is handled by generate_cover.py now
    #     print("错误：'view' 命令现在由 generate_cover.py 处理。请使用 'crc view ...'")
    #     sys.exit(1)

    if args.subcommand == "list":
        if args.remote:
            # Fetch from remote API
            logger.info(f"获取远程任务列表 (Page: {args.page}, Limit: {args.limit})...")
            job_list = fetch_job_list_from_ttapi(api_key, logger, page=args.page, limit=args.limit)
            if job_list:
                print(f"--- 远程任务列表 (Page: {args.page}, Limit: {args.limit}) ---")
                pprint(job_list, indent=2)
                print(f"--------------------------------------------------")
                print(f"共获取到 {len(job_list)} 条远程记录。")
            elif job_list == []: # API succeeded but returned empty list
                 print(f"--- 远程任务列表 (Page: {args.page}, Limit: {args.limit}) ---")
                 print("未找到远程任务记录。")
                 print(f"--------------------------------------------------")
            else:
                print("错误：无法从 TTAPI 获取远程任务列表。")
                return 1 # Return exit code
        else:
            # List from local metadata file
            logger.info(f"从本地元数据文件 {IMAGES_METADATA_FILENAME} 加载任务列表...")
            try:
                if os.path.exists(IMAGES_METADATA_FILENAME):
                    if os.path.getsize(IMAGES_METADATA_FILENAME) > 0:
                        with open(IMAGES_METADATA_FILENAME, 'r', encoding='utf-8') as f:
                            metadata_data = json.load(f)
                            if isinstance(metadata_data, dict) and "images" in metadata_data and isinstance(metadata_data["images"], list):
                                local_job_list = metadata_data["images"]
                                # Apply limit (default 50 for local)
                                limit = args.limit if args.limit != 10 else 50 # Default to 50 if not specified, else use user limit
                                display_list = local_job_list[-limit:] # Show last N items
                                print(f"--- 本地元数据任务列表 (最近 {len(display_list)} 条 / 共 {len(local_job_list)} 条) ---")
                                # Instead of pprint, format the output
                                if not display_list:
                                    print("  (无记录)")
                                else:
                                    # Find max length for alignment (optional, but nice)
                                    max_id_len = max(len(job.get("job_id", "N/A")) for job in display_list) if display_list else 10
                                    max_fname_len = max(len(job.get("filename", "N/A")) for job in display_list) if display_list else 20

                                    for job in display_list:
                                        job_id = job.get("job_id", "N/A")
                                        filename = job.get("filename", "N/A")
                                        seed = job.get("seed", "N/A") # Use N/A if seed is missing or None
                                        # Print formatted line with colors
                                        # ANSI color codes:  [94m (Blue),  [92m (Green),  [93m (Yellow),  [0m (Reset)
                                        print(f"  \033[94mJob ID:\033[0m   {job_id:<{max_id_len}}") # Corrected f-string again
                                        print(f"  \033[92mFilename:\033[0m {filename:<{max_fname_len}}")
                                        print(f"  \033[93mSeed:\033[0m     {seed}")
                                        print("  ---") # Add a separator between entries
                                # pprint(display_list, indent=2) # Removed pprint
                                # Remove the final separator as we now separate entries
                                # print(f"--------------------------------------------------")
                            else:
                                logger.error(f"本地元数据文件 {IMAGES_METADATA_FILENAME} 格式无效。")
                                print(f"错误：本地元数据文件 {IMAGES_METADATA_FILENAME} 格式无效。")
                                return 1 # Return exit code
                    else:
                        print(f"--- 本地元数据任务列表 --- ")
                        print("本地元数据文件为空。")
                        print(f"------------------------")
                else:
                    print(f"--- 本地元数据任务列表 --- ")
                    print(f"本地元数据文件 {IMAGES_METADATA_FILENAME} 未找到。")
                    print(f"------------------------")
            except IOError as e:
                logger.error(f"读取本地元数据文件 {IMAGES_METADATA_FILENAME} 时出错: {e}")
                print(f"错误：读取本地元数据文件时出错: {e}")
                return 1 # Return exit code
            except json.JSONDecodeError as e:
                 logger.error(f"解析本地元数据文件 {IMAGES_METADATA_FILENAME} 时出错: {e}")
                 print(f"错误：解析本地元数据文件时出错: {e}")
                 return 1 # Return exit code

    elif args.subcommand == "restore":
        logger.info(f"开始从 TTAPI 历史记录恢复元数据 (Limit: {args.limit})...")
        # Ensure directories exist before restoring
        ensure_directories()
        restored_count = restore_metadata_from_job_list(api_key, logger, limit=args.limit)
        if restored_count >= 0:
            print(f"元数据恢复完成，处理了 {restored_count} 条新记录或更新记录。")
        else:
            print("错误：元数据恢复过程中发生错误。")
            return 1 # Return exit code

    elif args.subcommand == "action":
        # Directly use args.job_id and args.action_code
        job_id = args.job_id
        action_code = args.action_code
        logger.info(f"准备对任务 Job ID '{job_id}' 执行 Action '{action_code}'...")

        action_result = call_action_api(
            logger=logger, # Pass logger
            api_key=api_key,
            original_job_id=job_id, # Use job_id directly
            action=action_code, # Use action_code directly
            hook_url=args.hook_url
        )

        if action_result: # Check if API call returned something (assuming job_id on success)
            new_job_id = action_result # Assume result is the new job id
            logger.info(f"Action '{action_code}' 提交成功，新 Job ID: {new_job_id}")
            print(f"Action '{action_code}' 提交成功，新 Job ID: {new_job_id}")

            # Store necessary info for metadata saving
            job_id_for_save = new_job_id
            action_code_for_save = action_code # Store the action code
            # Cannot easily inherit prompt/concept/seed without local lookup
            prompt_text_for_save = f"Action: {action_code} on {job_id}" # Placeholder prompt
            concept_key_for_save = None
            seed_for_save = None

            if not args.hook_url:
                logger.info("未提供 Webhook URL，将开始轮询 Action 结果...")
                print("Polling for Action result...")
                # Corrected poll_for_result call order: logger, job_id, api_key
                final_result = poll_for_result(logger, new_job_id, api_key)
                if final_result and final_result.get("cdnImage"): # Check cdnImage
                    image_url = final_result.get("cdnImage")
                    logger.info(f"Action 任务完成，图像 URL: {image_url}")
                    print(f"Action 任务完成，图像 URL: {image_url}")
                    # Corrected download_and_save_image call order: logger first
                    # Assign single return value to saved_path
                    saved_path = download_and_save_image(
                        logger,
                        image_url,
                        new_job_id,
                        prompt_text_for_save,
                        concept_key_for_save,
                        None, # variations
                        None, # styles
                        job_id, # original_job_id (the one action was performed on)
                        action_code_for_save, # action_code
                        final_result.get("components"),
                        final_result.get("seed") # seed from result
                    )
                    # Check if saved_path is not None to determine success
                    if saved_path:
                        # Metadata saving is handled inside download_and_save_image
                        # REMOVED redundant call to save_image_metadata below
                        # final_seed = final_result.get("seed") # Use seed from poll result
                        # save_image_metadata( ... )
                        logger.info(f"Action 结果图像和元数据已保存: {saved_path}")
                        print(f"Action 结果图像和元数据已保存: {saved_path}")
                        return 0
                    else:
                        logger.error("Action 结果图像下载或保存失败。")
                        print("错误：Action 结果图像下载或保存失败。")
                        return 1
                else:
                    logger.error(f"轮询 Action 任务结果失败或未获取到图像 URL。最后状态: {final_result.get('status') if final_result else 'N/A'}")
                    print(f"错误：轮询 Action 任务结果失败或未获取到图像 URL。最后状态: {final_result.get('status') if final_result else 'N/A'}")
                    # Save basic metadata even if polling failed
                    if job_id_for_save:
                        # Corrected save_image_metadata call order
                        save_image_metadata(
                            logger=logger,
                            image_id=None,
                            job_id=job_id_for_save,
                            filename=None,
                            filepath=None,
                            image_url=None,
                            prompt=prompt_text_for_save,
                            concept=concept_key_for_save,
                            variations=None,
                            global_styles=None,
                            components=final_result, # Save last poll result
                            seed=seed_for_save,
                            original_job_id=job_id
                        )
                        logger.info(f"已保存 Action 任务 {job_id_for_save} 的基本元数据（无图像）。")
                    return 1
            else:
                logger.info("提供了 Webhook URL，Action 任务将在后台处理。")
                print("提供了 Webhook URL，Action 任务将在后台处理。")
                # Save basic metadata immediately
                # Corrected save_image_metadata call order
                save_image_metadata(
                    logger=logger,
                    image_id=None,
                    job_id=job_id_for_save,
                    filename=None,
                    filepath=None,
                    image_url=None,
                    prompt=prompt_text_for_save,
                    concept=concept_key_for_save,
                    variations=None,
                    global_styles=None,
                    components=None, # No component info yet
                    seed=seed_for_save,
                    original_job_id=job_id
                )
                logger.info(f"已保存 Action 任务 {job_id_for_save} 的初始元数据（无图像）。")
                return 0
        else:
            logger.error(f"执行 Action '{action_code}' 失败: {action_result if isinstance(action_result, str) else 'API 调用未返回 Job ID 或失败'}")
            print(f"错误：执行 Action '{action_code}' 失败。")
            return 1

    elif args.subcommand == "seed":
        logger.info(f"准备获取任务 '{args.identifier}' 的 Seed 值...")
        # 1. 尝试从本地元数据获取
        local_job_info = find_initial_job_info(args.identifier)
        if local_job_info and local_job_info.get("seed") is not None:
            seed_value = local_job_info["seed"]
            logger.info(f"从本地元数据找到 Seed: {seed_value} (任务 ID: {local_job_info.get('job_id')})")
            print(f"Seed: {seed_value}")
            return 0
        else:
            logger.info(f"本地元数据中未找到 '{args.identifier}' 的 Seed 或任务信息不存在。尝试从 API 获取...")
            # 2. 如果本地没有，尝试从 API 获取
            # Need the actual Job ID first
            if not local_job_info or not local_job_info.get("job_id"):
                 logger.error(f"无法确定任务 '{args.identifier}' 的 Job ID，无法从 API 获取 Seed。")
                 print(f"错误：无法确定任务 '{args.identifier}' 的 Job ID。请先确保任务信息存在于本地 (可使用 'list --remote' 和 'restore')。")
                 return 1
            
            job_id = local_job_info["job_id"]
            print(f"正在从 API 查询任务 {job_id} 的 Seed...")
            api_seed_result = fetch_seed_from_ttapi(api_key, job_id, logger)

            if api_seed_result["success"]:
                seed_value = api_seed_result["seed"]
                logger.info(f"从 API 获取到 Seed: {seed_value}")
                print(f"Seed: {seed_value}")
                # Optionally update local metadata with the fetched seed
                update_job_metadata(job_id, {"seed": seed_value})
                logger.info(f"已更新任务 {job_id} 的本地元数据 Seed。")
                return 0
            else:
                logger.error(f"无法从 API 获取任务 {job_id} 的 Seed: {api_seed_result.get('message')}")
                print(f"错误：无法从 API 获取 Seed: {api_seed_result.get('message')}")
                return 1
    else:
        logger.error(f"未知的子命令: {args.subcommand}")
        parser.print_help()
        return 1

    return 0 # Default success

# Remove or comment out the direct execution block
# if __name__ == "__main__":
#     exit_code = main()
#     sys.exit(exit_code)

def fetch_job_status(job_id, api_key):
    # This function seems misplaced or potentially redundant now.
    # The main logic uses poll_for_result for status checking.
    # Keeping it here might cause confusion. Consider removing or refactoring.
    logger.warning("fetch_job_status function is likely deprecated. Polling is handled within main logic.")
    print(f"正在查询任务 {job_id} 的状态...")
    result = poll_for_result(logger, job_id, api_key, poll_interval=1, timeout=5, max_retries_per_poll=1)
    if result:
        display_job_details(result)
    else:
        print("未能获取任务状态或任务失败。") 