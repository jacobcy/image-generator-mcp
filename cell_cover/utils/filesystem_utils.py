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

def check_and_create_directories(logger: logging.Logger, cwd: str) -> bool:
    """Checks and creates necessary application directories within the current working directory."""
    logger.info(f"检查并创建应用程序在 '{cwd}' 下所需的工作目录...")

    # Define directories relative to cwd
    crc_base_dir = os.path.join(cwd, '.crc')
    output_dir = os.path.join(crc_base_dir, 'output')
    metadata_dir = os.path.join(crc_base_dir, 'metadata')
    # Logs and state dirs are already created in cli.py's common_setup
    # We just need output and metadata here.
    dirs_to_check = [output_dir, metadata_dir]

    return ensure_directories(logger, *dirs_to_check)

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

# --- Last Job ID Functions (now use state_dir) ---

def read_last_job_id(logger: logging.Logger, state_dir: Optional[str]) -> Optional[str]:
    """Reads the last Job ID from the state directory."""
    if not state_dir:
        logger.error("state_dir 为空，无法读取 last job ID")
        return None
    last_job_filepath = os.path.join(state_dir, 'last_job.json')
    if not os.path.exists(last_job_filepath):
        logger.info(f"Last job ID file ({last_job_filepath}) not found. Cannot retrieve last job.")
        return None
    try:
        with open(last_job_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_id = data.get("last_job_id")
            if last_id and isinstance(last_id, str):
                logger.info(f"从 {last_job_filepath} 读取到上一个 Job ID: {last_id}")
                return last_id
            else:
                logger.warning(f"文件 {last_job_filepath} 格式无效或缺少 'last_job_id'。")
                return None
    except json.JSONDecodeError:
        logger.error(f"文件 {last_job_filepath} 不是有效的 JSON 文件。")
        return None
    except IOError as e:
        logger.error(f"读取 {last_job_filepath} 时出错: {e}")
        return None
    except Exception as e:
        logger.error(f"读取最后一个 Job ID 时发生意外错误: {e}", exc_info=True)
        return None

def write_last_job_id(logger: logging.Logger, job_id: str, state_dir: Optional[str]) -> bool:
    """Writes the given Job ID to the state directory."""
    if not job_id or not isinstance(job_id, str):
        logger.error("尝试写入无效的 Job ID。")
        return False

    if not state_dir:
        logger.error("state_dir 为空，无法写入 last job ID")
        return False

    # state_dir should already exist from common_setup, but double-check
    if not ensure_directories(logger, state_dir):
        logger.error(f"无法创建或访问状态目录 {state_dir}，无法写入 Last Job ID。")
        return False

    last_job_filepath = os.path.join(state_dir, 'last_job.json')
    data = {"last_job_id": job_id, "updated_at": datetime.now().isoformat()}
    try:
        # Use atomic write pattern
        temp_filename = last_job_filepath + ".tmp"
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        os.replace(temp_filename, last_job_filepath)
        logger.info(f"已将最后一个 Job ID ({job_id}) 写入到 {last_job_filepath}")
        return True
    except (IOError, OSError) as e:
        logger.error(f"写入 {last_job_filepath} 时出错: {e}")
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except OSError: pass
        return False
    except Exception as e:
        logger.error(f"写入最后一个 Job ID 时发生意外错误: {e}", exc_info=True)
        return False

# --- Last Succeed Job ID Functions (now use state_dir) ---

def read_last_succeed_job_id(logger: logging.Logger, state_dir: Optional[str]) -> Optional[str]:
    """Reads the last successfully completed Job ID from the state directory."""
    if not state_dir:
        logger.error("state_dir 为空，无法读取 last succeed job ID")
        return None
    last_succeed_filepath = os.path.join(state_dir, 'last_succeed.json')
    if not os.path.exists(last_succeed_filepath):
        logger.info(f"Last succeed job ID file ({last_succeed_filepath}) not found.")
        return None
    try:
        with open(last_succeed_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_id = data.get("last_succeed_job_id") # Use a distinct key
            if last_id and isinstance(last_id, str):
                logger.info(f"从 {last_succeed_filepath} 读取到上一个成功 Job ID: {last_id}")
                return last_id
            else:
                logger.warning(f"文件 {last_succeed_filepath} 格式无效或缺少 'last_succeed_job_id'。")
                return None
    except json.JSONDecodeError:
        logger.error(f"文件 {last_succeed_filepath} 不是有效的 JSON 文件。")
        return None
    except IOError as e:
        logger.error(f"读取 {last_succeed_filepath} 时出错: {e}")
        return None
    except Exception as e:
        logger.error(f"读取最后一个成功 Job ID 时发生意外错误: {e}", exc_info=True)
        return None

def write_last_succeed_job_id(logger: logging.Logger, job_id: str, state_dir: Optional[str]) -> bool:
    """Writes the given successfully completed Job ID to the state directory."""
    if not job_id or not isinstance(job_id, str):
        logger.error("尝试写入无效的成功 Job ID。")
        return False

    if not state_dir:
        logger.error("state_dir 为空，无法写入 last succeed job ID")
        return False

    # state_dir should already exist from common_setup, but double-check
    if not ensure_directories(logger, state_dir):
        logger.error(f"无法创建或访问状态目录 {state_dir}，无法写入 Last Succeed Job ID。")
        return False

    last_succeed_filepath = os.path.join(state_dir, 'last_succeed.json')
    data = {"last_succeed_job_id": job_id, "updated_at": datetime.now().isoformat()} # Use distinct key
    try:
        # Use atomic write pattern
        temp_filename = last_succeed_filepath + ".tmp"
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        os.replace(temp_filename, last_succeed_filepath)
        logger.info(f"已将最后一个成功 Job ID ({job_id}) 写入到 {last_succeed_filepath}")
        return True
    except (IOError, OSError) as e:
        logger.error(f"写入 {last_succeed_filepath} 时出错: {e}")
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except OSError: pass
        return False
    except Exception as e:
        logger.error(f"写入最后一个成功 Job ID 时发生意外错误: {e}", exc_info=True)
        return False