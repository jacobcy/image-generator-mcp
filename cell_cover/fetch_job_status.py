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
    from cell_cover.utils.file_handler import restore_metadata_from_job_list, download_and_save_image, find_initial_job_info, ensure_directories, update_job_metadata, upsert_job_metadata
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

def main():
    parser = argparse.ArgumentParser(
        description="使用 TTAPI 查询和管理 Midjourney 任务",
        epilog="需要设置环境变量 TTAPI_API_KEY 或在项目根目录有 .env 文件"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="可用子命令", required=True)

    # --- View 子命令 ---
    parser_view = subparsers.add_parser("view", help="查看指定 Job ID 的历史任务详情 (从最近列表获取)")
    parser_view.add_argument("job_id", type=str, help="要查看的任务的 Job ID")

    # --- List 子命令 ---
    parser_list = subparsers.add_parser("list", help="获取任务列表 (默认本地, 使用 --remote 获取远程)")
    parser_list.add_argument("--page", type=int, default=1, help="远程列表页码 (仅当使用 --remote 时有效)")
    parser_list.add_argument("--limit", type=int, default=10, help="每页数量 (默认本地最多显示50条，远程默认10条)")
    parser_list.add_argument("--remote", action="store_true", help="从 TTAPI 服务器获取远程任务列表")

    # --- Restore 子命令 ---
    parser_restore = subparsers.add_parser("restore", help="从 TTAPI 历史记录恢复缺失的本地元数据")
    parser_restore.add_argument("--limit", type=int, default=100, help="尝试一次恢复的最大记录数 (默认: 100)")
    # Future: Add --all flag to paginate and restore everything?

    # --- Upscale 子命令 ---
    parser_upscale = subparsers.add_parser("upscale", help="放大指定原始任务的图像")
    parser_upscale.add_argument("identifier", type=str, help="要放大图像的原始任务标识符 (Job ID 前缀/完整 ID/文件名)")
    parser_upscale.add_argument("index", type=int, choices=range(1, 5), help="要放大的图像索引 (1-4)")
    parser_upscale.add_argument("--hook-url", type=str, help="Webhook URL 用于异步通知（可选）")

    # --- Variation 子命令 ---
    parser_variation = subparsers.add_parser("variation", help="基于指定原始任务的图像创建变体")
    parser_variation.add_argument("identifier", type=str, help="要创建变体的原始任务标识符 (Job ID 前缀/完整 ID/文件名)")
    parser_variation.add_argument("index", type=int, choices=range(1, 5), help="要创建变体的图像索引 (1-4)")
    parser_variation.add_argument("--hook-url", type=str, help="Webhook URL 用于异步通知（可选）")

    # --- Reroll 子命令 ---
    parser_reroll = subparsers.add_parser("reroll", help="重新执行指定原始任务的提示词")
    parser_reroll.add_argument("identifier", type=str, help="要重新执行的原始任务标识符 (Job ID 前缀/完整 ID/文件名)")
    parser_reroll.add_argument("--hook-url", type=str, help="Webhook URL 用于异步通知（可选）")

    # --- Seed 子命令 ---
    parser_seed = subparsers.add_parser("seed", help="获取指定任务的 Seed 值")
    parser_seed.add_argument("identifier", type=str, help="要获取 Seed 的任务标识符 (Job ID 前缀/完整 ID/文件名)")

    args = parser.parse_args()
    api_key = get_api_key()

    # --- 执行子命令 ---
    if args.subcommand == "view":
        logger.info(f"尝试查找 Job ID: {args.job_id} 的历史记录...")
        # Fetch a list to find the job (fetch might not work for old jobs)
        # Fetch more items to increase the chance of finding it
        job_list = fetch_job_list_from_ttapi(api_key, logger, limit=100)
        if job_list:
            found_job = None
            for job in job_list:
                if job.get("job_id") == args.job_id:
                    found_job = job
                    break
            if found_job:
                display_job_details(found_job)
                # --- BEGIN METADATA UPSERT --- #
                logger.info(f"尝试将获取到的远程任务信息 Upsert 到本地元数据 (Job ID: {args.job_id})...")
                upsert_success = upsert_job_metadata(logger, args.job_id, found_job)
                if upsert_success:
                    logger.info(f"成功 Upsert Job ID {args.job_id} 的本地元数据。")
                else:
                    logger.error(f"未能 Upsert Job ID {args.job_id} 的本地元数据。请检查日志。")
                # --- END METADATA UPSERT --- #
            else:
                print(f"错误：在最近的 {len(job_list)} 条历史记录中未找到 Job ID: {args.job_id}")
                print("注意：此命令仅查找最近的历史记录。")
                sys.exit(1)
        else:
            print("错误：无法从 TTAPI 获取历史任务列表。")
            sys.exit(1)

    elif args.subcommand == "list":
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
                sys.exit(1)
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
                                sys.exit(1)
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
                sys.exit(1)
            except json.JSONDecodeError as e:
                 logger.error(f"解析本地元数据文件 {IMAGES_METADATA_FILENAME} 时出错: {e}")
                 print(f"错误：解析本地元数据文件时出错: {e}")
                 sys.exit(1)

    elif args.subcommand == "restore":
        logger.info(f"开始恢复元数据过程，尝试获取最近 {args.limit} 条记录...")
        # Fetch a batch of jobs to potentially restore
        job_list = fetch_job_list_from_ttapi(api_key, logger, limit=args.limit)
        if job_list:
            restored_count = restore_metadata_from_job_list(logger, job_list)
            if restored_count is not None:
                print(f"元数据恢复完成。共恢复了 {restored_count} 条缺失的记录。")
            else:
                print("错误：元数据恢复过程中发生错误。请检查日志。")
                sys.exit(1)
        elif job_list == []:
             print("未从 TTAPI 获取到任何历史任务记录，无法恢复。")
        else:
            print("错误：无法从 TTAPI 获取任务列表以进行恢复。")
            sys.exit(1)

    elif args.subcommand == "upscale" or args.subcommand == "variation" or args.subcommand == "reroll":
        action_name = args.subcommand.capitalize()
        logger.info(f"开始 {action_name} 操作: 标识符='{args.identifier}'")
        if hasattr(args, 'index'):
            logger.info(f"  索引={args.index}")

        # 1. 查找原始任务信息
        original_job_info = find_initial_job_info(logger, args.identifier)
        if not original_job_info:
            print(f"错误：无法根据标识符 '{args.identifier}' 找到唯一的原始任务。请检查标识符和元数据文件。")
            sys.exit(1)

        original_job_id = original_job_info.get("job_id")
        concept_key = original_job_info.get("concept", "unknown_concept")
        original_prompt = original_job_info.get("prompt", "")

        # 2. 构造 Action 字符串
        action_string = ""
        action_type_char = ''
        action_idx = 0
        if args.subcommand == "upscale":
            action_string = f"upsample{args.index}"
            action_type_char = 'U'
            action_idx = args.index
        elif args.subcommand == "variation":
            action_string = f"variation{args.index}"
            action_type_char = 'V'
            action_idx = args.index
        elif args.subcommand == "reroll":
            action_string = "reroll0" # Assuming 0 for reroll based on common patterns
            action_type_char = 'R'
            action_idx = 0 # Use 0 for reroll filename index

        logger.debug(f"构造的 Action 字符串: {action_string}")

        # 3. 调用 Action API
        print(f"提交 {action_name} 请求 (Action: {action_string}) for original job {original_job_id}...")
        new_job_id = call_action_api(logger, api_key, original_job_id, action_string, hook_url=args.hook_url)

        if not new_job_id:
            print(f"错误：提交 {action_name} 请求失败。")
            sys.exit(1)

        # 4. 处理同步/异步
        if args.hook_url:
            print(f"{action_name} 任务已提交 (新 Job ID: {new_job_id})。结果将发送到 webhook。")
            logger.info(f"{action_name} 任务 (新 Job ID: {new_job_id}) 已提交，使用 webhook: {args.hook_url}")
        else:
            print(f"{action_name} 任务已提交 (新 Job ID: {new_job_id})。开始轮询结果 (同步模式)...")
            logger.info(f"开始轮询 {action_name} 结果 (新 Job ID: {new_job_id})...")
            # 5. 轮询新任务结果
            result_data = poll_for_result(logger, new_job_id, api_key)

            if not result_data:
                print(f"错误：未能获取 {action_name} 任务 (Job ID: {new_job_id}) 的最终结果。")
                sys.exit(1)

            # 6. 下载并保存图像
            image_url = result_data.get("cdnImage")
            if not image_url:
                print(f"错误：{action_name} 任务 (Job ID: {new_job_id}) 成功，但结果中未找到图像 URL。")
                sys.exit(1)

            seed = result_data.get("seed")
            # components = result_data.get("components") # Removed components extraction

            print(f"{action_name} 完成，正在下载图像...")
            saved_path = download_and_save_image(
                logger=logger,
                image_url=image_url,
                job_id=new_job_id, # Pass the new job id
                prompt=original_prompt, # Use original prompt for context
                concept_key=concept_key,
                original_job_id=original_job_id, # Pass the original job id
                action_type=action_type_char,
                action_index=action_idx,
                seed=seed
                # components=components # Removed components argument
            )

            if saved_path:
                print(f"{action_name} 图像已成功保存到: {saved_path}")
            else:
                print(f"错误：下载或保存 {action_name} 图像失败。")
                sys.exit(1)

    elif args.subcommand == "seed":
         logger.info(f"开始获取 Seed 操作，查找标识符 '{args.identifier}'...")
         job_info = find_initial_job_info(logger, args.identifier)
         job_id_to_query = None
         job_id_for_update = None # May differ if identifier is prefix/filename

         if job_info:
             # Found in local metadata
             job_id_for_update = job_info.get("job_id")
             metadata_seed = job_info.get("seed")
             if metadata_seed is not None:
                 print(f"从本地元数据找到任务 {job_id_for_update} 的 Seed: {metadata_seed}")
                 logger.info(f"从本地元数据找到任务 {job_id_for_update} 的 Seed: {metadata_seed}")
                 sys.exit(0) # Exit successfully
             else:
                 # Found locally, but no seed stored. Query API using the confirmed Job ID.
                 if job_id_for_update:
                     logger.info(f"本地元数据中找到任务 {job_id_for_update}，但未记录 Seed。尝试从 API 获取...")
                     job_id_to_query = job_id_for_update
                 else:
                      logger.error(f"本地找到匹配 '{args.identifier}' 的记录，但该记录缺少 job_id，无法查询 API。")
                      print(f"错误：本地找到匹配 '{args.identifier}' 的记录，但该记录缺少 job_id。")
                      sys.exit(1)
         else:
             # Not found in local metadata. Check if the identifier itself is a Job ID.
             # Simple check: length 36 and contains hyphens
             if len(args.identifier) == 36 and '-' in args.identifier:
                  logger.info(f"本地元数据未找到，但标识符 '{args.identifier}' 看起来像一个 Job ID。尝试直接从 API 获取 Seed...")
                  job_id_to_query = args.identifier
                  job_id_for_update = args.identifier # Use the identifier for potential update
             else:
                  logger.error(f"在本地元数据中未找到标识符 '{args.identifier}'，且它不是一个有效的 Job ID 格式。无法查询 API。")
                  print(f"错误：无法找到任务 '{args.identifier}' 的本地记录，并且提供的标识符不是有效的 Job ID。")
                  sys.exit(1)

         # Proceed to query API if job_id_to_query is set
         if job_id_to_query:
             api_seed_data = fetch_seed_from_ttapi(logger, api_key, job_id_to_query)
             if api_seed_data and api_seed_data.get("seed") is not None:
                 seed_value = api_seed_data.get("seed")
                 print(f"从 API 获取到任务 {job_id_to_query} 的 Seed: {seed_value}")

                 # Attempt to update metadata if we have a definitive job_id_for_update
                 if job_id_for_update:
                     logger.info(f"尝试将获取到的 Seed {seed_value} 更新回本地元数据文件 (Job ID: {job_id_for_update})...")
                     update_success = update_job_metadata(logger, job_id_for_update, {"seed": seed_value})
                     if update_success:
                         logger.info(f"成功更新 Job ID {job_id_for_update} 的本地元数据 Seed。")
                     else:
                         logger.error(f"未能更新 Job ID {job_id_for_update} 的本地元数据 Seed。请检查日志。")
                 else:
                      # This case might happen if metadata was found via filename/prefix but lacked job_id initially
                      # We successfully queried API using identifier, but can't reliably update metadata without the original full job_id
                      logger.warning(f"已从 API 获取 Seed ({seed_value})，但无法更新本地元数据，因为原始记录缺少 Job ID 或未在本地找到。")

             elif api_seed_data is not None: # API responded but no seed
                 print(f"API 未返回任务 {job_id_to_query} 的 Seed 值。可能该任务不支持或未记录 Seed。")
                 logger.warning(f"API 未返回任务 {job_id_to_query} 的 Seed 值。")
             else: # API call failed
                 print(f"错误：无法从 API 获取任务 {job_id_to_query} 的 Seed。")
                 sys.exit(1)
         # else: Logic should ensure job_id_to_query is None only if exited earlier

# (保留旧的 fetch_job_status 函数，但可能不再直接被 main 调用)
def fetch_job_status(job_id, api_key):
    """调用 TTAPI 的 /fetch 接口获取任务状态 (旧版，用于 view 或 poll)"""
    # ... (旧的实现可以保留，但可能需要调整日志和错误处理) ...
    # For now, let's use fetch_job_list_from_ttapi for the 'view' command
    logger.warning("fetch_job_status 函数未在新流程中使用，'view' 命令将使用 fetch_job_list。")
    return None # Indicate this function isn't used in the primary new flow

if __name__ == "__main__":
    main() 