#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
元数据恢复与同步工具
------------------
1. 从TTAPI获取的任务列表恢复本地缺失的元数据
2. 同步本地状态不确定的任务和引用但找不到的源任务
"""

import os
import json
import uuid
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# 从其他utils模块导入常量和函数
from .filesystem_utils import (
    ensure_directories, write_last_succeed_job_id,
    sanitize_filename
)
from .file_handler import MAX_FILENAME_LENGTH
from .image_metadata import (
    _load_metadata_file, _save_metadata_file, 
    update_job_metadata, upsert_job_metadata,
    load_all_metadata,
    _build_metadata_index,
    trace_job_history,
    remove_job_metadata
)
from .log import setup_logging
# 区分 api.py (包含 normalize_api_response) 和 api_client.py (包含实际 API 调用)
from .api import normalize_api_response
from .api_client import poll_for_result
# from .api import poll_for_result, normalize_api_response # 旧的导入方式
from .image_handler import download_and_save_image

# 定义 METADATA_FILENAME 本地
METADATA_FILENAME = 'images_metadata.json'  # 直接在本文件中定义

# 定义 META_DIR 本地
META_DIR = 'metadata'  # 直接在本文件中定义

# 定义 IMAGE_DIR 本地
IMAGE_DIR = 'images'  # 直接在本文件中定义

def restore_metadata_from_remote(logger: logging.Logger, job_list: List[Dict[str, Any]], api_key: Optional[str] = None) -> Optional[int]:
    """从TTAPI获取的任务列表恢复本地缺失的元数据。
    
    Args:
        logger: 日志记录器
        job_list: 从TTAPI获取的任务列表
        api_key: API密钥，用于获取更多任务详情（可选）
    
    Returns:
        int: 恢复的记录数，如果发生错误则返回None
    """
    target_filename = METADATA_FILENAME
    logger.info(f"开始从TTAPI任务列表恢复缺失的元数据到{target_filename}...")

    # 1. 加载现有的本地元数据
    all_tasks = load_all_metadata(logger)
    if all_tasks is None:
        logger.critical("无法加载本地元数据，无法继续恢复操作")
        return None

    # 2. 构建任务ID索引
    existing_job_ids = {task.get('job_id') for task in all_tasks if task.get('job_id')}
    logger.info(f"已加载{len(existing_job_ids)}条现有本地元数据记录")

    # 3. 处理远程任务列表，找出缺失的任务
    restored_count = 0
    for remote_task in job_list:
        job_id = remote_task.get("job_id") or remote_task.get("jobId")
        if not job_id:
            logger.warning("远程任务缺少job_id，跳过")
            continue
            
        # 如果任务在本地不存在，则恢复
        if job_id not in existing_job_ids:
            # 标准化API响应
            normalized_data = normalize_api_response(logger, remote_task)
            if not normalized_data:
                logger.warning(f"无法标准化任务{job_id}的数据，跳过")
                continue
                
            # 确保有job_id
            normalized_data["job_id"] = job_id
            
            # 如果需要并且有API密钥，获取更多任务详情
            if api_key and normalized_data.get("status") == "completed":
                try:
                    logger.info(f"从API获取任务{job_id}的详细信息...")
                    poll_response = poll_for_result(logger, job_id, api_key)

                    if poll_response:
                        final_status, api_data = poll_response
                        
                        # Only update if poll succeeded and status is still relevant
                        if final_status == "SUCCESS" and isinstance(api_data, dict):
                            # 更新标准化数据 - Use api_data
                            api_normalized = normalize_api_response(logger, api_data)
                            if api_normalized:
                                normalized_data.update(api_normalized)
                                logger.debug(f"任务 {job_id} 的元数据已使用轮询结果更新。")
                            else:
                                logger.warning(f"无法标准化来自 poll_for_result 的任务 {job_id} 数据。")
                        elif final_status == "FAILED":
                            logger.warning(f"轮询任务 {job_id} 时发现其状态为 FAILED，将跳过更新，后续 sync 可能移除。")
                            # Optionally update local status to FAILED here?
                            # update_job_metadata(logger, job_id, {'status': 'FAILED'}) # Consider this
                        else:
                             logger.warning(f"轮询任务 {job_id} 未成功或状态非 SUCCESS (状态: {final_status})。")
                    else:
                        logger.warning(f"轮询任务 {job_id} 失败或超时，无法获取详细信息。")

                except Exception as e:
                    logger.warning(f"获取任务{job_id}的详情时出错: {str(e)}")
            
            # 添加恢复标记
            normalized_data["restored_at"] = datetime.now().isoformat()
            
            # 如果没有concept，设置为"restored"
            if not normalized_data.get("concept"):
                normalized_data["concept"] = "restored"
                
            # 保存到元数据
            success = upsert_job_metadata(logger, job_id, normalized_data)
            if success:
                restored_count += 1
                logger.info(f"已恢复任务{job_id}的元数据")
                
                # 如果有图像URL，尝试下载
                image_url = normalized_data.get("url")
                if image_url and api_key:
                    try:
                        # 收集下载所需信息
                        prompt_text = normalized_data.get("prompt", f"Job: {job_id}")
                        concept = normalized_data.get("concept", "restored")
                        variations = normalized_data.get("variations", "")
                        styles = normalized_data.get("global_styles", "")
                        original_job_id = normalized_data.get("original_job_id")
                        action_code = normalized_data.get("action_code")
                        
                        # 下载图像
                        download_success, saved_path, _ = download_and_save_image(
                            logger,
                            image_url,
                            job_id,
                            prompt_text,
                            concept,
                            variations,
                            styles,
                            original_job_id,
                            action_code,
                            None,  # 不传递components
                            normalized_data.get("seed")
                        )
                        
                        if download_success:
                            logger.info(f"已下载并保存任务{job_id}的图像: {saved_path}")
                            # 记录成功任务ID
                            write_last_succeed_job_id(logger, job_id)
                    except Exception as e:
                        logger.warning(f"下载任务{job_id}的图像时出错: {str(e)}")
            else:
                logger.error(f"保存任务{job_id}的元数据失败")

    logger.info(f"共恢复了{restored_count}个任务的元数据")
    return restored_count
