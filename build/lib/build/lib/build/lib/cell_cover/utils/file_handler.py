#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File and Directory Handling Utilities
------------------------------------
Functions for managing directories, downloading images, and saving metadata.
"""

import os
import json
import uuid
import logging
from datetime import datetime
import requests
import time
import shutil
import re # Import re for sanitize_filename

# Define directory paths relative to the script's location (utils/)
# We might need to adjust this if the base should be cell_cover/
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(UTILS_DIR) # Assumes utils is one level down

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
IMAGE_DIR = os.path.join(BASE_DIR, "images")
META_DIR = os.path.join(BASE_DIR, "metadata")
METADATA_FILENAME = os.path.join(META_DIR, "images_metadata.json")
ACTIONS_METADATA_FILENAME = os.path.join(META_DIR, "actions_metadata.json") # New file for action results
MAX_FILENAME_LENGTH = 200 # Define a max filename length

# --- Helper Function ---
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
        dirs: A list of directory paths to ensure. Defaults to [OUTPUT_DIR, IMAGE_DIR, META_DIR].
        base_dir: Optional base directory to use instead of the default BASE_DIR.
    """
    # 如果提供了 base_dir，则使用它来创建目录
    if base_dir:
        # 创建目录列表，如果没有提供，则使用默认目录名称
        if dirs is None:
            # 使用默认目录名称，但基于提供的 base_dir
            dirs = [
                os.path.join(base_dir, "outputs"),
                os.path.join(base_dir, "images"),
                os.path.join(base_dir, "metadata"),
                os.path.join(base_dir, "logs")
            ]
    elif dirs is None:
        # 使用默认目录
        dirs = [OUTPUT_DIR, IMAGE_DIR, META_DIR]

    logger.debug(f"检查并创建目录: {dirs}")
    all_created = True
    for directory in dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"创建目录: {directory}")
                print(f"创建目录: {directory}")
            except OSError as e:
                logger.error(f"警告：无法创建目录 {directory} - {e}")
                print(f"警告：无法创建目录 {directory} - {e}")
                all_created = False # Mark as failed if any dir creation fails
        else:
            logger.debug(f"目录已存在: {directory}")
    return all_created # Return status

