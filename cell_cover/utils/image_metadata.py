\
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
    META_DIR, METADATA_FILENAME, IMAGE_DIR, # IMAGE_DIR needed for restore filepath default
    ensure_directories, sanitize_filename
)

# 导入 API 响应标准化函数
from .api import normalize_api_response

# 注意：原本 save_image_metadata/update_job_metadata/upsert_job_metadata 中包含 print 语句
# 为了让模块更纯粹，这些 print 语句可以移除，仅保留 logger 输出。
# 调用这些函数的地方（例如 command handlers）可以在操作后打印用户反馈。

def _load_metadata_file(logger, target_filename):
    """内部辅助函数：安全地加载元数据文件 (期望是包含 'images' 列表的字典)。"""
    metadata_data = None
    load_error = False
    backup_filename = ""

    try:
        if not ensure_directories(logger, META_DIR):
             logger.error(f"元数据目录 {META_DIR} 不存在且无法创建，无法加载元数据。")
             return None, True, "" # Indicate load error

        if os.path.exists(target_filename):
            if os.path.getsize(target_filename) > 0:
                with open(target_filename, 'r', encoding='utf-8') as f:
                    try:
                        loaded_data = json.load(f)
                        if isinstance(loaded_data, dict) and "images" in loaded_data and isinstance(loaded_data["images"], list):
                            metadata_data = loaded_data
                            logger.debug(f"成功加载现有元数据 ({target_filename})，包含 {len(metadata_data.get('images', []))} 个条目")
                        else:
                            logger.error(f"元数据文件 {target_filename} 格式无效 (不是包含 'images' 列表的字典)。")
                            load_error = True
                    except json.JSONDecodeError as e:
                        logger.error(f"解析元数据文件 {target_filename} 时出错 ({e})。")
                        load_error = True
            else:
                logger.info(f"元数据文件 {target_filename} 为空，将创建新结构。")
                metadata_data = {"images": [], "version": "1.0"} # Initialize
        else:
            logger.info(f"元数据文件 {target_filename} 不存在，将创建新结构。")
            metadata_data = {"images": [], "version": "1.0"} # Initialize

    except IOError as e:
        logger.error(f"读取元数据文件 {target_filename} 时发生 IO 错误: {e}")
        load_error = True
    except Exception as e:
        logger.error(f"加载元数据文件 {target_filename} 时发生意外错误: {e}", exc_info=True)
        load_error = True

    if load_error and os.path.exists(target_filename):
        # Backup the problematic file
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{target_filename}.bak.{timestamp}"
            shutil.move(target_filename, backup_filename)
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

def _save_metadata_file(logger, target_filename, metadata_data):
    """内部辅助函数：安全地将元数据字典写入文件。"""
    temp_filename = target_filename + ".tmp"
    try:
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=4, ensure_ascii=False)
        os.replace(temp_filename, target_filename)
        logger.info(f"元数据已成功写入: {target_filename}")
        return True
    except (IOError, OSError) as e:
        logger.error(f"无法写入元数据文件 {target_filename}: {e}")
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except OSError as rem_e: logger.error(f"删除临时文件 {temp_filename} 失败: {rem_e}")
        return False
    except Exception as e:
        logger.error(f"保存元数据时发生意外错误: {e}", exc_info=True)
        return False

