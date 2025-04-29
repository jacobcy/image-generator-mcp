#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图像元数据管理
---------------
处理 images_metadata.json 文件的读写和查询功能。
"""

import os
import json
import uuid
import logging
import shutil
from datetime import datetime
from typing import Optional, Dict, Any

# 从 filesystem_utils 导入常量和函数
from .filesystem_utils import (
    ensure_directories, sanitize_filename
)

# 导入 API 响应标准化函数
from .api import normalize_api_response

# 注意：原本 save_image_metadata/update_job_metadata/upsert_job_metadata 中包含 print 语句
# 为了让模块更纯粹，这些 print 语句可以移除，仅保留 logger 输出。
# 调用这些函数的地方（例如 command handlers）可以在操作后打印用户反馈。

def _load_metadata_file(logger, metadata_dir: str, target_filename: str = "images_metadata.json"):
    """内部辅助函数：安全地加载元数据文件 (期望是包含 'images' 列表的字典)。

    Args:
        logger: 日志记录器。
        metadata_dir: 元数据文件所在的目录。
        target_filename: 元数据文件的名称 (默认为 images_metadata.json)。
    
    Returns:
        tuple: (metadata_data, load_error, backup_filename)
    """
    metadata_data = None
    load_error = False
    backup_filename = ""
    # Construct full path
    full_filepath = os.path.join(metadata_dir, target_filename)

    try:
        # Ensure directory exists first
        if not ensure_directories(logger, metadata_dir):
             logger.error(f"元数据目录 {metadata_dir} 不存在且无法创建，无法加载元数据。")
             return None, True, "" # Indicate load error

        if os.path.exists(full_filepath):
            if os.path.getsize(full_filepath) > 0:
                with open(full_filepath, 'r', encoding='utf-8') as f:
                    try:
                        loaded_data = json.load(f)
                        if isinstance(loaded_data, dict) and "images" in loaded_data and isinstance(loaded_data["images"], list):
                            metadata_data = loaded_data
                            logger.debug(f"成功加载现有元数据 ({full_filepath})，包含 {len(metadata_data.get('images', []))} 个条目")
                        else:
                            logger.error(f"元数据文件 {full_filepath} 格式无效 (不是包含 'images' 列表的字典)。")
                            load_error = True
                    except json.JSONDecodeError as e:
                        logger.error(f"解析元数据文件 {full_filepath} 时出错 ({e})。")
                        load_error = True
            else:
                logger.info(f"元数据文件 {full_filepath} 为空，将创建新结构。")
                metadata_data = {"images": [], "version": "1.0"} # Initialize
        else:
            logger.info(f"元数据文件 {full_filepath} 不存在，将创建新结构。")
            metadata_data = {"images": [], "version": "1.0"} # Initialize

    except IOError as e:
        logger.error(f"读取元数据文件 {full_filepath} 时发生 IO 错误: {e}")
        load_error = True
    except Exception as e:
        logger.error(f"加载元数据文件 {full_filepath} 时发生意外错误: {e}", exc_info=True)
        load_error = True

    if load_error and os.path.exists(full_filepath):
        # Backup the problematic file
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{full_filepath}.bak.{timestamp}"
            shutil.move(full_filepath, backup_filename)
            logger.info(f"已将损坏/无效的元数据文件备份到: {backup_filename}")
            # After backup, initialize fresh structure
            metadata_data = {"images": [], "version": "1.0"}
            load_error = False # Allow proceeding with fresh structure
        except Exception as backup_e:
            logger.error(f"尝试备份损坏/无效的元数据文件失败: {backup_e}")
            # Keep load_error=True, cannot proceed safely
            metadata_data = None

    # If metadata_data is still None after attempting load/init, it's a critical error
    if metadata_data is None and not load_error:
        logger.critical("内部错误：无法加载或初始化元数据结构。")
        load_error = True

    return metadata_data, load_error, backup_filename

def _save_metadata_file(logger, metadata_dir: str, metadata_data: dict, target_filename: str = "images_metadata.json"):
    """内部辅助函数：安全地将元数据字典写入文件。

    Args:
        logger: 日志记录器。
        metadata_dir: 元数据文件所在的目录。
        metadata_data: 要保存的元数据字典。
        target_filename: 元数据文件的名称 (默认为 images_metadata.json)。

    Returns:
        bool: 是否保存成功。
    """
    # Construct full path
    full_filepath = os.path.join(metadata_dir, target_filename)
    temp_filename = full_filepath + ".tmp"

    # Ensure directory exists before writing
    if not ensure_directories(logger, metadata_dir):
         logger.error(f"元数据目录 {metadata_dir} 不存在且无法创建，无法保存元数据。")
         return False

    try:
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=4, ensure_ascii=False)
        os.replace(temp_filename, full_filepath)
        logger.info(f"元数据已成功写入: {full_filepath}")
        return True
    except (IOError, OSError) as e:
        logger.error(f"无法写入元数据文件 {full_filepath}: {e}")
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except OSError as rem_e: logger.error(f"删除临时文件 {temp_filename} 失败: {rem_e}")
        return False
    except Exception as e:
        logger.error(f"保存元数据时发生意外错误: {e}", exc_info=True)
        return False

def save_image_metadata(logger, image_id, job_id, filename, filepath, url, prompt, concept,
                       metadata_dir: str, # Added metadata_dir
                       variations=None, global_styles=None, components=None, seed=None, original_job_id=None,
                       action_code: Optional[str] = None,
                       status: Optional[str] = None):
    """保存初始图像元数据到 images_metadata.json 文件 (安全模式)。

    Args:
        logger: The logging object.
        image_id: The ID of the image.
        job_id: The ID of the job associated with the image.
        filename: The filename of the image.
        filepath: The path to the image file.
        url: The URL of the image.
        prompt: The prompt used to generate the image.
        concept: The concept associated with the image.
        variations: 变体字符串，例如 "variation1"。
        global_styles: 全局样式字符串，例如 "palette_bw_gold"。
        components: DEPRECATED - Components data from API response (no longer stored).
        seed: Seed value from API response.
        original_job_id: The ID of the original job (for action results).
        action_code: The action code that was applied.
        status: The status of the job.
        metadata_dir: The directory containing the images_metadata.json file.
    """
    metadata_filename = "images_metadata.json"
    logger.info(f"准备保存初始图像元数据到 {os.path.join(metadata_dir, metadata_filename)}，Job ID: {job_id}")

    # Pass metadata_dir and filename to _load_metadata_file
    metadata_data, load_error, backup_file = _load_metadata_file(logger, metadata_dir, metadata_filename)

    if load_error or metadata_data is None:
        logger.critical(f"无法加载或初始化元数据，无法保存新记录。{(' 备份文件: ' + backup_file) if backup_file else ''}")
        return False

    # Check if job_id already exists to perform an update instead of append
    existing_index = -1
    if "images" in metadata_data:
        for i, job in enumerate(metadata_data["images"]):
            if job.get("job_id") == job_id:
                existing_index = i
                logger.info(f"找到 Job ID {job_id} 的现有记录，将执行更新。")
                break

    # 构建初始元数据字典
    image_metadata = {
        "id": image_id or str(uuid.uuid4()), # Ensure local ID exists
        "job_id": job_id,
        "filename": filename,
        "filepath": filepath,
        "url": url,
        "prompt": prompt,
        "concept": concept,
        "variations": variations or "", # 改为字符串，默认为空字符串
        "global_styles": global_styles or "", # 改为字符串，默认为空字符串
        "seed": seed,
        "original_job_id": original_job_id, # Include original_job_id
        "action_code": action_code, # Include action_code
        "status": status or (existing_index != -1 and metadata_data["images"][existing_index].get("status")) # Preserve existing status unless new one provided
    }

    # 使用 normalize_api_response 标准化元数据
    # 注意：normalize_api_response 会移除 None 值和不必要的字段
    normalized_metadata = normalize_api_response(logger, image_metadata)

    # 确保关键字段存在
    if "job_id" not in normalized_metadata:
        normalized_metadata["job_id"] = job_id
    if "id" not in normalized_metadata:
        normalized_metadata["id"] = image_id or str(uuid.uuid4())

    if existing_index != -1:
        # Update existing record
        logger.debug("更新现有元数据条目")
        metadata_data["images"][existing_index].update(normalized_metadata)
        # Update timestamp
        metadata_data["images"][existing_index]["metadata_updated_at"] = datetime.now().isoformat()
    else:
        # Append new record
        logger.debug("追加新的初始元数据条目")
        # Add created_at timestamp for new records
        normalized_metadata["created_at"] = datetime.now().isoformat()
        # Ensure 'images' list exists
        if "images" not in metadata_data:
            metadata_data["images"] = []
        metadata_data["images"].append(normalized_metadata)

    logger.debug(f"准备写入 {len(metadata_data['images'])} 条记录")

    # Pass metadata_dir and filename to _save_metadata_file
    if _save_metadata_file(logger, metadata_dir, metadata_data, metadata_filename):
        action_desc = "更新" if existing_index != -1 else "保存"
        logger.info(f"成功 {action_desc} Job ID {job_id} 的元数据。")
        return True
    else:
        logger.error(f"保存 Job ID {job_id} 的元数据失败。")
        return False

def find_initial_job_info(logger, identifier: str, metadata_dir: str):
    """在 images_metadata.json 中根据标识符查找初始任务信息。

    Args:
        logger: 日志记录器。
        identifier: 要查找的标识符 (Job ID, 前缀, 或文件名)。
        metadata_dir: 元数据文件所在的目录。

    Returns:
        Optional[dict]: 找到的任务信息，或 None。
    """
    metadata_filename = "images_metadata.json"
    full_filepath = os.path.join(metadata_dir, metadata_filename)
    logger.info(f"在 {full_filepath} 中查找标识符 '{identifier}' 对应的任务...")

    # Pass metadata_dir and filename to _load_metadata_file
    metadata_data, load_error, _ = _load_metadata_file(logger, metadata_dir, metadata_filename)

    if load_error or metadata_data is None or "images" not in metadata_data:
        logger.error("无法加载或解析元数据，无法执行查找。")
        return None

    found_job = None
    search_mode = ""

    # 1. Check for full Job ID (UUID)
    if len(identifier) == 36 and '-' in identifier:
        search_mode = "完整 Job ID"
        logger.debug(f"按 {search_mode} 查找...")
        for job in metadata_data["images"]:
            if job.get("job_id") == identifier:
                found_job = job
                break

    # 2. Check for Job ID prefix (e.g., 6 chars) - adjust length if needed
    elif len(identifier) == 6: # Example prefix length
        search_mode = "Job ID 前缀"
        logger.debug(f"按 {search_mode} 查找...")
        possible_matches = [job for job in metadata_data["images"] if job.get("job_id", "").startswith(identifier)]
        if len(possible_matches) == 1:
            found_job = possible_matches[0]
        elif len(possible_matches) > 1:
            logger.error(f"找到多个 Job ID 前缀为 '{identifier}' 的任务，请提供更明确的标识。")
            for match in possible_matches: logger.error(f"  - Job ID: {match.get('job_id')}, Filename: {match.get('filename')}")
            return None

    # 3. Assume filename if not found by ID/prefix
    if not found_job and not search_mode:
        search_mode = "文件名"
        logger.debug(f"按 {search_mode} 查找...")
        normalized_identifier = identifier.lower().removesuffix('.png')
        for job in metadata_data["images"]:
            stored_filename = job.get("filename", "").lower().removesuffix('.png')
            if stored_filename == normalized_identifier:
                found_job = job
                break

    if found_job:
        logger.info(f"通过 {search_mode} 找到匹配的任务: {found_job.get('job_id')}")
        return found_job
    else:
        logger.warning(f"在元数据中未能根据标识符 '{identifier}' ({search_mode or '文件名'} 模式) 找到唯一的任务。")
        return None

def update_job_metadata(logger, job_id_to_update: str, updates: Dict[str, Any], metadata_dir: str):
    """更新指定 Job ID 的元数据。

    Args:
        logger: 日志记录器。
        job_id_to_update: 要更新的 Job ID。
        updates: 包含要更新的字段和值的字典。
        metadata_dir: 元数据文件所在的目录。

    Returns:
        bool: 操作是否成功。
    """
    metadata_filename = "images_metadata.json"
    full_filepath = os.path.join(metadata_dir, metadata_filename)
    logger.info(f"准备在 {full_filepath} 中更新 Job ID {job_id_to_update[:6]}... 的元数据")

    # Pass metadata_dir and filename to _load_metadata_file
    metadata_data, load_error, backup_file = _load_metadata_file(logger, metadata_dir, metadata_filename)

    if load_error or metadata_data is None or "images" not in metadata_data:
        logger.error(f"无法加载元数据，无法执行更新。{(' 备份文件: ' + backup_file) if backup_file else ''}")
        return False

    updated = False
    for job in metadata_data["images"]:
        if job.get("job_id") == job_id_to_update:
            cleaned_updates = normalize_api_response(logger, updates)
            job.update(cleaned_updates)
            job["metadata_updated_at"] = datetime.now().isoformat()
            logger.debug(f"更新了 Job ID {job_id_to_update[:6]} 的字段: {list(cleaned_updates.keys())}")
            updated = True
        break

    if not updated:
        logger.warning(f"未找到 Job ID {job_id_to_update[:6]}，无法更新元数据。")
        return False

    # Pass metadata_dir and filename to _save_metadata_file
    if _save_metadata_file(logger, metadata_dir, metadata_data, metadata_filename):
        logger.info(f"成功更新了 Job ID {job_id_to_update[:6]} 的元数据。")
        return True
    else:
        logger.error(f"写入更新后的元数据失败 (Job ID: {job_id_to_update[:6]})。")
        return False

def upsert_job_metadata(logger, job_id_to_upsert: str, new_data: Dict[str, Any], metadata_dir: str):
    """插入或更新指定 Job ID 的元数据。

    Args:
        logger: 日志记录器。
        job_id_to_upsert: 要插入或更新的 Job ID。
        new_data: 完整的任务数据字典。
        metadata_dir: 元数据文件所在的目录。

    Returns:
        bool: 操作是否成功。
    """
    metadata_filename = "images_metadata.json"
    full_filepath = os.path.join(metadata_dir, metadata_filename)
    logger.info(f"准备在 {full_filepath} 中 Upsert Job ID {job_id_to_upsert[:6]}... 的元数据")

    # Pass metadata_dir and filename to _load_metadata_file
    metadata_data, load_error, backup_file = _load_metadata_file(logger, metadata_dir, metadata_filename)

    if load_error or metadata_data is None:
        logger.critical(f"无法加载或初始化元数据，无法执行 Upsert。{(' 备份文件: ' + backup_file) if backup_file else ''}")
        return False

    # Ensure 'images' list exists
    if "images" not in metadata_data:
        metadata_data["images"] = []

    # Clean the incoming data using normalize_api_response
    # This ensures consistency and removes unwanted fields/None values
    normalized_new_data = normalize_api_response(logger, new_data)
    # Ensure job_id is present after normalization
    normalized_new_data['job_id'] = job_id_to_upsert
    if 'id' not in normalized_new_data or not normalized_new_data['id']:
         normalized_new_data['id'] = str(uuid.uuid4()) # Ensure local ID

    found_index = -1
    for i, job in enumerate(metadata_data["images"]):
        if job.get("job_id") == job_id_to_upsert:
            found_index = i
            break

    if found_index != -1:
        # Update existing
        logger.debug(f"Upsert: 更新 Job ID {job_id_to_upsert[:6]} (索引 {found_index})")
        # Preserve created_at if it exists in the old record but not the new
        if 'created_at' not in normalized_new_data and 'created_at' in metadata_data["images"][found_index]:
             normalized_new_data['created_at'] = metadata_data["images"][found_index]['created_at']
        # Merge updates into the existing record
        metadata_data["images"][found_index].update(normalized_new_data)
        # Add/update timestamp
        metadata_data["images"][found_index]["metadata_updated_at"] = datetime.now().isoformat()
    else:
        # Insert new
        logger.debug(f"Upsert: 插入新的 Job ID {job_id_to_upsert[:6]}")
        # Add created_at if missing
        if 'created_at' not in normalized_new_data:
            normalized_new_data["created_at"] = datetime.now().isoformat()
        metadata_data["images"].append(normalized_new_data)

    # Pass metadata_dir and filename to _save_metadata_file
    if _save_metadata_file(logger, metadata_dir, metadata_data, metadata_filename):
        action_desc = "更新" if found_index != -1 else "插入"
        logger.info(f"成功 {action_desc} 了 Job ID {job_id_to_upsert[:6]} 的元数据。")
        return True
    else:
        logger.error(f"写入 Upsert 后的元数据失败 (Job ID: {job_id_to_upsert[:6]})。")
        return False

def load_all_metadata(logger, metadata_dir: str):
    """加载所有元数据记录。

    Args:
        logger: 日志记录器。
        metadata_dir: 元数据文件所在的目录。

    Returns:
        list: 包含所有图像元数据的列表，如果失败则返回空列表。
    """
    metadata_filename = "images_metadata.json"
    full_filepath = os.path.join(metadata_dir, metadata_filename)
    logger.info(f"尝试从 {full_filepath} 加载所有元数据...")

    # Pass metadata_dir and filename to _load_metadata_file
    metadata_data, load_error, backup_file = _load_metadata_file(logger, metadata_dir, metadata_filename)

    if load_error or metadata_data is None:
        logger.error(f"加载元数据失败。{(' 备份文件: ' + backup_file) if backup_file else ''}")
        return [] # Return empty list on failure
    
    if "images" not in metadata_data or not isinstance(metadata_data["images"], list):
        logger.warning(f"元数据文件 {full_filepath} 缺少 'images' 列表或格式错误。返回空列表。")
        return []

    logger.info(f"成功加载 {len(metadata_data['images'])} 条元数据记录。")
    return metadata_data["images"]

def _build_metadata_index(metadata_list: list) -> dict:
    """Builds an index of metadata by job_id for faster lookups."""
    index = {}
    duplicates = set()
    for item in metadata_list:
        job_id = item.get('job_id')
        if job_id:
            if job_id in index:
                duplicates.add(job_id)
            index[job_id] = item
    if duplicates:
         logging.warning(f"元数据中发现重复的 Job ID: {list(duplicates)}。索引将使用最后找到的记录。")
    return index

def trace_job_history(logger, target_job_id, metadata_dir: str, all_metadata_index=None):
    """根据 original_job_id 追溯任务历史链。

    Args:
        logger: 日志记录器。
        target_job_id: 要追溯的起始任务 ID。
        metadata_dir: 元数据文件所在的目录。
        all_metadata_index: (可选) 预先构建的元数据索引。

    Returns:
        list: 从根任务到目标任务的任务字典列表，如果找不到则为空列表。
    """
    logger.debug(f"开始追溯 Job ID {target_job_id[:6]} 的历史...")
    # Load metadata if index is not provided
    if all_metadata_index is None:
        all_metadata_list = load_all_metadata(logger, metadata_dir)
        if not all_metadata_list:
            logger.error(f"无法加载元数据以追溯 Job ID {target_job_id[:6]}")
            return []
        all_metadata_index = _build_metadata_index(all_metadata_list)
        logger.debug("为追溯历史构建了临时元数据索引。")

    history = []
    current_job_id = target_job_id
    visited = set()
    max_depth = 20 # 防止无限循环
    depth = 0

    while current_job_id and depth < max_depth:
        if current_job_id in visited:
            logger.error(f"追溯历史时检测到循环！在 Job ID {current_job_id[:6]} 处中断。历史链可能不完整。")
            break
        visited.add(current_job_id)
        depth += 1

        current_job_data = all_metadata_index.get(current_job_id)

        if not current_job_data:
            logger.warning(f"在元数据索引中找不到 Job ID {current_job_id[:6]} (追溯历史中)。")
            break

        history.append(current_job_data)

        # Check for original_job_id to continue tracing back
        original_job_id = current_job_data.get('original_job_id')
        if original_job_id:
            logger.debug(f"  -> {current_job_id[:6]} 源自 {original_job_id[:6]}")
            current_job_id = original_job_id
        else:
            logger.debug(f"  -> {current_job_id[:6]} 是根任务或没有 original_job_id。")
            break # Reached the root or a job without original_job_id

    if depth >= max_depth:
         logger.warning(f"追溯 Job ID {target_job_id[:6]} 的历史达到最大深度 {max_depth}，可能未完全追溯。")

    # Reverse the history to get root -> target order
    history.reverse()
    logger.debug(f"追溯完成，历史链长度: {len(history)} (根: {history[0]['job_id'][:6] if history else 'N/A'})")
    return history

def remove_job_metadata(logger: logging.Logger, job_id_to_remove: str, metadata_dir: str) -> bool:
    """从元数据文件中移除指定 Job ID 的记录。

    Args:
        logger: 日志记录器。
        job_id_to_remove: 要移除的 Job ID。
        metadata_dir: 元数据文件所在的目录。

    Returns:
        bool: 操作是否成功 (找到并移除返回 True，未找到或失败返回 False)。
    """
    metadata_filename = "images_metadata.json"
    full_filepath = os.path.join(metadata_dir, metadata_filename)
    logger.info(f"准备从 {full_filepath} 中移除 Job ID {job_id_to_remove[:6]}...")

    # Pass metadata_dir and filename to _load_metadata_file
    metadata_data, load_error, backup_file = _load_metadata_file(logger, metadata_dir, metadata_filename)

    if load_error or metadata_data is None or "images" not in metadata_data:
        logger.error(f"无法加载元数据，无法执行移除。{(' 备份文件: ' + backup_file) if backup_file else ''}")
        return False

    initial_count = len(metadata_data["images"])
    # Filter out the job to remove
    metadata_data["images"] = [job for job in metadata_data["images"] if job.get("job_id") != job_id_to_remove]
    final_count = len(metadata_data["images"])

    if final_count < initial_count:
        logger.info(f"已准备移除 Job ID {job_id_to_remove[:6]}。")
        # Pass metadata_dir and filename to _save_metadata_file
        if _save_metadata_file(logger, metadata_dir, metadata_data, metadata_filename):
            logger.info(f"成功移除了 Job ID {job_id_to_remove[:6]} 的元数据。")
            return True
        else:
            logger.error(f"写入移除后的元数据失败 (Job ID: {job_id_to_remove[:6]})。")
            # Attempt to restore from backup? Or just report failure.
            return False
    else:
        logger.warning(f"未找到 Job ID {job_id_to_remove[:6]}，无需移除。")
        return False # Return False as nothing was removed