def save_image_metadata(logger, image_id, job_id, filename, filepath, url, prompt, concept, variations=None, global_styles=None, components=None, seed=None, original_job_id=None):
    """保存初始图像元数据到 images_metadata.json 文件 (安全模式)

    Args:
        logger: The logging object.
        image_id: The ID of the image.
        job_id: The ID of the job associated with the image.
        filename: The filename of the image.
        filepath: The path to the image file.
        url: The URL of the image.
        prompt: The prompt used to generate the image.
        concept: The concept associated with the image.
        variations: List of variation keys used.
        global_styles: List of global style keys used.
        components: Components data from API response.
        seed: Seed value from API response.
        original_job_id (str, optional): 通常为 None，但为保持签名一致而包含。
    """
    target_filename = METADATA_FILENAME
    logger.info(f"准备保存初始图像元数据到 {target_filename}，图像 ID: {image_id}, Job ID: {job_id}")

    # --- 安全加载现有元数据 (适配字典结构) --- #
    metadata_data = None
    load_error = False
    backup_filename = ""

    try:
        if not ensure_directories(logger, dirs=[META_DIR]):
             logger.error("元数据目录不存在且无法创建，无法保存元数据。")
             return False

        if os.path.exists(target_filename):
            if os.path.getsize(target_filename) > 0:
                with open(target_filename, 'r', encoding='utf-8') as f:
                    try:
                        loaded_data = json.load(f)
                        # 验证基本结构 (期望是包含 'images' 列表的字典)
                        if isinstance(loaded_data, dict) and "images" in loaded_data and isinstance(loaded_data["images"], list):
                            metadata_data = loaded_data
                            logger.debug(f"成功加载现有元数据 ({target_filename})，包含 {len(metadata_data.get('images', []))} 个条目")
                        else:
                            logger.error(f"元数据文件 {target_filename} 格式无效 (不是包含 'images' 列表的字典)，将尝试覆盖。")
                            load_error = True
                    except json.JSONDecodeError as e:
                        logger.error(f"解析元数据文件 {target_filename} 时出错 ({e})，将尝试覆盖。")
                        load_error = True
            else:
                logger.info(f"元数据文件 {target_filename} 为空，将创建新内容。")
                metadata_data = {"images": [], "version": "1.0"} # Initialize with dict structure
        else:
            logger.info(f"元数据文件 {target_filename} 不存在，将创建新的。")
            metadata_data = {"images": [], "version": "1.0"}

    except IOError as e:
        logger.error(f"读取元数据文件 {target_filename} 时发生 IO 错误: {e}")
        load_error = True
    except Exception as e:
        logger.error(f"加载元数据文件 {target_filename} 时发生意外错误: {e}", exc_info=True)
        load_error = True

    # --- 处理加载错误 --- #
    if load_error:
        logger.critical(f"由于元数据文件 {target_filename} 损坏或无法解析，本次操作将不会保存新的元数据以防数据丢失。")
        if os.path.exists(target_filename):
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{target_filename}.bak.{timestamp}"
                shutil.move(target_filename, backup_filename)
                logger.info(f"已将损坏的元数据文件备份到: {backup_filename}")
                print(f"错误：元数据文件已损坏，已尝试备份到 {backup_filename}")
            except Exception as backup_e:
                logger.error(f"尝试备份损坏的元数据文件失败: {backup_e}")
                print(f"错误：元数据文件已损坏，且尝试备份失败 ({backup_e})。请手动检查。")
        else:
             # This case should not happen if load_error is True due to IO/Decode error, but added for safety
             print(f"错误：无法加载元数据，且原始文件 {target_filename} 未找到。")

        return False # 阻止写入新数据

    # --- 追加新数据 --- #
    if metadata_data is None: # Should have been initialized if load failed/file empty
         logger.error("内部错误：无法加载或初始化元数据结构。")
         return False

    logger.debug("追加新的初始元数据条目")
    image_metadata = {
        "id": image_id,
        "job_id": job_id,
        "filename": filename,
        "filepath": filepath,
        "url": url,
        "prompt": prompt,
        "concept": concept,
        "variations": variations or [],
        "global_styles": global_styles or [],
        "seed": seed,
        "created_at": datetime.now().isoformat()
    }
    image_metadata = {k: v for k, v in image_metadata.items() if v is not None}

    # Ensure we append to the 'images' list within the dictionary
    if isinstance(metadata_data, dict) and "images" in metadata_data:
         metadata_data["images"].append(image_metadata)
         logger.debug(f"元数据更新完成，现在共有 {len(metadata_data['images'])} 个条目")
    else:
         logger.error(f"无法追加元数据，元数据结构不是预期的字典: {type(metadata_data)}")
         return False

    # --- 安全写入 --- #
    temp_filename = target_filename + ".tmp"
    try:
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=4, ensure_ascii=False) # Dump the whole dict
        os.replace(temp_filename, target_filename)
        success_msg = f"图像元数据已成功更新并保存到: {target_filename}"
        logger.info(success_msg)
        print(success_msg)
        return True
    except (IOError, OSError) as e:
        logger.error(f"无法写入元数据文件 {target_filename}: {e}")
        print(f"错误：无法写入元数据文件 {target_filename}: {e}")
        # Attempt to remove the temp file if it exists
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except OSError as rem_e:
                logger.error(f"删除临时文件 {temp_filename} 失败: {rem_e}")
        return False
    except Exception as e:
        error_msg = f"保存元数据时发生意外错误: {e}"
        logger.error(error_msg, exc_info=True)
        print(error_msg)
        return False