def save_image_metadata(logger, image_id, job_id, filename, filepath, url, prompt, concept,
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
    """
    target_filename = METADATA_FILENAME
    logger.info(f"准备保存初始图像元数据到 {target_filename}，Job ID: {job_id}")

    metadata_data, load_error, backup_file = _load_metadata_file(logger, target_filename)

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

    if _save_metadata_file(logger, target_filename, metadata_data):
        action_desc = "更新" if existing_index != -1 else "保存"
        logger.info(f"成功 {action_desc} Job ID {job_id} 的元数据。")
        return True
    else:
        logger.error(f"保存 Job ID {job_id} 的元数据失败。")
        return False

def find_initial_job_info(logger, identifier):
    """在 images_metadata.json 中根据标识符查找初始任务信息。"""
    target_filename = METADATA_FILENAME
    logger.info(f"在 {target_filename} 中查找标识符 '{identifier}' 对应的任务...")

    metadata_data, load_error, _ = _load_metadata_file(logger, target_filename)

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

def update_job_metadata(logger, job_id_to_update, updates):
    """更新 images_metadata.json 中指定 Job ID 的记录。"""
    target_filename = METADATA_FILENAME
    logger.info(f"尝试更新 {target_filename} 中 Job ID {job_id_to_update} 的记录: {updates}")

    metadata_data, load_error, backup_file = _load_metadata_file(logger, target_filename)

    if load_error or metadata_data is None:
        logger.error(f"无法加载或初始化元数据，无法更新。{(' 备份文件: ' + backup_file) if backup_file else ''}")
        return False

    job_found_and_updated = False
    if "images" in metadata_data:
        for job in metadata_data["images"]:
            if job.get("job_id") == job_id_to_update:
                logger.info(f"找到 Job ID {job_id_to_update}，应用更新。")
                job.update(updates)
                job["metadata_updated_at"] = datetime.now().isoformat()
                job_found_and_updated = True
                break

    if not job_found_and_updated:
        logger.warning(f"在元数据中未找到 Job ID {job_id_to_update}，无法执行更新。")
        return False

    if _save_metadata_file(logger, target_filename, metadata_data):
        logger.info(f"成功更新 Job ID {job_id_to_update} 的元数据。")
        # Removed print statement
        return True
    else:
        logger.error(f"保存 Job ID {job_id_to_update} 更新后的元数据失败。")
        return False

def upsert_job_metadata(logger, job_id_to_upsert, new_data):
    """更新或插入 (Upsert) images_metadata.json 中指定 Job ID 的记录。"""
    target_filename = METADATA_FILENAME
    logger.info(f"尝试 Upsert {target_filename} 中的 Job ID {job_id_to_upsert}...")

    metadata_data, load_error, backup_file = _load_metadata_file(logger, target_filename)

    # If loading failed critically (even after backup attempt), we cannot proceed.
    # _load_metadata_file returns None for metadata_data in critical scenarios.
    if metadata_data is None:
         logger.critical(f"Upsert 失败：无法加载或初始化元数据结构。{(' 备份文件: ' + backup_file) if backup_file else ''}")
         return False
    # If there was a non-critical load error but we initialized a fresh structure, proceed.

    # 使用 normalize_api_response 标准化输入数据
    normalized_data = normalize_api_response(logger, new_data)

    # 确保 job_id 存在且正确
    if "job_id" not in normalized_data or normalized_data["job_id"] != job_id_to_upsert:
        normalized_data["job_id"] = job_id_to_upsert

    job_found = False
    # Ensure 'images' list exists even if we loaded a fresh structure
    if "images" not in metadata_data or not isinstance(metadata_data["images"], list):
        logger.warning("元数据缺少 'images' 列表，正在初始化。")
        metadata_data["images"] = []

    for i, job in enumerate(metadata_data["images"]):
        if job.get("job_id") == job_id_to_upsert:
            logger.info(f"找到现有 Job ID {job_id_to_upsert}，执行更新...")
            update_payload = normalized_data.copy()
            update_payload["metadata_updated_at"] = datetime.now().isoformat()
            if 'id' not in update_payload and 'id' in job:
                update_payload['id'] = job['id']
            metadata_data["images"][i].update(update_payload)
            job_found = True
            break

    if not job_found:
        logger.info(f"未找到现有 Job ID {job_id_to_upsert}，执行追加...")
        upsert_payload = normalized_data.copy() # Use copy to avoid modifying original
        if "job_id" not in upsert_payload or upsert_payload["job_id"] != job_id_to_upsert:
            upsert_payload["job_id"] = job_id_to_upsert
        if "id" not in upsert_payload:
            upsert_payload["id"] = str(uuid.uuid4())
        upsert_payload["metadata_added_at"] = datetime.now().isoformat()
        metadata_data["images"].append(upsert_payload)

    action_desc = "更新" if job_found else "追加"
    if _save_metadata_file(logger, target_filename, metadata_data):
        logger.info(f"成功 {action_desc} Job ID {job_id_to_upsert} 的元数据。")
        # Removed print
        return True
    else:
        logger.error(f"{action_desc} Job ID {job_id_to_upsert} 后保存元数据失败。")
        return False

def load_all_metadata(logger):
    """安全地加载 images_metadata.json 中的所有元数据记录。"""
    target_filename = METADATA_FILENAME
    logger.debug(f"正在尝试加载所有元数据从: {target_filename}")

    metadata_data, load_error, _ = _load_metadata_file(logger, target_filename)

    if load_error or metadata_data is None or "images" not in metadata_data:
        logger.error(f"加载所有元数据失败。")
        return [] # Return empty list on failure

    logger.info(f"成功加载 {len(metadata_data['images'])} 条元数据记录。")
    return metadata_data['images'] # Return only the list part

def _build_metadata_index(metadata_list):
    """
    构建元数据索引，创建 job_id 到任务元数据的映射。

    Args:
        metadata_list: 元数据列表

    Returns:
        dict: 以 job_id 为键、对应元数据字典为值的索引
    """
    index = {}
    if not metadata_list:
        return index

    for task in metadata_list:
        job_id = task.get("job_id")
        if job_id:
            index[job_id] = task

    return index

def trace_job_history(logger, target_job_id, all_metadata=None):
    """
    追溯给定任务 ID 的完整历史链条。

    Args:
        logger: 日志记录器
        target_job_id: 目标任务 ID
        all_metadata: (可选) 预加载的所有元数据。如果未提供，函数会从 METADATA_FILENAME 加载。

    Returns:
        list: 任务链条元数据列表，从根任务（没有original_job_id的任务）到目标任务
    """
    logger.info(f"追溯任务 {target_job_id} 的历史链条...")

    # 加载元数据或使用传入的元数据/索引
    metadata_index = None
    if isinstance(all_metadata, dict) and not "images" in all_metadata:
        # 假设如果传入的是字典且没有 'images' 键，则它是预构建的索引
        logger.debug("使用预构建的元数据索引进行追溯。")
        metadata_index = all_metadata
    elif all_metadata is None:
        # 如果未提供，则加载
        logger.debug("未提供元数据，正在从文件加载...")
        loaded_data, load_error, _ = _load_metadata_file(logger, METADATA_FILENAME)
        if load_error or not loaded_data or "images" not in loaded_data:
            logger.error("无法加载元数据，无法追溯任务历史。")
            return []
        metadata_index = _build_metadata_index(loaded_data.get("images", []))
    elif isinstance(all_metadata, dict) and "images" in all_metadata:
        # 如果传入的是包含 'images' 的字典
        logger.debug("从传入的元数据字典构建索引...")
        metadata_index = _build_metadata_index(all_metadata.get("images", []))
    elif isinstance(all_metadata, list):
         # 如果传入的是列表
        logger.debug("从传入的元数据列表构建索引...")
        metadata_index = _build_metadata_index(all_metadata)
    else:
        logger.error("传入的 all_metadata 参数类型无效，无法追溯任务历史。")
        return []

    # 构建索引以提高查找效率 (现在在上面处理了)
    # metadata_index = _build_metadata_index(all_metadata)

    if target_job_id not in metadata_index:
        logger.warning(f"目标任务 ID {target_job_id} 不存在于元数据索引中。")
        return []

    # 开始回溯链条
    history_chain = []
    visited_job_ids = set()  # 用于循环检测
    current_job_id = target_job_id

    try:
        while current_job_id and current_job_id not in visited_job_ids:
            visited_job_ids.add(current_job_id)

            current_task = metadata_index.get(current_job_id)
            if not current_task:
                logger.warning(f"追踪 Job ID {target_job_id} 时未找到 {current_job_id} 的元数据。")
                break # Stop tracing if a link is missing

            # Safety check: Ensure current_task is a dictionary
            if not isinstance(current_task, dict):
                logger.error(f"追踪 Job ID {target_job_id} 时遇到无效的任务数据（非字典） for Job ID: {current_job_id}。数据: {current_task}")
                break # Stop tracing if data is corrupted

            history_chain.insert(0, current_task)

            # 获取前一个任务 ID
            current_job_id = current_task.get("original_job_id") # Now safer to call .get()
    except Exception as e:
        logger.exception(f"追踪 Job ID {target_job_id} 的历史记录时发生意外错误: {e}") # Use logger.exception for stack trace
        # Return potentially partial history
    return history_chain

# --- 新增：移除元数据记录 --- #

def remove_job_metadata(logger: logging.Logger, job_id_to_remove: str) -> bool:
    """从 images_metadata.json 中移除指定 Job ID 的记录。"""
    target_filename = METADATA_FILENAME
    logger.info(f"尝试从 {target_filename} 中移除 Job ID {job_id_to_remove} 的记录...")

    metadata_data, load_error, backup_file = _load_metadata_file(logger, target_filename)

    if load_error or metadata_data is None:
        logger.error(f"无法加载或初始化元数据，无法移除记录。{(' 备份文件: ' + backup_file) if backup_file else ''}")
        return False

    initial_count = len(metadata_data.get("images", []))
    job_found = False
    index_to_remove = -1

    if "images" in metadata_data:
        for i, job in enumerate(metadata_data["images"]):
            if job.get("job_id") == job_id_to_remove:
                index_to_remove = i
                job_found = True
                break

    if job_found:
        try:
            removed_task = metadata_data["images"].pop(index_to_remove)
            logger.info(f"成功找到并标记待移除 Job ID {job_id_to_remove} (Index: {index_to_remove})。")
            # 保存更改
            if _save_metadata_file(logger, target_filename, metadata_data):
                logger.info(f"成功从元数据文件中移除 Job ID {job_id_to_remove}。")
                return True
            else:
                logger.error(f"保存移除 Job ID {job_id_to_remove} 后的元数据失败。文件可能未更新。")
                # 理论上应该尝试恢复？但目前设计是失败就返回False
                return False
        except IndexError:
             logger.error(f"尝试移除 Job ID {job_id_to_remove} 时发生内部错误：索引 {index_to_remove} 无效。")
             return False
        except Exception as e:
             logger.error(f"移除 Job ID {job_id_to_remove} 时发生意外错误: {e}", exc_info=True)
             return False
    else:
        logger.warning(f"在元数据中未找到要移除的 Job ID {job_id_to_remove}。")
        return False # Return False if not found, although technically not an error
