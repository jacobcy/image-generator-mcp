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
# 需要导入底层的保存函数
from ..utils.image_metadata import _save_metadata_file 
from ..utils.api import poll_for_result, normalize_api_response
from ..utils.filesystem_utils import write_last_succeed_job_id, METADATA_FILENAME
from ..utils.image_handler import download_and_save_image

logger = logging.getLogger(__name__)

# --- ANSI Color Codes ---
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_GRAY = "\033[90m"

def _colorize_status(status):
    # 确保 status 是字符串
    status_str = str(status)
    status_lower = status_str.lower()

    if status_lower in ['success', 'completed', 'true']:
        return f"{C_GREEN}{status_str}{C_RESET}"
    elif status_lower in ['failed', 'error', 'false']:
        return f"{C_RED}{status_str}{C_RESET}"
    elif status_lower in ['pending_queue', 'on_queue', 'submitted', 'submitted_webhook', 'submitted_no_wait', 'polling_failed']:
        return f"{C_YELLOW}{status_str}{C_RESET}"
    elif status:
        return f"{C_GRAY}{status_str}{C_RESET}"
    else:
        return f"{C_GRAY}N/A{C_RESET}"

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
    # (保持这部分逻辑不变，使用 all_tasks 数据)
    # 将 args.num 转换为 args.limit
    args.limit = getattr(args, 'num', 10)
    # 将 args.sort 转换为 args.sort_by
    args.sort_by = 'timestamp' if getattr(args, 'sort', 'time') == 'time' else getattr(args, 'sort', 'time')
    # 将 args.status 转换为字符串
    if hasattr(args, 'status') and args.status == 'all':
        args.status = None
    # 设置 args.asc
    args.asc = False

    filtered_tasks = all_tasks

    # 1. Filtering
    if args.status:
        logger.debug(f"按状态过滤: {args.status}")
        # Filter based on the status field, case-insensitive
        filtered_tasks = [t for t in filtered_tasks
                          if str(t.get('status', '')).lower() == args.status.lower() or
                             (args.status.lower() == 'success' and str(t.get('status', '')).lower() == 'completed') # Treat completed as success for filtering
                         ]
        if verbose_mode:
            print(f"DEBUG: 按状态过滤后剩余 {len(filtered_tasks)} 条记录")

    if args.concept:
        logger.debug(f"按概念过滤: {args.concept}")
        filtered_tasks = [t for t in filtered_tasks if str(t.get('concept', '')).lower() == args.concept.lower()]
        if verbose_mode:
            print(f"DEBUG: 按概念过滤后剩余 {len(filtered_tasks)} 条记录")

    if not filtered_tasks and (args.status or args.concept):
        print("根据当前过滤条件，未找到匹配的任务。")
        return 0 # No results found is not an error

    # 2. Sorting
    sort_key = args.sort_by
    reverse_sort = not args.asc # Default is descending
    logger.debug(f"按 '{sort_key}' 排序，升序: {args.asc}")
    if verbose_mode:
        print(f"DEBUG: 排序键: {sort_key}, 升序: {args.asc}")

    def get_sort_value(task):
        value = task.get(sort_key)
        if sort_key == 'timestamp':
            # Use 'created_at' or a potential 'updated_at' field
            ts_str = task.get('created_at') or task.get('metadata_updated_at') or task.get('metadata_added_at') or task.get('restored_at')
            if ts_str:
                try:
                    # Attempt to parse ISO format
                    return datetime.fromisoformat(str(ts_str))
                except ValueError:
                    # Fallback for other formats if needed, or return a default
                    return datetime.min
            return datetime.min # Default for missing timestamp
        # For other keys like status or concept, use lowercase for case-insensitive sort
        return str(value).lower() if value is not None else ''

    try:
        # 打印前几个任务的排序值
        if filtered_tasks and verbose_mode:
            print("DEBUG: 前几个任务的排序值:")
            for i, task in enumerate(filtered_tasks[:3]):
                sort_val = get_sort_value(task)
                print(f"  - 任务 {i+1}: {sort_val} (ID: {task.get('job_id', 'N/A')[:6]})")

        sorted_tasks = sorted(filtered_tasks, key=get_sort_value, reverse=reverse_sort)
        if verbose_mode:
            print(f"DEBUG: 排序后的任务数量: {len(sorted_tasks)}")
    except Exception as e:
        logger.error(f"排序任务时出错: {e}", exc_info=True)
        print(f"错误：排序任务时发生错误: {e}")
        return 1

    # 3. Limiting
    limited_tasks = sorted_tasks[:args.limit]
    logger.debug(f"限制显示最近的 {args.limit} 条记录。")
    if verbose_mode:
        print(f"DEBUG: 限制后的任务数量: {len(limited_tasks)}")

    # 4. Formatting and Printing with Colors
    if not limited_tasks:
        print("未找到要显示的任务记录。")
        return 0

    print(f"\n{C_BOLD}--- 任务列表 ---{C_RESET}")
    if verbose_mode:
        print(f"DEBUG: 找到 {len(limited_tasks)} 条任务记录")

    # Define columns and flexible widths - 简化显示，移除Filename列
    cols = ["时间", "ID", "状态", "命令", "概念"]
    # 调整列宽，特别是简化后的列
    col_widths = {"时间": 12, "ID": 8, "状态": 12, "命令": 12, "概念": 28}

    if args.verbose:
        cols.extend(["Seed", "URL"])
        col_widths["Seed"] = 12
        col_widths["URL"] = 28

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
        try:
            dt_obj = datetime.fromisoformat(str(ts_str)) if ts_str else None
            # 只显示月/日 时:分
            ts_formatted = dt_obj.strftime("%m/%d %H:%M") if dt_obj else 'N/A'
        except ValueError:
             ts_formatted = 'Invalid Date'
        row_parts.append(f"{C_BLUE}{ts_formatted:<{col_widths['时间']}}{C_RESET}")

        # Job ID (只显示前6位)
        job_id_str = (task.get('job_id') or 'N/A')[:6]
        row_parts.append(f"{C_MAGENTA}{job_id_str:<{col_widths['ID']}}{C_RESET}")

        # Status (Colored)
        status_str = (task.get('status') or 'N/A')[:col_widths["状态"]]
        colored_status = _colorize_status(status_str)
        # Correct padding calculation for colored strings
        padding_needed = col_widths["状态"] - (len(status_str) if status_str != 'N/A' else 3) 
        row_parts.append(f"{colored_status}{' ' * max(0, padding_needed)}")

        # 按照新规范显示类型和概念
        action_code = task.get('action_code')
        original_job_id = task.get('original_job_id')
        concept = task.get('concept')
        variations = task.get('variations', '')
        global_styles = task.get('global_styles', '')

        # 判断是原创任务还是action任务
        is_action = bool(action_code)
        is_original = not original_job_id

        # 如果是action任务，显示 action_code
        if is_action:
            type_str = action_code
        else:
            # 原创任务显示 create 或 recreate
            # 检查是否有标记表明这是一个 recreate 任务
            is_recreate = task.get('is_recreate', False) or task.get('recreate', False)
            type_str = "recreate" if is_recreate else "create"

        # 构建概念-变体-风格的格式
        # 对于所有任务，先检查是否有原始任务ID或概念是否为 action/unknown/restored
        logger.debug(f"Task {task.get('job_id')}: concept={concept}, original_job_id={original_job_id}")

        # 如果有原始任务ID或概念是 action/unknown/restored，尝试使用 trace_job_history 查找根任务
        if original_job_id or concept in ["action", "unknown", "restored"]:
            # 确定要追溯的任务ID
            trace_id = original_job_id if original_job_id else task.get('job_id')
            logger.debug(f"Task {task.get('job_id')}: 尝试使用 trace_job_history 查找根任务，追溯 ID: {trace_id}")

            # 追溯任务链条
            history_chain = trace_job_history(logger, trace_id, all_tasks)

            if history_chain and len(history_chain) > 0:
                # 从链条中找到根任务（第一个任务）
                root_task = history_chain[0]
                old_concept = concept

                # 只有当根任务的概念不是 action/unknown/restored 时才替换
                if root_task.get('concept') and root_task.get('concept') not in ["action", "unknown", "restored"]:
                    concept = root_task.get('concept')
                    variations = root_task.get('variations', '')
                    global_styles = root_task.get('global_styles', '')
                    logger.debug(f"Task {task.get('job_id')}: 从根任务 {root_task.get('job_id')} 继承概念信息: {old_concept} -> {concept}")
                else:
                    logger.info(f"Task {task.get('job_id')}: 根任务 {root_task.get('job_id')} 的概念也是 {root_task.get('concept')}，不替换")
            else:
                logger.info(f"Task {task.get('job_id')}: 无法找到根任务，保持原概念: {concept}")

        # 构建概念字符串
        concept_parts = []
        if concept:
            concept_parts.append(concept)
        if variations and variations != "":
            concept_parts.append(variations)
        if global_styles and global_styles != "":
            concept_parts.append(global_styles)

        # 如果概念列表为空但是action任务，显示原始任务ID
        if not concept_parts and is_action and original_job_id:
            concept_str = f"from:{original_job_id[:6]}"
        else:
            concept_str = "-".join(concept_parts) if concept_parts else "N/A"

        # 命令列显示 action_code 或 create/recreate
        command_str = type_str
        # 截断过长的命令字符串
        max_command_len = col_widths['命令']
        if len(command_str) > max_command_len:
            command_display = command_str[:max_command_len-3] + "..."
        else:
            command_display = command_str
        row_parts.append(f"{command_display:<{col_widths['命令']}}")

        # 概念列显示 concept-variation-style
        # 截断过长的概念字符串
        max_concept_len = col_widths['概念']
        if len(concept_str) > max_concept_len:
            concept_display = concept_str[:max_concept_len-3] + "..."
        else:
            concept_display = concept_str
        row_parts.append(f"{concept_display:<{col_widths['概念']}}")

        if args.verbose:
            # Seed (Gray)
            seed_str = str(task.get('seed') or 'N/A')[:col_widths["Seed"]]
            row_parts.append(f"{C_GRAY}{seed_str:<{col_widths['Seed']}}{C_RESET}")

            # URL (Gray, Truncated)
            url_str = (task.get('url') or 'N/A') # Already normalized
            max_url_len = col_widths["URL"]
            if len(url_str) > max_url_len:
                 url_display = url_str[:max_url_len-3] + "..."
            else:
                 url_display = url_str
            row_parts.append(f"{C_GRAY}{url_display:<{col_widths['URL']}}{C_RESET}")

        print(" | ".join(row_parts))

    print(f"{C_GRAY}{'-' * len(header)}{C_RESET}")
    print(f"显示 {C_BOLD}{len(limited_tasks)}{C_RESET} 条记录 (总匹配: {len(filtered_tasks)}, 总记录: {len(all_tasks)})")
    print()

    return 0

def add_subparser(subparsers):
    """Add list subparser"""
    parser = subparsers.add_parser(
        "list", aliases=["ls"], help="List tasks from local metadata"
    )
    parser.add_argument(
        "-n", "--num", type=int, default=10, help="Number of tasks to display"
    )
    parser.add_argument(
        "-s", "--sort", type=str, default="time", choices=["time", "status", "concept"], help="Sort order"
    )
    parser.add_argument(
        "--status", type=str, default=None, help="Filter by status (e.g., completed, pending)"
    )
    parser.add_argument(
        "-c", "--concept", type=str, default=None, help="Filter by concept"
    )
    parser.add_argument(
        '--sync', action='store_true', help='自动同步本地数据库中状态不确定的任务'
    )
    parser.add_argument(
        '--normalize', action='store_true', help='规范化元数据文件，移除冗余字段并统一格式'
    )
    parser.set_defaults(handle=handle_list_tasks)
    return parser