def save_action_metadata(logger, image_id, new_job_id, original_job_id, action_code, filename, filepath, url, prompt, concept, seed=None):
    """将后续操作 (Upscale/Variation/Action) 的结果元数据保存到 actions_metadata.json。

    Args:
        logger: The logging object.
        image_id: The ID of the image.
        new_job_id: The ID of the new job associated with the image.
        original_job_id: The ID of the original job associated with the image.
        action_code: The code of the action associated with the image.
        filename: The filename of the image.
        filepath: The path to the image file.
        url: The URL of the image.
        prompt: The prompt used to generate the image.
        concept: The concept associated with the image.
        seed: The seed used to generate the image.
    """
    target_filename = ACTIONS_METADATA_FILENAME
    logger.info(f"准备保存 Action 元数据到 {target_filename}，New Job ID: {new_job_id}, Orig Job ID: {original_job_id}, Action: {action_code}")

    action_metadata_item = {
        "action_image_id": image_id,
        "new_job_id": new_job_id,
        "original_job_id": original_job_id,
        "action_code": action_code,
        "filename": filename,
        "filepath": filepath,
        "url": url,
        "original_prompt_ref": prompt, # Label clearly that this might be original
        "concept_ref": concept,
        "seed": seed,
        "saved_at": datetime.now().isoformat()
    }
    action_metadata_item = {k: v for k, v in action_metadata_item.items() if v is not None}

    # Load existing action metadata (assuming simple list structure)
    existing_actions = []
    try:
        ensure_directories(logger, [META_DIR])
        if os.path.exists(target_filename):
            if os.path.getsize(target_filename) > 0:
                with open(target_filename, 'r', encoding='utf-8') as f:
                    try:
                        existing_actions = json.load(f)
                        if not isinstance(existing_actions, list):
                             logger.warning(f"Action元数据文件 {target_filename} 格式错误，不是列表，将覆盖。")
                             existing_actions = []
                    except json.JSONDecodeError:
                        logger.error(f"无法解析 {target_filename}，将覆盖。", exc_info=True)
                        existing_actions = []
            else:
                 logger.info(f"Action元数据文件 {target_filename} 为空。")
        else:
            logger.info(f"Action元数据文件 {target_filename} 不存在，将创建。")

    except Exception as e:
        logger.error(f"加载 Action 元数据 {target_filename} 时出错: {e}", exc_info=True)
        # Decide if we should proceed or fail
        # Let's proceed and try to overwrite
        existing_actions = []

    # Append new action metadata
    existing_actions.append(action_metadata_item)

    # Save back to actions_metadata.json (using safe write)
    temp_filename = target_filename + ".tmp"
    try:
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(existing_actions, f, ensure_ascii=False, indent=4)
        os.replace(temp_filename, target_filename)
        logger.info(f"成功将 Action 元数据 ({len(existing_actions)} 条) 写入 {target_filename}")
        return True
    except Exception as e:
        logger.error(f"写入 Action 元数据到 {target_filename} 时失败: {e}", exc_info=True)
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except Exception as rem_e: logger.error(f"删除临时文件 {temp_filename} 失败: {rem_e}")
        return False

