# -*- coding: utf-8 -*-
import logging
import json
from datetime import datetime
import os
import requests
from typing import Optional

# 从 utils 导入必要的函数 - 使用统一的元数据管理模块
from ..utils.metadata_manager import (
    load_all_metadata,
    update_job_metadata,
    find_initial_job_info,
    trace_job_history,
    normalize_all_metadata_records # 导入规范化函数
)
# 不再需要导入sync_tasks
# from ..utils.sync_metadata import sync_tasks
# 不再需要导入normalize_task_metadata，因为元数据已经包含type和concept字段
# from ..utils.normalize_metadata import normalize_task_metadata
# 需要导入底层的保存函数
from ..utils.image_metadata import _save_metadata_file
from ..utils.api import normalize_api_response
from ..utils.api_client import fetch_job_list_from_ttapi # 直接从 api_client 导入
from ..utils.filesystem_utils import write_last_succeed_job_id # Removed METADATA_FILENAME
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

def handle_list_tasks(
    status: Optional[str],
    concept: Optional[str],
    limit: Optional[int],
    sort_by: str,
    ascending: bool,
    verbose: bool,
    logger: logging.Logger,
    crc_base_dir: str, # Changed from args to explicit parameters
    remote: bool = False, # 新增参数：是否从远程API获取任务列表
    api_key: Optional[str] = None # 新增参数：API密钥
):
    """处理 'list' 命令，加载、过滤、排序并打印任务列表。

    Args:
        status: Filter by status.
        concept: Filter by concept.
        limit: Limit number of tasks.
        sort_by: Field to sort by.
        ascending: Sort order.
        verbose: Verbose output flag.
        logger: Logger instance.
        crc_base_dir: Path to the .crc directory in CWD.
        remote: Whether to get tasks from remote API.
        api_key: API key for remote queries.
    """
    # 根据remote参数决定从本地还是从远程API获取任务列表
    if remote:
        if not api_key:
            print("错误：需要API密钥来获取远程任务列表")
            return 1
            
        logger.info("开始从远程API获取任务列表...")
        print("从远程API获取任务列表...")
        
        # 调用API获取任务列表，默认获取50条最新的任务
        remote_limit = limit if limit is not None else 50
        all_tasks = fetch_job_list_from_ttapi(api_key, logger, page=1, limit=remote_limit)
        
        if not all_tasks:
            print("无法从远程API获取任务列表，或者远程没有任务。")
            return 1
            
        logger.info(f"成功从远程API获取 {len(all_tasks)} 条任务")
        print(f"成功从远程API获取 {len(all_tasks)} 条任务")
        
        # 标准化远程任务数据
        normalized_tasks = []
        for task in all_tasks:
            normalized = normalize_api_response(logger, task)
            if normalized:
                normalized_tasks.append(normalized)
                
        all_tasks = normalized_tasks
        initial_load_count = len(all_tasks)
    else:
        # 从本地加载任务
        logger.info("开始加载本地任务元数据...")
    metadata_dir = os.path.join(crc_base_dir, 'metadata')
    # Pass metadata_dir to load_all_metadata
    all_tasks = load_all_metadata(logger, metadata_dir)
    initial_load_count = len(all_tasks) if all_tasks else 0
        
    if initial_load_count == 0:
        print("未找到任何任务元数据。")
        return 0

    source_text = "远程API" if remote else "本地元数据"
    logger.info(f"成功从{source_text}加载 {initial_load_count} 条任务元数据")

    # --- 处理列表显示逻辑 (Filtering, Sorting, Limiting, Printing) --- #
    # Use passed arguments directly
    display_limit = limit if limit is not None else 10 # Default limit
    # Handle potential sort alias
    sort_field = 'created_at' if sort_by == 'time' else sort_by
    # Handle potential status alias
    status_filter = None if status and status.lower() == 'all' else status

    filtered_tasks = all_tasks

    # 1. Filtering
    if status_filter:
        logger.debug(f"按状态过滤: {status_filter}")
        status_lower = status_filter.lower()
        filtered_tasks = [t for t in filtered_tasks
                          if str(t.get('status', '')).lower() == status_lower or
                             (status_lower == 'success' and str(t.get('status', '')).lower() == 'completed')]
        if verbose: print(f"DEBUG: 按状态过滤后剩余 {len(filtered_tasks)} 条记录")
    if concept:
        logger.debug(f"按概念过滤: {concept}")
        concept_lower = concept.lower()
        filtered_tasks = [t for t in filtered_tasks if str(t.get('concept', '')).lower() == concept_lower]
        if verbose: print(f"DEBUG: 按概念过滤后剩余 {len(filtered_tasks)} 条记录")
    if not filtered_tasks and (status_filter or concept):
        print("根据当前过滤条件，未找到匹配的任务。")
        return 0

    # 2. Sorting
    sort_key = sort_field
    reverse_sort = not ascending
    logger.debug(f"按 '{sort_key}' 排序，升序: {ascending}")
    if verbose: print(f"DEBUG: 排序键: {sort_key}, 升序: {ascending}")
    def get_sort_value(task):
        value = task.get(sort_key)
        # Adjust timestamp key check if needed
        if sort_key == 'created_at' or sort_key == 'timestamp': # Handle both common keys
            ts_str = task.get('created_at') or task.get('metadata_updated_at') or task.get('metadata_added_at') or task.get('restored_at')
            if ts_str:
                try:
                    # Ensure value is a string before passing to fromisoformat
                    ts_str_val = str(ts_str)
                    # Handle potential variations like 'Z' suffix or microseconds
                    if 'Z' in ts_str_val:
                        ts_str_val = ts_str_val.replace('Z', '+00:00')
                    if '.' in ts_str_val and len(ts_str_val.split('.')[1].split('+')[0]) > 6:
                         ts_str_val = ts_str_val.split('.')[0] + '.' + ts_str_val.split('.')[1][:6] + ts_str_val.split('.')[1][6:].split('+')[1]

                    return datetime.fromisoformat(ts_str_val)
                except (ValueError, TypeError) as dt_err:
                    logger.warning(f"无法解析任务 {task.get('job_id', '')} 的日期时间 '{ts_str}': {dt_err}")
                    return datetime.min # Default for unparseable dates
            return datetime.min # Default for missing dates
        # Ensure we sort strings case-insensitively
        return str(value).lower() if value is not None else ''
    try:
        # 打印前几个任务的排序值
        if filtered_tasks and verbose:
             print("DEBUG: 前几个任务的排序值:")
             for i, t in enumerate(filtered_tasks[:3]):
                 task_id_short = t.get('job_id', 'N/A')[:6]
                 sort_val = get_sort_value(t)
                 debug_msg = f"  - 任务 {i+1}: {sort_val} (ID: {task_id_short})"
                 print(debug_msg) # Print the formatted string

        sorted_tasks = sorted(filtered_tasks, key=get_sort_value, reverse=reverse_sort)
        if verbose: print(f"DEBUG: 排序后的任务数量: {len(sorted_tasks)}")
    except Exception as e: logger.error(f"排序任务时出错: {e}", exc_info=True); print(f"错误：排序任务时发生错误: {e}"); return 1

    # 3. Limiting
    limited_tasks = sorted_tasks[:display_limit]
    logger.debug(f"限制显示最近的 {display_limit} 条记录。")
    if verbose: print(f"DEBUG: 限制后的任务数量: {len(limited_tasks)}")

    # 4. Formatting and Printing with Colors
    if not limited_tasks:
        print("未找到要显示的任务记录。")
        return 0

    print("\n--- 任务列表 ---")
    if verbose: print(f"DEBUG: 找到 {len(limited_tasks)} 条任务记录")

    # Define columns and flexible widths
    cols = ["时间", "ID", "状态", "命令", "概念"]
    col_widths = {"时间": 12, "ID": 7, "状态": 13, "命令": 22, "概念": 12} # Adjusted widths

    if verbose:
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
        try: 
            ts_str_val = str(ts_str)
            if 'Z' in ts_str_val:
                ts_str_val = ts_str_val.replace('Z', '+00:00')
            if '.' in ts_str_val and len(ts_str_val.split('.')[1].split('+')[0]) > 6:
                ts_str_val = ts_str_val.split('.')[0] + '.' + ts_str_val.split('.')[1][:6] + ts_str_val.split('.')[1][6:].split('+')[1]
            dt_obj = datetime.fromisoformat(ts_str_val) if ts_str else None; 
            ts_formatted = dt_obj.strftime("%m/%d %H:%M") if dt_obj else 'N/A'
        except (ValueError, TypeError): ts_formatted = 'Invalid Date'
        row_parts.append(f"{C_BLUE}{ts_formatted:<{col_widths['时间']}}{C_RESET}")

        # Job ID (只显示前6位)
        job_id_str = (task.get('job_id') or 'N/A')[:6]
        row_parts.append(f"{C_CYAN}{job_id_str:<{col_widths['ID']}}{C_RESET}")

        # Status (Colored)
        status_raw = task.get('status') or 'N/A'
        status_color = get_status_color(status_raw)
        status_str = status_raw[:col_widths["状态"]]
        row_parts.append(f"{status_color}{status_str:<{col_widths['状态']}}{C_RESET}")

        # Command/Action
        action = task.get('action', 'create') # Default to 'create' if missing
        action_code = task.get('action_code')
        original_job_id_short = (task.get('original_job_id') or '')[:6]
        cmd_str = action
        if action_code and original_job_id_short:
            # Format action like upscale_a1b2c3d
            cmd_str = f"{action_code}_{original_job_id_short}"
        elif action_code:
            cmd_str = action_code # Fallback if original ID is missing
        cmd_str = cmd_str[:col_widths["命令"]]
        row_parts.append(f"{cmd_str:<{col_widths['命令']}}")

        # Concept
        concept_str = task.get('concept') or 'N/A'
        concept_str = concept_str[:col_widths["概念"]]
        row_parts.append(f"{concept_str:<{col_widths['概念']}}")

        if verbose:
            # Seed
            seed_str = str(task.get('seed', '')) or 'N/A'
            seed_str = seed_str[:col_widths["Seed"]]
            row_parts.append(f"{C_GRAY}{seed_str:<{col_widths['Seed']}}{C_RESET}")

            # Filename
            filename_str = task.get('filename') or 'N/A'
            filename_str = filename_str[:col_widths["文件名"]]
            row_parts.append(f"{C_GRAY}{filename_str:<{col_widths['文件名']}}{C_RESET}")

        print(" | ".join(row_parts))

    print(f"{C_GRAY}{'-' * len(header)}{C_RESET}")
    total_shown = len(limited_tasks)
    total_matching = len(sorted_tasks)
    total_all = initial_load_count
    source_note = "从远程API获取" if remote else "本地元数据中"
    print(f"显示 {total_shown} 条记录 (共匹配 {total_matching} 条，总计 {total_all} 条{source_note})")

    return 0

# --- 移除旧的 add_subparser 函数 --- #
# Subparsers are now handled by Typer in cli.py
