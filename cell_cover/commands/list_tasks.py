# -*- coding: utf-8 -*-
import logging
import json
from datetime import datetime
import os
import requests

# 从 utils 导入必要的函数 - 使用统一的元数据管理模块
from ..utils.metadata_manager import (
    load_all_metadata,
    update_job_metadata,
    find_initial_job_info,
    trace_job_history,
    sync_tasks,
    normalize_all_metadata_records # 导入规范化函数
)
# 不再需要导入normalize_task_metadata，因为元数据已经包含type和concept字段
# from ..utils.normalize_metadata import normalize_task_metadata
# 需要导入底层的保存函数
from ..utils.image_metadata import _save_metadata_file
from ..utils.api import normalize_api_response
from ..utils.api_client import fetch_job_list_from_ttapi # 直接从 api_client 导入
from ..utils.filesystem_utils import write_last_succeed_job_id, METADATA_FILENAME
from ..utils.image_handler import download_and_save_image

logger = logging.getLogger(__name__)

# 颜色常量
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_GRAY = "\033[90m" # Added Gray
C_RESET = "\033[0m"

def get_status_color(status):
    """根据状态返回颜色代码。"""
    status_lower = str(status).lower()
    if status_lower == 'completed':
        return C_GREEN
    elif 'fail' in status_lower or 'error' in status_lower or status_lower in ['file_missing', 'rename_failed']:
        return C_RED
    elif status_lower in ['pending', 'submitted', 'submitted_webhook', 'pending_queue', 'on_queue', 'processing', 'polling']:
        return C_YELLOW
    else:
        return C_RESET # Default color