def download_and_save_image(logger, image_url, job_id, prompt, concept_key,
                          variation_keys=None, global_style_keys=None,
                          original_job_id=None, action_code=None,
                          components=None, seed=None, max_retries=1):
    """Downloads an image from a URL, saves it locally, and updates metadata.

    Handles both initial generations and action results (upscale/variation).

    Args:
        logger: The logging object.
        image_url (str): The URL of the image to download.
        job_id (str): The job ID associated with this image (can be new or original).
        prompt (str): The prompt text.
        concept_key (str): The concept key.
        variation_keys (list, optional): List of variation keys used.
        global_style_keys (list, optional): List of global style keys used.
        original_job_id (str, optional): The original job ID if this is an action result.
        action_code (str, optional): The code of the action associated with the image.
        components (list, optional): Components data from API.
        seed (int, optional): The seed value from API.
        max_retries (int): Maximum number of download retries.

    Returns:
        str: The path to the saved image file, or None if download/save failed.
    """
    if not image_url:
        logger.error("无法下载图像，因为图像 URL 为空。")
        return None

    action_log_str = f"{action_code}" if action_code else 'N/A'
    logger.info(f"开始下载图像，概念: {concept_key or 'N/A'}, 当前Job: {job_id}, 操作: {action_log_str}")
    print("开始下载图像...")

    # Ensure image directory exists
    if not ensure_directories(logger, dirs=[IMAGE_DIR]):
        logger.error("图像目录不存在且无法创建，无法下载图像。")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- 文件名生成 --- #
    base_name = f"{sanitize_filename(concept_key)}"
    if variation_keys:
        base_name += f"_{'-'.join(map(sanitize_filename, variation_keys))}"
    if global_style_keys:
        base_name += f"_{'-'.join(map(sanitize_filename, global_style_keys))}"

    # 根据是否是 Action 结果调整文件名
    if action_code:
        # 使用 action_code 生成后缀，确保先处理原始 job id
        orig_id_prefix = original_job_id.split('-')[0] if original_job_id else "orig"
        # Sanitize action_code for filename safety
        safe_action_code = sanitize_filename(action_code)
        filename = f"{base_name}_{orig_id_prefix}_{safe_action_code}_{timestamp}.png"
        target_dir = IMAGE_DIR # Action 结果也保存在主 images 目录
    else:
        # 初始生成的文件名
        filename = f"{base_name}_{timestamp}.png"
        target_dir = IMAGE_DIR

    filepath = os.path.join(target_dir, filename)
    logger.debug(f"图像将保存到: {filepath}")

    logger.info(f"正在从 {image_url} 下载图像...")
    print(f"正在从 {image_url} 下载图像...")

    # Retry logic
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"第 {attempt} 次重试下载图像...")
                print(f"第 {attempt} 次重试下载图像...")
                time.sleep(2)  # Wait before retrying

            response = requests.get(image_url, stream=True, timeout=60) # Increased download timeout
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            success_msg = f"图像已成功保存到: {filepath}"
            logger.info(success_msg)
            print(success_msg)

            # Generate unique ID and save metadata
            image_id = str(uuid.uuid4())
            logger.debug(f"生成图像 ID: {image_id}")

            # --- 保存元数据 --- #
            if action_code:
                # 保存 Action 元数据
                save_action_metadata(
                    logger=logger,
                    image_id=image_id,
                    new_job_id=job_id, # 当前任务的 Job ID
                    original_job_id=original_job_id,
                    action_code=action_code, # 传递 action_code
                    filename=filename,
                    filepath=filepath,
                    url=image_url,
                    prompt=prompt, # 原始任务的 prompt
                    concept=concept_key,
                    seed=seed # 新任务的 seed
                )
            else:
                # 保存初始图像元数据
                save_image_metadata(
                    logger=logger,
                    image_id=image_id,
                    job_id=job_id,
                    filename=filename,
                    filepath=filepath,
                    url=image_url,
                    prompt=prompt,
                    concept=concept_key,
                    variations=variation_keys, # 传递变体信息
                    global_styles=global_style_keys, # 传递风格信息 (需要添加到 save_image_metadata 参数)
                    components=components, # 保持 components
                    seed=seed
                )

            return filepath

        except requests.exceptions.RequestException as e:
            error_msg = f"错误：下载图像时出错 - {e}"
            logger.error(error_msg)
            print(error_msg)
            # Clean up potentially incomplete file
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.debug(f"删除不完整的图像文件: {filepath}")
                except OSError as remove_error:
                    logger.warning(f"无法删除不完整的图像文件: {remove_error}")

            if attempt < max_retries:
                continue # Retry if possible
            else:
                logger.error("所有下载重试尝试均失败 (RequestException)。")
                return None

        except IOError as e:
            error_msg = f"错误：保存图像到 {filepath} 时出错 - {e}"
            logger.error(error_msg)
            print(error_msg)
            if attempt < max_retries:
                continue # Retry if possible (though IOError might persist)
            else:
                 logger.error("所有下载重试尝试均失败 (IOError)。")
                 return None
        except Exception as e: # Catch any other unexpected errors
            error_msg = f"下载或保存图像时发生意外错误: {e}"
            logger.error(error_msg, exc_info=True)
            print(error_msg)
            # Clean up potentially incomplete file
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.debug(f"删除出错时创建的文件: {filepath}")
                except OSError as remove_error:
                    logger.warning(f"无法删除出错时创建的文件: {remove_error}")
            return None # Exit on unexpected error

    # If loop finishes without returning (all retries failed)
    logger.error("所有下载尝试均失败。")
    return None

