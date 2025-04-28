#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Response Normalization
--------------------------
Utility function for normalizing responses from the TTAPI API.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Note: Removed direct dependency/import of .api_client here as it's no longer needed
# for re-exporting. If normalization logic needs constants from api_client,
# they should be imported directly or passed as arguments.

def normalize_api_response(logger, api_response):
    """
    标准化API响应，过滤并保留需要的字段，去除不必要的字段。

    Args:
        logger: 日志记录器
        api_response: API返回的原始响应

    Returns:
        dict: 标准化后的响应数据，只保留必要字段
    """
    if not api_response or not isinstance(api_response, dict):
        logger.warning("API响应为空或格式不正确")
        return {}

    # 保留的必要字段列表 (移除了 progress, cdnImage)
    necessary_fields = [
        "job_id", "jobId", "status",
        "url", "seed", "prompt", # cdnImage 的值会被赋给 url
        "concept", "variations", "global_styles",
        "action_code", "original_job_id", "action",
        # 保留时间戳字段以便脚本处理
        "created_at", "metadata_updated_at", "metadata_added_at", "restored_at",
        # 保留id字段以便脚本处理
        "id",
        # 保留文件路径信息
        "filename", "filepath"
    ]

    # 移除的不必要字段列表 (供参考，实际通过只复制必要字段实现)
    # remove_fields = [
    #     "components", "discordImage", "hookUrl",
    #     "images", "width", "height", "quota", "progress", "cdnImage"
    # ]

    # 创建新的标准化响应
    normalized = {}

    # 复制必要字段
    for field in necessary_fields:
        if field in api_response:
            normalized[field] = api_response[field]

    # 确保job_id格式统一
    if "jobId" in api_response and "job_id" not in normalized:
        normalized["job_id"] = api_response["jobId"]
    # 显式移除jobId字段
    if "jobId" in normalized:
        del normalized["jobId"]

    # 确保URL字段统一 (从cdnImage复制)
    if "cdnImage" in api_response and "url" not in normalized:
        normalized["url"] = api_response["cdnImage"]
    # 显式移除cdnImage字段 (即使它不在necessary_fields里，以防万一)
    if "cdnImage" in normalized:
        del normalized["cdnImage"]

    # 标准化状态字段
    if "status" in normalized:
        # 将 SUCCESS 和 True (可能存在的旧格式) 都转为 completed
        if isinstance(normalized["status"], str) and normalized["status"].upper() == "SUCCESS":
            normalized["status"] = "completed"
        elif isinstance(normalized["status"], bool) and normalized["status"] is True:
             normalized["status"] = "completed"
        # 保留 FAILED 状态
        elif isinstance(normalized["status"], str) and normalized["status"].upper() == "FAILED":
            normalized["status"] = "FAILED"

    # --- 设置 action 字段 --- #
    action_code = normalized.get('action_code')
    original_job_id = normalized.get('original_job_id')

    if original_job_id and action_code:
        # Action Job: action = {action_code}_{short_id}
        short_orig_id = original_job_id[:6]
        normalized['action'] = f"{action_code}_{short_orig_id}"
        # action_code 保持不变 (从必要字段复制而来)
    elif original_job_id and not action_code:
        # 有 original_id 但无 action_code (异常情况?)
        short_orig_id = original_job_id[:6]
        normalized['action'] = f"unknown_action_{short_orig_id}"
        normalized['action_code'] = None # 明确 action_code 为 None
    else:
        # 原生任务 (无 original_job_id): action = 'create'
        normalized['action'] = 'create'
        normalized['action_code'] = None # 明确 action_code 为 None

    # 保留原始更新时间戳，或添加新的
    if "metadata_updated_at" not in normalized:
        normalized["metadata_updated_at"] = datetime.now().isoformat()

    # logger.debug(f"API响应标准化结果: {normalized}") # 在脚本中打印更清晰
    return normalized

# Example usage (for testing if run directly)
# ... (rest of the file remains the same)