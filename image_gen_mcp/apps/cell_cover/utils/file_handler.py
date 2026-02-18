#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File and Directory Handling Utilities
------------------------------------
Functions for managing directories and files.

Metadata handling functions have been moved to:
- cell_cover/utils/image_metadata.py
- cell_cover/utils/restore_metadata.py

This module now focuses on filesystem operations like
directory creation and filename sanitization.
"""

import os
import logging
import re
import shutil
import logging
from datetime import datetime
from typing import Dict, Any

# --- Constants --- #

# Define directory paths relative to the script's location (utils/)
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(UTILS_DIR) # Assumes utils is one level down

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
IMAGE_DIR = os.path.join(BASE_DIR, "images")
META_DIR = os.path.join(BASE_DIR, "metadata")
LOG_DIR = os.path.join(BASE_DIR, "logs") # Added logs directory
MAX_FILENAME_LENGTH = 200 # Define a max filename length

# --- Helper Functions --- #

def sanitize_filename(name):
    """Sanitizes a string to be safe for use as a filename."""
    if not isinstance(name, str):
        name = str(name) # Ensure it's a string
    # Remove characters not suitable for filenames
    name = re.sub(r'[\\/*?"<>|:]', '', name) # Simpler regex for invalid chars
    # Replace spaces and other separators with underscores
    name = re.sub(r'[\s._-]+', "_", name)
    # Ensure it's not empty after sanitization
    if not name:
        name = "sanitized_empty"
    # Limit length
    return name[:MAX_FILENAME_LENGTH]

def ensure_directories(logger, dirs=None, base_dir=None):
    """确保必要的目录存在

    Args:
        logger: The logging object.
        dirs: A list of directory paths to ensure. Defaults to standard project dirs.
        base_dir: Optional base directory to use instead of the default BASE_DIR.
    """
    default_dirs = [OUTPUT_DIR, IMAGE_DIR, META_DIR, LOG_DIR]
    
    # Determine the list of directories to check/create
    dirs_to_check = []
    if base_dir:
        if dirs is None:
            # Use default directory names relative to the provided base_dir
            dirs_to_check = [os.path.join(base_dir, os.path.basename(d)) for d in default_dirs]
        else:
            # Use the provided list of dirs relative to the base_dir
            dirs_to_check = [os.path.join(base_dir, d) for d in dirs]
    elif dirs is None:
        # Use the default directories defined by constants
        dirs_to_check = default_dirs
    else:
        # Use the provided list of dirs (absolute or relative to current execution)
        dirs_to_check = dirs

    logger.debug(f"检查并创建目录: {dirs_to_check}")
    all_created = True
    for directory in dirs_to_check:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"创建目录: {directory}")
                # Optionally print for direct user feedback
                # print(f"创建目录: {directory}")
            except OSError as e:
                logger.error(f"警告：无法创建目录 {directory} - {e}")
                # Optionally print for direct user feedback
                # print(f"警告：无法创建目录 {directory} - {e}")
                all_created = False # Mark as failed if any dir creation fails
        else:
            logger.debug(f"目录已存在: {directory}")
    return all_created # Return status

# --- 文件名生成辅助函数 --- #

def _generate_expected_filename(logger: logging.Logger, task_data: Dict[str, Any], all_tasks_index: Dict[str, Dict[str, Any]]) -> str:
    """
    根据规范生成期望的文件名。
    使用已规范化的任务数据（包含action和concept字段）。
    使用 task_data['created_at'] 作为主要的时间戳来源。

    Args:
        logger: 日志记录器
        task_data: 已规范化的任务数据（包含action和concept字段）
        all_tasks_index: 所有任务的索引（用于兼容旧接口，实际上不再使用）

    Returns:
        str: 生成的标准文件名
    """
    job_id = task_data.get('job_id', 'nojobid') # 获取 job_id 用于日志

    # --- 使用 created_at 作为时间戳 --- #
    created_at_str = task_data.get('created_at')
    timestamp = None
    if created_at_str:
        try:
            # 尝试解析ISO格式的时间戳
            dt_obj = datetime.fromisoformat(str(created_at_str))
            timestamp = dt_obj.strftime("%Y%m%d_%H%M%S")
            logger.debug(f"Task {job_id[:6]} 使用 created_at ({created_at_str}) 生成时间戳: {timestamp}")
        except ValueError as e:
            logger.warning(f"Task {job_id[:6]} 的 created_at 字段 ('{created_at_str}') 格式无效: {e}，将使用当前时间作为时间戳")
            # 可以选择尝试解析其他格式，或者直接使用当前时间
    else:
        logger.warning(f"Task {job_id[:6]} 缺少 created_at 字段，将使用当前时间作为时间戳")

    # 如果无法从 created_at 获取时间戳，则使用当前时间作为后备
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.debug(f"Task {job_id[:6]} 回退使用当前时间生成时间戳: {timestamp}")
    # ---------------------------------- #
    
    job_id_part = job_id[:6] # 已在前面获取
    filename = ""
    prefix = task_data.get("prefix", "") # 处理来自recreate的可能前缀

    action_code = task_data.get('action_code')
    original_job_id = task_data.get('original_job_id')

    # 获取task_data中的action字段
    action = task_data.get('action', 'unknown')

    # 清理变体和风格
    variations = task_data.get('variations', [])
    styles = task_data.get('global_styles', [])
    # 确保variations/styles是列表
    clean_variations = [v for v in variations if v] if isinstance(variations, list) else ([variations] if variations else [])
    clean_styles = [s for s in styles if s] if isinstance(styles, list) else ([styles] if styles else [])

    if action_code and original_job_id:
        # --- Action 任务命名 --- #
        # 直接使用 task_data 中的 concept (应已由 normalize_task_metadata 处理)
        concept = task_data.get('concept')
        # 如果 concept 为空或 None，设为 unknown
        if not concept:
            concept = "unknown"

        base_concept = sanitize_filename(concept)
        orig_job_id_part = original_job_id[:6]
        safe_action = sanitize_filename(action) # 使用action字段
        filename = f"{prefix}{base_concept}-{orig_job_id_part}-{safe_action}-{timestamp}.png"
    else:
        # --- 原始任务命名 --- #
        concept = task_data.get('concept')
        if not concept:
            concept = "unknown"

        base_concept = sanitize_filename(concept)
        parts = [prefix + base_concept, job_id_part]
        if clean_variations:
            parts.append("-".join(map(sanitize_filename, clean_variations)))
        if clean_styles:
            parts.append("-".join(map(sanitize_filename, clean_styles)))
        parts.append(timestamp)
        filename = "-".join(parts) + ".png"

    # 限制整体文件名长度
    filename = filename[:MAX_FILENAME_LENGTH]
    if not filename.lower().endswith('.png'):
         filename = filename[:MAX_FILENAME_LENGTH - 4] + ".png"

    return filename