def restore_metadata_from_job_list(logger, job_list):
    """Compares a list of jobs from TTAPI with local metadata and adds missing ones.

    Args:
        logger: Logging object.
        job_list (list): List of job dictionaries from TTAPI /fetch-list.

    Returns:
        int: Number of records restored, or None if an error occurred.
    """
    target_filename = METADATA_FILENAME
    logger.info(f"开始从 TTAPI 任务列表恢复缺失的元数据到 {target_filename}...")

    # 1. Load existing local metadata safely
    existing_metadata = {"images": [], "version": "1.0"}
    existing_job_ids = set()
    load_error = False

    try:
        if not ensure_directories(logger, dirs=[META_DIR]):
             logger.error("元数据目录不存在且无法创建，无法恢复元数据。")
             return None

        if os.path.exists(target_filename):
            if os.path.getsize(target_filename) > 0:
                with open(target_filename, 'r', encoding='utf-8') as f:
                    try:
                        loaded_data = json.load(f)
                        if isinstance(loaded_data, dict) and "images" in loaded_data and isinstance(loaded_data["images"], list):
                            existing_metadata = loaded_data
                            existing_job_ids = {img.get('job_id') for img in existing_metadata.get('images', []) if img.get('job_id')}
                            logger.info(f"已加载 {len(existing_job_ids)} 条现有本地元数据记录。")
                        else:
                             logger.error(f"本地元数据文件 {target_filename} 格式无效，将创建新文件。")
                             load_error = True # Treat as error, will start fresh
                    except json.JSONDecodeError as e:
                        logger.error(f"解析本地元数据文件 {target_filename} 时出错 ({e})，将创建新文件。")
                        load_error = True # Treat as error, will start fresh
            else:
                logger.info(f"本地元数据文件 {target_filename} 为空。")
                # existing_metadata already initialized
        else:
            logger.info(f"本地元数据文件 {target_filename} 不存在。")
            # existing_metadata already initialized

    except IOError as e:
        logger.error(f"读取本地元数据文件 {target_filename} 时发生 IO 错误: {e}")
        return None # Cannot proceed
    except Exception as e:
        logger.error(f"加载本地元数据文件 {target_filename} 时发生意外错误: {e}", exc_info=True)
        return None # Cannot proceed

    if load_error:
        # Attempt backup before overwriting
        if os.path.exists(target_filename):
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{target_filename}.bak.{timestamp}"
                shutil.move(target_filename, backup_filename)
                logger.info(f"已将格式无效的元数据文件备份到: {backup_filename}")
            except Exception as backup_e:
                logger.error(f"尝试备份格式无效的元数据文件失败: {backup_e}")
        # Reset metadata to default structure
        existing_metadata = {"images": [], "version": "1.0"}
        existing_job_ids = set()

    # 2. Iterate through fetched job list and identify missing records
    restored_count = 0
    for job in job_list:
        job_id = job.get("job_id")
        # Only restore if job ID is present and not already in local metadata
        if job_id and job_id not in existing_job_ids:
            # Try to extract relevant information for metadata
            prompt = job.get("prompt")
            status = job.get("status")
            cdn_image_url = job.get("cdnImage") # URL to potentially download
            created_time_str = job.get("createdAt")

            # Only restore completed jobs with a prompt and URL
            if status == "SUCCESS" and prompt and cdn_image_url:
                logger.info(f"发现缺失的已完成任务: {job_id}，准备恢复...")

                # Basic reconstruction - some fields might be missing
                image_id = str(uuid.uuid4())
                concept_key = "restored" # Mark as restored
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Create a placeholder filename based on job_id and timestamp
                sanitized_prompt_part = sanitize_filename(prompt[:30]) # Use first 30 chars of prompt
                filename = f"{concept_key}_{sanitized_prompt_part}_{timestamp_str}_{job_id[:6]}.png"
                filepath = os.path.join(IMAGE_DIR, filename) # Assume default image dir

                metadata_entry = {
                    "id": image_id,
                    "job_id": job_id,
                    "filename": filename,
                    "filepath": filepath,
                    "url": cdn_image_url,
                    "prompt": prompt,
                    "concept": concept_key,
                    "variations": [], # Cannot reliably restore variations
                    "seed": job.get("seed"), # Restore seed if available
                    "created_at": created_time_str or datetime.now().isoformat(), # Use API time or current
                    "restored_at": datetime.now().isoformat() # Add restoration timestamp
                }
                metadata_entry = {k: v for k, v in metadata_entry.items() if v is not None}

                # Append to the list in memory
                existing_metadata["images"].append(metadata_entry)
                existing_job_ids.add(job_id) # Add to set to avoid duplicates within this run
                restored_count += 1
                logger.debug(f"已准备恢复记录: {job_id}")
            else:
                logger.debug(f"跳过任务 {job_id}: 状态非 SUCCESS 或缺少 prompt/URL (Status: {status})")

    # 3. Save the updated metadata if changes were made
    if restored_count > 0:
        logger.info(f"共找到 {restored_count} 条可恢复的记录，正在写入 {target_filename}...")
        temp_filename = target_filename + ".tmp"
        try:
            with open(temp_filename, 'w', encoding='utf-8') as f:
                json.dump(existing_metadata, f, indent=4, ensure_ascii=False)
            os.replace(temp_filename, target_filename)
            logger.info(f"成功将 {restored_count} 条记录恢复到 {target_filename}")
        except (IOError, OSError) as e:
            logger.error(f"无法写入恢复后的元数据文件 {target_filename}: {e}")
            # Attempt to remove the temp file if it exists
            if os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                except OSError as rem_e:
                    logger.error(f"删除临时文件 {temp_filename} 失败: {rem_e}")
            return None # Indicate error
        except Exception as e:
            logger.error(f"保存恢复后的元数据时发生意外错误: {e}", exc_info=True)
            return None # Indicate error
    else:
        logger.info("未找到需要恢复的本地元数据记录。")

    return restored_count

