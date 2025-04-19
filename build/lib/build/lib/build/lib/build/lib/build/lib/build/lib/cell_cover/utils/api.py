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
    original_job_id: str,
    action: str,
    hook_url: Optional[str] = None
) -> Optional[str]:
    """调用 TTAPI 的 /action 接口执行操作 (兼容层)"""
    return api_client.call_action_api(
        logger=logger,
        api_key=api_key,
        original_job_id=original_job_id,
        action=action,
        hook_url=hook_url
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

# Example usage (for testing if run directly)
# ... (rest of the file remains the same) 