#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File and Directory Handling Utilities
------------------------------------
Functions for managing directories and files.

Metadata handling functions have been moved to:
- cell_cover/utils/image_metadata.py
- cell_cover/utils/restore_metadata.py

This module now focuses on filesystem operations like
directory creation and filename sanitization.
"""

import os
import logging
import re
import shutil
from datetime import datetime

# --- Constants --- #

# Define directory paths relative to the script's location (utils/)
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(UTILS_DIR) # Assumes utils is one level down

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
IMAGE_DIR = os.path.join(BASE_DIR, "images")
META_DIR = os.path.join(BASE_DIR, "metadata")
LOG_DIR = os.path.join(BASE_DIR, "logs") # Added logs directory
MAX_FILENAME_LENGTH = 200 # Define a max filename length

# --- Helper Functions --- #

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
        dirs: A list of directory paths to ensure. Defaults to standard project dirs.
        base_dir: Optional base directory to use instead of the default BASE_DIR.
    """
    default_dirs = [OUTPUT_DIR, IMAGE_DIR, META_DIR, LOG_DIR]
    
    # Determine the list of directories to check/create
    dirs_to_check = []
    if base_dir:
        if dirs is None:
            # Use default directory names relative to the provided base_dir
            dirs_to_check = [os.path.join(base_dir, os.path.basename(d)) for d in default_dirs]
        else:
            # Use the provided list of dirs relative to the base_dir
            dirs_to_check = [os.path.join(base_dir, d) for d in dirs]
    elif dirs is None:
        # Use the default directories defined by constants
        dirs_to_check = default_dirs
    else:
        # Use the provided list of dirs (absolute or relative to current execution)
        dirs_to_check = dirs

    logger.debug(f"检查并创建目录: {dirs_to_check}")
    all_created = True
    for directory in dirs_to_check:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"创建目录: {directory}")
                # Optionally print for direct user feedback
                # print(f"创建目录: {directory}")
            except OSError as e:
                logger.error(f"警告：无法创建目录 {directory} - {e}")
                # Optionally print for direct user feedback
                # print(f"警告：无法创建目录 {directory} - {e}")
                all_created = False # Mark as failed if any dir creation fails
        else:
            logger.debug(f"目录已存在: {directory}")
    return all_created # Return status

# --- DEPRECATED METADATA FUNCTIONS BELOW --- #
# These are kept temporarily for reference or specific tests if needed,
# but should not be used in new code. Import from metadata_manager instead.

def _load_metadata_file_deprecated(logger, target_filename):
    # ... implementation removed ...
    logger.warning(f"DEPRECATED: _load_metadata_file_deprecated called from file_handler. Use image_metadata._load_metadata_file.")
    pass

def _save_metadata_file_deprecated(logger, target_filename, metadata_data):
    # ... implementation removed ...
    logger.warning(f"DEPRECATED: _save_metadata_file_deprecated called from file_handler. Use image_metadata._save_metadata_file.")
    pass

def save_image_metadata_deprecated(*args, **kwargs):
    logger.warning("DEPRECATED: save_image_metadata_deprecated called from file_handler. Import from metadata_manager.")
    pass

def save_action_metadata_deprecated(*args, **kwargs):
    logger.warning("DEPRECATED: save_action_metadata_deprecated called from file_handler. Use save_image_metadata from metadata_manager with action_code/original_job_id.")
    pass

def restore_metadata_from_job_list_deprecated(*args, **kwargs):
    logger.warning("DEPRECATED: restore_metadata_from_job_list_deprecated called from file_handler. Import from metadata_manager.")
    pass

def find_initial_job_info_deprecated(*args, **kwargs):
    logger.warning("DEPRECATED: find_initial_job_info_deprecated called from file_handler. Import from metadata_manager.")
    return None

def update_job_metadata_deprecated(*args, **kwargs):
    logger.warning("DEPRECATED: update_job_metadata_deprecated called from file_handler. Import from metadata_manager.")
    pass

def upsert_job_metadata_deprecated(*args, **kwargs):
    logger.warning("DEPRECATED: upsert_job_metadata_deprecated called from file_handler. Import from metadata_manager.")
    pass