# --- Metadata Finding Function (Moved from fetch_job_status.py) ---
def find_initial_job_info(logger, identifier):
    """在 images_metadata.json 中根据标识符 (UUID, 前缀, 文件名) 查找初始任务信息。

    Args:
        logger: 日志记录器。
        identifier (str): 可能是完整的 Job ID (UUID), 6位前缀, 或图像文件名。

    Returns:
        dict: 包含 'job_id', 'prompt', 'concept' 等信息的字典，如果找到唯一的匹配项。
        None: 如果未找到或找到多个匹配项。
    """
    # Use the globally defined METADATA_FILENAME
    logger.info(f"在 {METADATA_FILENAME} 中查找标识符 '{identifier}' 对应的任务...")
    metadata_data = None
    try:
        # We assume the directory check happens before saving, so just check file existence here
        if os.path.exists(METADATA_FILENAME):
            if os.path.getsize(METADATA_FILENAME) > 0:
                with open(METADATA_FILENAME, 'r', encoding='utf-8') as f:
                    metadata_data = json.load(f)
                    if not isinstance(metadata_data, dict) or "images" not in metadata_data:
                        logger.error(f"元数据文件 {METADATA_FILENAME} 格式无效。")
                        return None
            else:
                logger.warning(f"元数据文件 {METADATA_FILENAME} 为空。")
                return None # Empty file means no match
        else:
            logger.error(f"元数据文件 {METADATA_FILENAME} 未找到。")
            return None

    except IOError as e:
        logger.error(f"读取元数据文件 {METADATA_FILENAME} 时出错: {e}")
        return None
    except json.JSONDecodeError as e: # Catch JSON errors specifically
         logger.error(f"解析元数据文件 {METADATA_FILENAME} 时出错 ({e})。")
         return None

    if not metadata_data or "images" not in metadata_data:
        # This condition might be redundant due to checks above, but safe to keep
        logger.error("无法加载或解析元数据或 'images' 键不存在。")
        return None

    found_job = None
    search_mode = ""

    # 1. Check if it looks like a full UUID
    # Simple check: length 36 and contains hyphens
    if len(identifier) == 36 and '-' in identifier:
        search_mode = "完整 Job ID"
        logger.info(f"将 '{identifier}' 视为 {search_mode} 进行查找...")
        for job in metadata_data["images"]:
            if job.get("job_id") == identifier:
                found_job = job
                break # Found unique match by full ID

    # 2. Check if it looks like a 6-digit prefix (if not found by UUID)
    elif len(identifier) == 6:
        search_mode = "Job ID 前缀"
        logger.info(f"将 '{identifier}' 视为 {search_mode} 进行查找...")
        possible_matches = []
        for job in metadata_data["images"]:
            if job.get("job_id", "").startswith(identifier):
                possible_matches.append(job)
        if len(possible_matches) == 1:
            found_job = possible_matches[0]
        elif len(possible_matches) > 1:
            logger.error(f"找到多个 Job ID 前缀为 '{identifier}' 的任务，请提供更明确的标识。")
            # Log the ambiguous matches for easier debugging
            for match in possible_matches:
                logger.error(f"  - Job ID: {match.get('job_id')}, Filename: {match.get('filename')}")
            return None # Ambiguous prefix

    # 3. Assume it's a filename (if not found by UUID or prefix)
    if not found_job and not search_mode: # Only search by filename if other methods failed
        search_mode = "文件名"
        logger.info(f"将 '{identifier}' 视为 {search_mode} 进行查找...")
        # Normalize the identifier by removing .png if it exists
        normalized_identifier = identifier.removesuffix('.png')
        for job in metadata_data["images"]:
            # Normalize the stored filename as well
            stored_filename = job.get("filename", "").removesuffix('.png')
            if stored_filename == normalized_identifier:
                found_job = job
                break # Assume filenames are unique for now

    # 4. Return result
    if found_job:
        # Ensure prompt and seed are returned if they exist, needed for recreate
        logger.info(f"通过 {search_mode} 找到匹配的任务: {found_job.get('job_id')} (Seed: {found_job.get('seed', 'N/A')})")
        return found_job
    else:
        logger.error(f"在元数据中未能根据提供的标识符 '{identifier}' ({search_mode or '文件名'} 模式) 找到唯一的任务。")
        return None

