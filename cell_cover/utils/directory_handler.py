#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Directory and Filename Handling Utilities
----------------------------------------
Functions for ensuring directories exist and sanitizing filenames.
"""

import os
import re
import logging

# Define directory paths relative to the script's location (utils/)
# Assume this file is in utils/, so BASE_DIR is the parent (cell_cover/)
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(UTILS_DIR)

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
IMAGE_DIR = os.path.join(BASE_DIR, "images")
META_DIR = os.path.join(BASE_DIR, "metadata")
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