def handle_list_tasks(args, logger):
    """处理 'list' 命令，加载、过滤、排序、同步、规范化并打印任务列表。"""
    # 设置日志级别
    verbose_mode = getattr(args, 'verbose', False)
    if not verbose_mode:
        logger.setLevel(logging.WARNING)

    logger.info("开始加载任务元数据...")
    all_tasks = load_all_metadata(logger)
    initial_load_count = len(all_tasks) if all_tasks else 0
    if initial_load_count == 0:
        print("未找到任何任务元数据。")
        # 如果是 sync 或 normalize 操作，即使为空也继续，因为 sync 可能找回任务
        if not getattr(args, 'sync', False) and not getattr(args, 'normalize', False):
             return 0
        else:
             all_tasks = [] #确保 all_tasks 是列表

    logger.info(f"成功加载 {initial_load_count} 条任务元数据")

    # --- 处理 --sync --- #
    if getattr(args, 'sync', False):
        api_key = os.environ.get('TTAPI_API_KEY')
        if not api_key:
            print("错误：--sync 选项需要设置 TTAPI_API_KEY 环境变量")
            return 1

        # 调用同步函数 (来自 metadata_manager, 其内部已包含标准化处理)
        # sync_tasks 返回 (sync_count, skipped_count, failed_count)
        sync_result = sync_tasks(logger, api_key, all_tasks)
        sync_count = sync_result[0]

        if sync_count > 0:
            # 同步后重新加载，因为 sync_tasks 会修改文件
            print(f"\n同步完成 {sync_count} 个任务，重新加载元数据...")
            all_tasks = load_all_metadata(logger)
            if all_tasks is None:
                logger.critical("同步后重新加载元数据失败！")
                print("错误：同步后重新加载元数据失败。")
                return 1

            # --- 在 sync 后自动进行规范化 --- #
            logger.info("同步完成后，开始自动规范化元数据...")
            normalized_tasks = normalize_all_metadata_records(logger, all_tasks)
            if normalized_tasks is not None and len(normalized_tasks) > 0:
                # 构建最终保存结构
                final_metadata_structure = {
                    "images": normalized_tasks,
                    "version": "1.1" # Or determine existing version
                }
                if _save_metadata_file(logger, METADATA_FILENAME, final_metadata_structure):
                    logger.info("同步后的元数据已成功规范化并保存。")
                    all_tasks = normalized_tasks # 使用规范化后的数据继续后续操作
                else:
                    logger.error("同步后保存规范化的元数据失败！后续列表可能使用未规范化的数据。")
            else:
                 logger.warning("同步后规范化未产生有效数据或失败。")
        else:
            print("同步操作完成，没有任务状态被更新。")

    # --- 处理 --normalize --- #
    if getattr(args, 'normalize', False):
        print("开始规范化元数据...")

        # 添加日志以清晰说明规范化逻辑
        logger.info("注意：规范化只对状态为 'completed' 的任务进行文件存在性检查")
        logger.info("      只有已完成但文件丢失的任务才会被标记为 'file_missing'")
        logger.info("      其他状态的任务将保持原状态")

        normalized_tasks = normalize_all_metadata_records(logger, all_tasks)
        if normalized_tasks is not None:
            processed_count = len(normalized_tasks)
            skipped = initial_load_count - processed_count
            # 构建最终保存结构
            final_metadata_structure = {
                 "images": normalized_tasks,
                 "version": "1.1" # Assume bumping version after normalize
            }
            # 覆盖写入文件
            if _save_metadata_file(logger, METADATA_FILENAME, final_metadata_structure):
                print(f"规范化完成。共处理 {processed_count} 条记录 (跳过 {skipped} 条)。文件已更新: {METADATA_FILENAME}")
                # 如果只执行 normalize，则在这里退出
                # 如果用户同时指定了其他列表参数，需要决定是否继续显示列表
                # 当前设计：--normalize 是独立操作，完成后退出
                return 0
            else:
                print("错误：写入规范化后的元数据失败！")
                return 1
        else:
             print("错误：规范化处理失败。")
             return 1

    # --- 如果执行到这里，说明没有执行 --normalize 或 normalize 失败后需要继续 --- #
    # --- 或者执行了 --sync (无论是否成功或规范化) 后需要继续显示列表 --- #

    # 检查是否还有任务数据（可能 sync 后为空）
    if not all_tasks:
         print("没有可显示的任务元数据。")
         return 0

    # --- 处理列表显示逻辑 (Filtering, Sorting, Limiting, Printing) --- #
    args.limit = getattr(args, 'num', 10)
    args.sort_by = 'timestamp' if getattr(args, 'sort', 'time') == 'time' else getattr(args, 'sort', 'time')
    if hasattr(args, 'status') and args.status == 'all':
        args.status = None
    args.asc = False

    filtered_tasks = all_tasks

    # 1. Filtering
    if args.status:
        logger.debug(f"按状态过滤: {args.status}")
        filtered_tasks = [t for t in filtered_tasks
                          if str(t.get('status', '')).lower() == args.status.lower() or
                             (args.status.lower() == 'success' and str(t.get('status', '')).lower() == 'completed')]
        if verbose_mode: print(f"DEBUG: 按状态过滤后剩余 {len(filtered_tasks)} 条记录")
    if args.concept:
        logger.debug(f"按概念过滤: {args.concept}")
        filtered_tasks = [t for t in filtered_tasks if str(t.get('concept', '')).lower() == args.concept.lower()]
        if verbose_mode: print(f"DEBUG: 按概念过滤后剩余 {len(filtered_tasks)} 条记录")
    if not filtered_tasks and (args.status or args.concept):
        print("根据当前过滤条件，未找到匹配的任务。")
        return 0

    # 2. Sorting
    sort_key = args.sort_by
    reverse_sort = not args.asc
    logger.debug(f"按 '{sort_key}' 排序，升序: {args.asc}")
    if verbose_mode: print(f"DEBUG: 排序键: {sort_key}, 升序: {args.asc}")
    def get_sort_value(task):
        value = task.get(sort_key)
        if sort_key == 'timestamp':
            ts_str = task.get('created_at') or task.get('metadata_updated_at') or task.get('metadata_added_at') or task.get('restored_at')
            if ts_str: 
                try: 
                    return datetime.fromisoformat(str(ts_str)); 
                except ValueError: 
                    return datetime.min
            return datetime.min
        return str(value).lower() if value is not None else ''
    try:
        # 打印前几个任务的排序值
        if filtered_tasks and verbose_mode:
             print("DEBUG: 前几个任务的排序值:")
             for i, t in enumerate(filtered_tasks[:3]):
                 task_id_short = t.get('job_id', 'N/A')[:6]
                 sort_val = get_sort_value(t)
                 debug_msg = f"  - 任务 {i+1}: {sort_val} (ID: {task_id_short})"
                 print(debug_msg) # Print the formatted string

        sorted_tasks = sorted(filtered_tasks, key=get_sort_value, reverse=reverse_sort)
        if verbose_mode: print(f"DEBUG: 排序后的任务数量: {len(sorted_tasks)}")
    except Exception as e: logger.error(f"排序任务时出错: {e}", exc_info=True); print(f"错误：排序任务时发生错误: {e}"); return 1

    # 3. Limiting
    limited_tasks = sorted_tasks[:args.limit]
    logger.debug(f"限制显示最近的 {args.limit} 条记录。")
    if verbose_mode: print(f"DEBUG: 限制后的任务数量: {len(limited_tasks)}")

    # 4. Formatting and Printing with Colors
    if not limited_tasks:
        print("未找到要显示的任务记录。")
        return 0

    print("\n--- 任务列表 ---")
    if verbose_mode: print(f"DEBUG: 找到 {len(limited_tasks)} 条任务记录")

    # Define columns and flexible widths
    cols = ["时间", "ID", "状态", "命令", "概念"]
    col_widths = {"时间": 12, "ID": 7, "状态": 13, "命令": 22, "概念": 12} # Adjusted widths

    if args.verbose:
        cols.extend(["Seed", "文件名"])
        col_widths["Seed"] = 12
        col_widths["文件名"] = 30 # Replaced URL with Filename for verbose

    # Print header with color
    header_parts = []
    for col in cols:
        header_parts.append(f"{C_CYAN}{col:<{col_widths[col]}}{C_RESET}")
    header = " | ".join(header_parts)
    print(header)
    print(f"{C_GRAY}{'-' * len(header)}{C_RESET}") # Use gray for separator

    # Print rows
    for task in limited_tasks:
        row_parts = []

        # 时间戳 (月/日 时:分)
        ts_str = task.get('created_at') or task.get('metadata_updated_at') or task.get('metadata_added_at') or task.get('restored_at')
        try: dt_obj = datetime.fromisoformat(str(ts_str)) if ts_str else None; ts_formatted = dt_obj.strftime("%m/%d %H:%M") if dt_obj else 'N/A'
        except ValueError: ts_formatted = 'Invalid Date'
        row_parts.append(f"{C_BLUE}{ts_formatted:<{col_widths['时间']}}{C_RESET}")

        # Job ID (只显示前6位)
        job_id_str = (task.get('job_id') or 'N/A')[:6]
        row_parts.append(f"{C_CYAN}{job_id_str:<{col_widths['ID']}}{C_RESET}")

        # Status (Colored)
        status_raw = task.get('status') or 'N/A'
        status_color = get_status_color(status_raw)
        status_str = status_raw[:col_widths["状态"]]
        row_parts.append(f"{status_color}{status_str:<{col_widths['状态']}}{C_RESET}")

        # 命令 (使用 action 字段)
        command_str = task.get('action', 'unknown') # Use the 'action' field
        max_command_len = col_widths['命令']
        command_display = (command_str[:max_command_len-3] + "...") if len(command_str) > max_command_len else command_str
        row_parts.append(f"{command_display:<{col_widths['命令']}}") # Default color

        # 概念 (直接使用 concept 字段, C_YELLOW)
        concept_str = task.get('concept', 'N/A') # Get concept directly
        max_concept_len = col_widths['概念']
        concept_display = (concept_str[:max_concept_len-3] + "...") if len(concept_str) > max_concept_len else concept_str
        row_parts.append(f"{C_YELLOW}{concept_display:<{col_widths['概念']}}{C_RESET}")

        if args.verbose:
            # Seed (Gray)
            seed_str = str(task.get('seed') or 'N/A')[:col_widths["Seed"]]
            row_parts.append(f"{C_GRAY}{seed_str:<{col_widths['Seed']}}{C_RESET}")

            # Filename (Gray, Truncated)
            filename_str = (task.get('filename') or 'N/A')
            max_filename_len = col_widths["文件名"]
            filename_display = (filename_str[:max_filename_len-3] + "...") if len(filename_str) > max_filename_len else filename_str
            row_parts.append(f"{C_GRAY}{filename_display:<{col_widths['文件名']}}{C_RESET}")

        print(" | ".join(row_parts))

    print(f"{C_GRAY}{'-' * len(header)}{C_RESET}")
    print(f"显示 {len(limited_tasks)} 条记录 (总匹配: {len(filtered_tasks)}, 总记录: {initial_load_count})")
    print()

    return 0

def add_subparser(subparsers):
    """Add list subparser"""
    parser = subparsers.add_parser(
        "list", aliases=["ls"], help="List tasks from local metadata"
    )
    parser.add_argument("-n", "--num", type=int, default=10, help="Number of tasks to display")
    parser.add_argument("-s", "--sort", type=str, default="time", choices=["time", "status", "concept"], help="Sort order")
    parser.add_argument("--status", type=str, default=None, help="Filter by status (e.g., completed, pending, all)")
    parser.add_argument("-c", "--concept", type=str, default=None, help="Filter by concept")
    parser.add_argument('--sync', action='store_true', help='同步本地数据库中状态不确定的任务')
    parser.add_argument('--normalize', action='store_true', help='规范化元数据文件 (独立操作)')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息 (Seed, 文件名)')
    parser.set_defaults(handle=handle_list_tasks)
    return parser