# --- Metadata Update Function ---
def update_job_metadata(logger, job_id_to_update, updates):
    """更新 images_metadata.json 中指定 Job ID 的记录。

    Args:
        logger: 日志记录器。
        job_id_to_update (str): 要更新记录的 Job ID。
        updates (dict): 包含要更新的键值对的字典 (例如 {"seed": 12345})。

    Returns:
        bool: 如果成功找到并更新记录则返回 True，否则返回 False。
    """
    target_filename = METADATA_FILENAME
    logger.info(f"尝试更新元数据文件 {target_filename} 中 Job ID {job_id_to_update} 的记录: {updates}")

    # --- 安全加载现有元数据 --- #
    metadata_data = None
    load_error = False
    backup_filename = ""

    try:
        # Ensure directory exists, crucial before trying to read/write
        if not ensure_directories(logger, dirs=[META_DIR]):
             logger.error("元数据目录不存在且无法创建，无法更新元数据。")
             return False

        if os.path.exists(target_filename):
            if os.path.getsize(target_filename) > 0:
                with open(target_filename, 'r', encoding='utf-8') as f:
                    try:
                        loaded_data = json.load(f)
                        if isinstance(loaded_data, dict) and "images" in loaded_data and isinstance(loaded_data["images"], list):
                            metadata_data = loaded_data
                            logger.debug(f"成功加载现有元数据用于更新 ({target_filename})")
                        else:
                            logger.error(f"元数据文件 {target_filename} 格式无效，更新操作中止。")
                            load_error = True
                    except json.JSONDecodeError as e:
                        logger.error(f"解析元数据文件 {target_filename} 时出错 ({e})，更新操作中止。")
                        load_error = True
            else:
                logger.info(f"元数据文件 {target_filename} 为空，无法找到 Job ID {job_id_to_update} 进行更新。")
                return False # Cannot update if file is empty
        else:
            logger.info(f"元数据文件 {target_filename} 不存在，无法找到 Job ID {job_id_to_update} 进行更新。")
            return False # Cannot update if file doesn't exist

    except IOError as e:
        logger.error(f"读取元数据文件 {target_filename} 时发生 IO 错误: {e}")
        load_error = True
    except Exception as e:
        logger.error(f"加载元数据文件 {target_filename} 时发生意外错误: {e}", exc_info=True)
        load_error = True

    # --- 处理加载错误 --- #
    if load_error:
        logger.critical(f"由于加载元数据文件 {target_filename} 时出错，无法执行更新操作。")
        # Backup logic can be added here if desired, similar to save_metadata
        return False # Prevent update if loading failed

    # --- 查找并更新记录 --- #
    if metadata_data is None or "images" not in metadata_data:
         logger.error("内部错误：元数据结构无效，无法执行更新。")
         return False

    job_found_and_updated = False
    for job in metadata_data["images"]:
        if job.get("job_id") == job_id_to_update:
            logger.info(f"找到 Job ID {job_id_to_update}，应用更新: {updates}")
            # Update the job dictionary with the provided updates
            job.update(updates)
            # Add/update a timestamp for the modification
            job["metadata_updated_at"] = datetime.now().isoformat()
            job_found_and_updated = True
            break # Assume job IDs are unique

    if not job_found_and_updated:
        logger.warning(f"在元数据中未找到 Job ID {job_id_to_update}，无法执行更新。")
        return False

    # --- 安全写入 --- #
    temp_filename = target_filename + ".tmp"
    try:
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=4, ensure_ascii=False)
        os.replace(temp_filename, target_filename)
        success_msg = f"成功更新 Job ID {job_id_to_update} 的元数据并保存到: {target_filename}"
        logger.info(success_msg)
        print(success_msg)
        return True
    except (IOError, OSError) as e:
        logger.error(f"无法写入更新后的元数据文件 {target_filename}: {e}")
        print(f"错误：无法写入更新后的元数据文件 {target_filename}: {e}")
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except OSError as rem_e: logger.error(f"删除临时文件 {temp_filename} 失败: {rem_e}")
        return False
    except Exception as e:
        error_msg = f"保存更新后的元数据时发生意外错误: {e}"
        logger.error(error_msg, exc_info=True)
        print(error_msg)
        return False

