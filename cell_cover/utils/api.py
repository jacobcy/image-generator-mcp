#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TTAPI API Interface
------------------
High-level interface for interacting with TTAPI Midjourney endpoints.
This module provides a compatibility layer and additional functionality
on top of the low-level api_client module.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from . import api_client

# Re-export constants for backward compatibility
TTAPI_BASE_URL = api_client.TTAPI_BASE_URL
POLL_INTERVAL_SECONDS = api_client.POLL_INTERVAL_SECONDS
FETCH_TIMEOUT_SECONDS = api_client.FETCH_TIMEOUT_SECONDS
MAX_POLL_ATTEMPTS = api_client.MAX_POLL_ATTEMPTS

# Re-export functions with additional functionality or compatibility layer
def call_imagine_api(
    logger: logging.Logger,
    prompt_data: dict,
    api_key: str,
    hook_url: Optional[str] = None,
    notify_id: Optional[str] = None,
    cref_url: Optional[str] = None
) -> Optional[str]:
    """调用 TTAPI 的 /imagine 接口提交任务 (兼容层)"""
    return api_client.call_imagine_api(
        logger=logger,
        prompt_data=prompt_data,
        api_key=api_key,
        hook_url=hook_url,
        notify_id=notify_id,
        cref_url=cref_url
    )

def poll_for_result(
    logger: logging.Logger,
    job_id: str,
    api_key: str,
    poll_interval: int = POLL_INTERVAL_SECONDS,
    timeout: int = FETCH_TIMEOUT_SECONDS,
    max_retries_per_poll: int = 1
) -> Optional[Dict[str, Any]]:
    """轮询 /fetch 接口获取任务结果 (兼容层)"""
    return api_client.poll_for_result(
        logger=logger,
        job_id=job_id,
        api_key=api_key,
        poll_interval=poll_interval,
        timeout=timeout,
        max_retries_per_poll=max_retries_per_poll
    )

def fetch_job_list_from_ttapi(
    api_key: str,
    logger: logging.Logger,
    page: int = 1,
    limit: int = 10
) -> Optional[List[Dict[str, Any]]]:
    """从 TTAPI 获取任务列表 (兼容层)"""
    return api_client.fetch_job_list_from_ttapi(
        api_key=api_key,
        logger=logger,
        page=page,
        limit=limit
    )

def call_action_api(
    logger: logging.Logger,
    api_key: str,
    job_id: str,
    action_code: str,
    hook_url: Optional[str] = None,
    mode: Optional[str] = None
) -> Optional[str]:
    """调用 TTAPI 的 /action 接口执行操作 (兼容层)

    Args:
        logger: 日志记录器。
        api_key: TTAPI 密钥。
        job_id: 要执行操作的任务 ID。
        action_code: 要执行的具体操作名称 (例如 'upsample1', 'variation2')。
        hook_url: Webhook 回调地址 (可选)。
        mode: Optional[str]: The mode for the action

    Returns:
        Optional[str]: 如果提交成功，返回 Job ID (通常与输入 job_id 相同)；否则返回 None。
    """
    return api_client.call_action_api(
        logger=logger,
        api_key=api_key,
        original_job_id=job_id,
        action=action_code,
        hook_url=hook_url,
        mode=mode
    )

def fetch_seed_from_ttapi(
    logger: logging.Logger,
    api_key: str,
    job_id: str
) -> Optional[int]:
    """从 TTAPI 获取任务的 seed 值 (兼容层)"""
    return api_client.fetch_seed_from_ttapi(
        logger=logger,
        api_key=api_key,
        job_id=job_id
    )

def check_prompt(
    logger: logging.Logger,
    prompt: str,
    api_key: str
) -> bool:
    """检查提示词是否违规 (兼容层)"""
    return api_client.check_prompt(
        logger=logger,
        prompt=prompt,
        api_key=api_key
    )

def call_blend_api(
    logger: logging.Logger,
    api_key: str,
    img_base64_array: List[str],
    dimensions: Optional[str] = None,
    mode: Optional[str] = None,
    hook_url: Optional[str] = None,
    get_u_images: Optional[bool] = None
) -> Optional[str]:
    """调用 TTAPI 的 /blend 接口提交任务 (兼容层)"""
    return api_client.call_blend_api(
        logger=logger,
        api_key=api_key,
        img_base64_array=img_base64_array,
        dimensions=dimensions,
        mode=mode,
        hook_url=hook_url,
        get_u_images=get_u_images
    )

def call_describe_api(*args, **kwargs):
    """调用 /describe API (兼容层)"""
    return api_client.call_describe_api(*args, **kwargs)

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
    
    # 保留原始更新时间戳，或添加新的
    if "metadata_updated_at" not in normalized:
        normalized["metadata_updated_at"] = datetime.now().isoformat()
    
    # logger.debug(f"API响应标准化结果: {normalized}") # 在脚本中打印更清晰
    return normalized

# Example usage (for testing if run directly)
# ... (rest of the file remains the same) 