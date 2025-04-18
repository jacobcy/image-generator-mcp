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

# Define directory paths relative to the script's location (utils/)
# We might need to adjust this if the base should be cell_cover/
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(UTILS_DIR) # Assumes utils is one level down

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
IMAGE_DIR = os.path.join(BASE_DIR, "images")
META_DIR = os.path.join(BASE_DIR, "metadata")
META_FILE = os.path.join(META_DIR, "images_metadata.json")

def ensure_directories(logger, dirs=None):
    """确保必要的目录存在

    Args:
        logger: The logging object.
        dirs: A list of directory paths to ensure. Defaults to [OUTPUT_DIR, IMAGE_DIR, META_DIR].
    """
    if dirs is None:
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

def save_image_metadata(logger, image_id, job_id, filename, filepath, url, prompt, concept, variations=None, components=None, seed=None):
    """保存图像元数据到 metadata/images_metadata.json 文件

    Args:
        logger: The logging object.
        variations: List of variation keys used.
        # ... other args ...
    """
    logger.info(f"正在保存图像元数据，图像 ID: {image_id}")
    try:
        # Ensure metadata directory exists before saving
        if not ensure_directories(logger, dirs=[META_DIR]):
             logger.error("元数据目录不存在且无法创建，无法保存元数据。")
             return False

        logger.debug(f"元数据文件路径: {META_FILE}")

        # 加载现有元数据或创建新的
        metadata_data = {"images": [], "version": "1.0"} # Default structure
        if os.path.exists(META_FILE):
            logger.debug("元数据文件已存在，正在加载")
            try:
                with open(META_FILE, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Basic validation
                    if isinstance(loaded_data, dict) and "images" in loaded_data and isinstance(loaded_data["images"], list):
                        metadata_data = loaded_data
                        logger.debug(f"已加载元数据，包含 {len(metadata_data.get('images', []))} 个图像条目")
                    else:
                        logger.warning("元数据文件格式无效，将使用新的元数据结构。")
            except json.JSONDecodeError:
                logger.warning("元数据文件格式错误，将使用新的元数据结构。")
            except Exception as e: # Catch other potential read errors
                 logger.error(f"加载元数据文件时出错: {e}，将使用新的元数据结构。")
        else:
            logger.debug("元数据文件不存在，创建新的元数据")

        # 添加新图像的元数据
        image_metadata = {
            "id": image_id,
            "job_id": job_id,
            "filename": filename,
            "filepath": filepath, # Consider making this relative or storing base path separately
            "url": url,
            "prompt": prompt,
            "concept": concept,
            "variations": variations or [], # Store the list of variations
            "components": components or [],
            "seed": seed,
            "created_at": datetime.now().isoformat()
        }

        metadata_data["images"].append(image_metadata)
        logger.debug(f"添加新的元数据条目，现在共有 {len(metadata_data['images'])} 个条目")

        # 保存元数据
        try:
            with open(META_FILE, 'w', encoding='utf-8') as f:
                json.dump(metadata_data, f, indent=2, ensure_ascii=False)
            success_msg = f"图像元数据已保存到: {META_FILE}"
            logger.info(success_msg)
            print(success_msg)
            return True
        except IOError as e:
            logger.error(f"无法写入元数据文件 {META_FILE}: {e}")
            print(f"错误：无法写入元数据文件 {META_FILE}: {e}")
            return False

    except Exception as e:
        error_msg = f"保存元数据时发生意外错误: {e}"
        logger.error(error_msg, exc_info=True) # Log traceback
        print(error_msg)
        return False

def download_and_save_image(logger, image_url, job_id, prompt, concept_key, variation_keys=None, components=None, seed=None, max_retries=1):
    """下载图像并保存到 images 目录，同时保存元数据

    Args:
        logger: The logging object.
        variation_keys: List of variation keys used.
        # ... other args ...
        max_retries: Maximum download retries.
    """
    variation_log_str = '-'.join(variation_keys) if variation_keys else 'N/A'
    logger.info(f"开始下载图像，概念: {concept_key or 'N/A'}, 变体: {variation_log_str}")
    print("开始下载图像...")

    # Ensure image directory exists
    if not ensure_directories(logger, dirs=[IMAGE_DIR]):
        logger.error("图像目录不存在且无法创建，无法下载图像。")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create filename string from list of variations
    variation_str = f"_{'-'.join(variation_keys)}" if variation_keys else ""

    # Generate filename
    try:
        # Attempt to get file extension from URL
        parsed_url = requests.utils.urlparse(image_url)
        path_part = parsed_url.path
        file_ext = os.path.splitext(path_part)[-1] or ".png"
        if not file_ext.startswith('.') or len(file_ext) > 5: # Basic sanity check
             file_ext = ".png"
    except Exception:
        logger.warning("无法从URL解析文件扩展名，默认为 .png")
        file_ext = ".png"

    # Handle potential None for concept_key
    concept_prefix = concept_key if concept_key else "unknown_concept"
    filename = f"{concept_prefix}{variation_str}_image_{timestamp}{file_ext}"
    filepath = os.path.join(IMAGE_DIR, filename)
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
            # Call save_image_metadata (defined in this file)
            metadata_saved = save_image_metadata(
                logger=logger,
                image_id=image_id,
                job_id=job_id,
                filename=filename,
                filepath=filepath,
                url=image_url,
                prompt=prompt,
                concept=concept_key,
                variations=variation_keys, # Pass the list of variations
                components=components,
                seed=seed
            )
            if not metadata_saved:
                logger.warning("图像已下载，但保存元数据失败。")
                # Decide if this should still be considered a success

            return filepath # Return path even if metadata failed? Or return None?

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