# --- Metadata Upsert Function ---
def upsert_job_metadata(logger, job_id_to_upsert, new_data):
    """更新或插入 (Upsert) images_metadata.json 中指定 Job ID 的记录。

    如果 Job ID 已存在，则用 new_data 更新现有记录。
    如果 Job ID 不存在，则将 new_data 作为新记录追加。

    Args:
        logger: 日志记录器。
        job_id_to_upsert (str): 要更新或插入记录的 Job ID。
        new_data (dict): 包含任务信息的完整字典 (通常来自 API)。

    Returns:
        bool: 操作是否成功。
    """
    target_filename = METADATA_FILENAME
    logger.info(f"尝试 Upsert 元数据文件 {target_filename} 中的 Job ID {job_id_to_upsert}...")

    # --- 安全加载现有元数据 --- #
    metadata_data = None
    load_error = False
    # Initialize default structure in case file is empty or missing
    default_structure = {"images": [], "version": "1.0"}

    try:
        if not ensure_directories(logger, dirs=[META_DIR]):
            logger.error("元数据目录不存在且无法创建，无法执行 Upsert。")
            return False

        if os.path.exists(target_filename):
            if os.path.getsize(target_filename) > 0:
                with open(target_filename, 'r', encoding='utf-8') as f:
                    try:
                        loaded_data = json.load(f)
                        if isinstance(loaded_data, dict) and "images" in loaded_data and isinstance(loaded_data["images"], list):
                            metadata_data = loaded_data
                            logger.debug(f"成功加载现有元数据用于 Upsert ({target_filename})")
                        else:
                            logger.error(f"元数据文件 {target_filename} 格式无效，将使用默认结构并尝试追加。")
                            metadata_data = default_structure # Start fresh but allow append
                    except json.JSONDecodeError as e:
                        logger.error(f"解析元数据文件 {target_filename} 时出错 ({e})，将使用默认结构并尝试追加。")
                        metadata_data = default_structure # Start fresh but allow append
            else:
                logger.info(f"元数据文件 {target_filename} 为空，将使用默认结构。")
                metadata_data = default_structure
        else:
            logger.info(f"元数据文件 {target_filename} 不存在，将创建新文件。")
            metadata_data = default_structure

    except IOError as e:
        logger.error(f"读取元数据文件 {target_filename} 时发生 IO 错误: {e}")
        return False # Cannot proceed if read fails
    except Exception as e:
        logger.error(f"加载元数据文件 {target_filename} 时发生意外错误: {e}", exc_info=True)
        return False # Cannot proceed on unexpected load error

    # --- 查找并更新或追加记录 --- #
    if metadata_data is None:
        logger.error("内部错误：无法加载或初始化元数据结构。")
        return False

    job_found = False
    # Ensure 'images' list exists
    if "images" not in metadata_data or not isinstance(metadata_data["images"], list):
        logger.warning("元数据缺少 'images' 列表，正在初始化。")
        metadata_data["images"] = []

    for i, job in enumerate(metadata_data["images"]):
        if job.get("job_id") == job_id_to_upsert:
            logger.info(f"找到现有 Job ID {job_id_to_upsert}，执行更新...")
            # Merge new data into existing job, potentially overwriting fields
            # Create a copy of new_data to avoid modifying the original dict if needed elsewhere
            update_payload = new_data.copy()
            update_payload["metadata_updated_at"] = datetime.now().isoformat()
            # Ensure essential IDs are preserved if new_data doesn't have them
            if 'id' not in update_payload and 'id' in job:
                 update_payload['id'] = job['id'] # Keep original local ID

            # Update the dictionary in the list
            metadata_data["images"][i].update(update_payload)
            job_found = True
            break

    if not job_found:
        logger.info(f"未找到现有 Job ID {job_id_to_upsert}，执行追加...")
        # Ensure the new data has a job_id (it should if passed correctly)
        if "job_id" not in new_data or new_data["job_id"] != job_id_to_upsert:
             new_data["job_id"] = job_id_to_upsert # Ensure job_id is correct
        # Add an 'id' if missing (local unique id)
        if "id" not in new_data:
             new_data["id"] = str(uuid.uuid4())
        new_data["metadata_added_at"] = datetime.now().isoformat()
        metadata_data["images"].append(new_data)

    # --- 安全写入 --- #
    temp_filename = target_filename + ".tmp"
    try:
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=4, ensure_ascii=False)
        os.replace(temp_filename, target_filename)
        action = "更新" if job_found else "追加"
        success_msg = f"成功 {action} Job ID {job_id_to_upsert} 的元数据并保存到: {target_filename}"
        logger.info(success_msg)
        # print(success_msg) # Maybe too verbose for view command?
        return True
    except (IOError, OSError) as e:
        logger.error(f"无法写入更新后的元数据文件 {target_filename}: {e}")
        # print(f"错误：无法写入更新后的元数据文件 {target_filename}: {e}")
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except OSError as rem_e: logger.error(f"删除临时文件 {temp_filename} 失败: {rem_e}")
        return False
    except Exception as e:
        error_msg = f"保存更新后的元数据时发生意外错误: {e}"
        logger.error(error_msg, exc_info=True)
        # print(error_msg)
        return False


# --- Metadata Saving Functions ---