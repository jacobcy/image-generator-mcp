#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件系统工具模块
---------------
提供文件系统相关功能，包括目录确保和文件名清理。
"""

import os
import re
import logging
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Define base directory - Assuming the script using this is in cell_cover/utils/
# Go up two levels to get the parent of cell_cover
# ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# More robust way using Path, assuming this file is cell_cover/utils/filesystem_utils.py
UTILS_DIR = Path(__file__).parent
CELL_COVER_DIR = UTILS_DIR.parent
ROOT_DIR = CELL_COVER_DIR.parent # Adjust if your structure is different

# --- Directory Constants ---
CACHE_DIR = os.path.join(ROOT_DIR, '.cache', 'cell_cover')
CONFIG_DIR = os.path.join(ROOT_DIR, '.config', 'cell_cover') # For config files
IMAGE_DIR = os.path.join(ROOT_DIR, 'cell_cover', 'images') # Where generated images are saved by default
META_DIR = os.path.join(ROOT_DIR, 'cell_cover', 'metadata') # For metadata files
USER_DATA_DIR = os.path.join(ROOT_DIR, 'cell_cover', 'user_data') # Example for other data
OUTPUT_DIR = os.path.join(ROOT_DIR, 'cell_cover', 'outputs') # For generated prompts etc.

# --- Filename Constants ---
PROMPTS_CONFIG_PATH = os.path.join(CONFIG_DIR, 'prompts_config.json') # Main prompt config
METADATA_FILENAME = os.path.join(META_DIR, 'images_metadata.json') # Image metadata
ACTIONS_METADATA_FILENAME = os.path.join(META_DIR, 'actions_metadata.json') # Actions metadata
LAST_JOB_FILENAME = os.path.join(CONFIG_DIR, 'last_job.json') # Stores the last executed job ID
# Add constant for last successfully completed job ID file
LAST_SUCCEED_FILENAME = os.path.join(CONFIG_DIR, 'last_succeed.json')

# Directories to ensure exist
# Added CONFIG_DIR explicitly, although PROMPTS_CONFIG_PATH implies it.
# Added META_DIR explicitly.
DIRS_TO_CHECK = [CACHE_DIR, CONFIG_DIR, IMAGE_DIR, META_DIR, USER_DATA_DIR, OUTPUT_DIR]

def ensure_directories(logger, *paths):
    """Ensure that the specified directories exist, creating them if necessary."""
    all_created = True
    for path in paths:
        try:
            # Explicitly cast path to string before passing to os.makedirs
            os.makedirs(str(path), exist_ok=True)
            logger.debug(f"目录已确认或创建: {path}")
        except OSError as e:
            logger.error(f"无法创建目录 {path}: {e}")
            all_created = False
        except Exception as e:
             # Catch any other unexpected error during makedirs for this path
             logger.error(f"创建目录 {path} 时发生意外错误: {e}", exc_info=True)
             all_created = False
    return all_created

def check_and_create_directories(logger):
    """Checks and creates all necessary application directories."""
    logger.info("检查并创建应用程序所需目录...")
    return ensure_directories(logger, *DIRS_TO_CHECK)

def sanitize_filename(name):
    """Sanitizes a string to be used as a filename."""
    # Remove potentially problematic characters
    name = re.sub(r'[\\/*?:"<>|\']', '', name)
    # Replace spaces with underscores
    name = re.sub(r'\s+', '_', name)
    # Limit length (optional, adjust as needed)
    max_len = 100
    if len(name) > max_len:
        name = name[:max_len]
    # Ensure it's not empty
    if not name:
        name = str(uuid.uuid4())[:8] # Fallback to a short UUID part
    return name

# --- Last Job ID Functions ---

def read_last_job_id(logger: logging.Logger) -> Optional[str]:
    """Reads the last Job ID from the dedicated file."""
    if not os.path.exists(LAST_JOB_FILENAME):
        logger.info(f"Last job ID file ({LAST_JOB_FILENAME}) not found. Cannot retrieve last job.")
        return None
    try:
        with open(LAST_JOB_FILENAME, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_id = data.get("last_job_id")
            if last_id and isinstance(last_id, str):
                logger.info(f"从 {LAST_JOB_FILENAME} 读取到上一个 Job ID: {last_id}")
                return last_id
            else:
                logger.warning(f"文件 {LAST_JOB_FILENAME} 格式无效或缺少 'last_job_id'。")
                return None
    except json.JSONDecodeError:
        logger.error(f"文件 {LAST_JOB_FILENAME} 不是有效的 JSON 文件。")
        return None
    except IOError as e:
        logger.error(f"读取 {LAST_JOB_FILENAME} 时出错: {e}")
        return None
    except Exception as e:
        logger.error(f"读取最后一个 Job ID 时发生意外错误: {e}", exc_info=True)
        return None

def write_last_job_id(logger: logging.Logger, job_id: str) -> bool:
    """Writes the given Job ID to the dedicated file."""
    if not job_id or not isinstance(job_id, str):
        logger.error("尝试写入无效的 Job ID。")
        return False

    # Ensure the config directory exists first
    if not ensure_directories(logger, CONFIG_DIR):
        logger.error(f"无法创建配置目录 {CONFIG_DIR}，无法写入 Last Job ID。")
        return False

    data = {"last_job_id": job_id, "updated_at": datetime.now().isoformat()}
    try:
        # Use atomic write pattern
        temp_filename = LAST_JOB_FILENAME + ".tmp"
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        os.replace(temp_filename, LAST_JOB_FILENAME)
        logger.info(f"已将最后一个 Job ID ({job_id}) 写入到 {LAST_JOB_FILENAME}")
        return True
    except (IOError, OSError) as e:
        logger.error(f"写入 {LAST_JOB_FILENAME} 时出错: {e}")
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except OSError: pass
        return False
    except Exception as e:
        logger.error(f"写入最后一个 Job ID 时发生意外错误: {e}", exc_info=True)
        return False

# --- Last Succeed Job ID Functions ---

def read_last_succeed_job_id(logger: logging.Logger) -> Optional[str]:
    """Reads the last successfully completed Job ID from its dedicated file."""
    if not os.path.exists(LAST_SUCCEED_FILENAME):
        logger.info(f"Last succeed job ID file ({LAST_SUCCEED_FILENAME}) not found.")
        return None
    try:
        with open(LAST_SUCCEED_FILENAME, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_id = data.get("last_succeed_job_id") # Use a distinct key
            if last_id and isinstance(last_id, str):
                logger.info(f"从 {LAST_SUCCEED_FILENAME} 读取到上一个成功 Job ID: {last_id}")
                return last_id
            else:
                logger.warning(f"文件 {LAST_SUCCEED_FILENAME} 格式无效或缺少 'last_succeed_job_id'。")
                return None
    except json.JSONDecodeError:
        logger.error(f"文件 {LAST_SUCCEED_FILENAME} 不是有效的 JSON 文件。")
        return None
    except IOError as e:
        logger.error(f"读取 {LAST_SUCCEED_FILENAME} 时出错: {e}")
        return None
    except Exception as e:
        logger.error(f"读取最后一个成功 Job ID 时发生意外错误: {e}", exc_info=True)
        return None

def write_last_succeed_job_id(logger: logging.Logger, job_id: str) -> bool:
    """Writes the given successfully completed Job ID to its dedicated file."""
    if not job_id or not isinstance(job_id, str):
        logger.error("尝试写入无效的成功 Job ID。")
        return False

    # Ensure the config directory exists first
    if not ensure_directories(logger, CONFIG_DIR):
        logger.error(f"无法创建配置目录 {CONFIG_DIR}，无法写入 Last Succeed Job ID。")
        return False

    data = {"last_succeed_job_id": job_id, "updated_at": datetime.now().isoformat()} # Use distinct key
    try:
        # Use atomic write pattern
        temp_filename = LAST_SUCCEED_FILENAME + ".tmp"
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        os.replace(temp_filename, LAST_SUCCEED_FILENAME)
        logger.info(f"已将最后一个成功 Job ID ({job_id}) 写入到 {LAST_SUCCEED_FILENAME}")
        return True
    except (IOError, OSError) as e:
        logger.error(f"写入 {LAST_SUCCEED_FILENAME} 时出错: {e}")
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except OSError: pass
        return False
    except Exception as e:
        logger.error(f"写入最后一个成功 Job ID 时发生意外错误: {e}", exc_info=True)
        return False