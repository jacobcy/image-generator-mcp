#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
元数据管理工具 - 兼容层
----------------------
这个模块现在作为兼容层，从拆分后的模块导入并重新导出功能。

新的实现位于:
- image_metadata.py
- restore_metadata.py (包含恢复和同步功能)
"""

import logging

# --- 从新模块导入并重新导出 --- #

from .image_metadata import (
    save_image_metadata,
    find_initial_job_info,
    update_job_metadata,
    upsert_job_metadata,
    load_all_metadata,
    trace_job_history
)

from .restore_metadata import (
    restore_metadata_from_remote,
    sync_tasks,
    normalize_all_metadata_records
)

# --- 清理旧代码 (函数定义已移动) --- #

# logger = logging.getLogger(__name__) # Logger is typically handled by the caller

logger = logging.getLogger(__name__) # Keep a logger instance for potential internal use or debug
logger.debug("metadata_manager: Acting as compatibility layer. Functions imported from submodules.")

# 警告：action_metadata.py 已弃用
# 所有操作元数据现在都保存在 images_metadata.json 中
# 使用 save_image_metadata 函数并传入 action_code 和 original_job_id 参数

# 将所有导入的名称添加到 __all__ 以便 `from .metadata_manager import *` 工作 (如果需要)
__all__ = [
    # 图像元数据操作
    'save_image_metadata',
    'find_initial_job_info',
    'update_job_metadata',
    'upsert_job_metadata',
    'load_all_metadata',
    'trace_job_history',
    
    # 恢复与同步操作
    'restore_metadata_from_remote',
    'sync_tasks',
    'normalize_all_metadata_records',
]

def restore_metadata_from_job_list(logger, job_list_file, image_metadata_file=None):
    """
    从任务列表文件恢复元数据（JSON格式的任务记录列表）。
    此函数将解析任务列表并重建元数据，对于恢复操作很有用。
    
    Args:
        logger: 日志记录器。
        job_list_file: 包含任务记录的JSON文件路径。
        image_metadata_file: 可选，目标元数据文件的路径。
        
    Returns:
        bool: 操作是否成功。
    """
    logger.error("restore_metadata_from_job_list 函数尚未实现")
    return False
