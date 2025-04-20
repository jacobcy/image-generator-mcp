#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logging Utilities
-----------------
Function for setting up the application logger.
"""

import logging
import os
from datetime import datetime

# Attempt to import colorlog, provide guidance if missing
try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False
    print("提示: 为了获得彩色日志输出，请安装 'colorlog' 库 (uv pip install colorlog)")

def setup_logging(log_dir_base, verbose=False):
    """配置日志记录器

    Args:
        log_dir_base: The base directory where the 'logs' subdirectory should be created.
        verbose: If True, set log level to DEBUG, otherwise WARNING.
    """
    log_level = logging.DEBUG if verbose else logging.WARNING
    log_format = (
        "%(asctime)s - "
        "%(levelname)s - "
        "%(message)s"
    )
    # Colored format string requires %(log_color)s
    color_log_format = (
        "%(log_color)s%(asctime)s - "
        "%(levelname)s%(reset)s - "
        "%(log_color)s%(message)s%(reset)s"
    )

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level) # Set level for the logger itself

    # --- Console Handler (StreamHandler) Setup --- #
    # Check if a handler already exists (e.g., from basicConfig or previous calls)
    # We want to replace the default formatter with our colored one
    console_handler = None
    if logger.hasHandlers():
        for handler in logger.handlers:
            # Typically the first handler added by basicConfig is a StreamHandler
            if isinstance(handler, logging.StreamHandler):
                console_handler = handler
                break

    # If no StreamHandler found, add one
    if console_handler is None:
        console_handler = logging.StreamHandler()
        logger.addHandler(console_handler)

    # Set formatter for console handler
    if COLORLOG_AVAILABLE:
        formatter = colorlog.ColoredFormatter(
            color_log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            reset=True,
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
    else:
        # Fallback to standard formatter if colorlog is not installed
        formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level) # Ensure handler respects the level

    # --- File Handler Setup --- #
    log_dir = os.path.join(log_dir_base, "logs")
    try:
        os.makedirs(log_dir, exist_ok=True) # Use exist_ok=True
        # Log directory creation info only if it didn't exist
        # We need a temporary basic config to log this if logger is not yet fully set up
        # Or, just print it
        # print(f"日志目录: {log_dir}") # Simple print
    except OSError as e:
        # Log warning but continue without file logging if dir creation fails
        # Use basic print since logger might not be ready for file logging
        print(f"警告：无法创建或访问日志目录 {log_dir} - {e}")
        # We can still return the logger with console handler configured
        return logger

    # Construct log file path
    log_file = os.path.join(log_dir, f"cover_generator_{datetime.now().strftime('%Y%m%d')}.log")

    # Create and add file handler (always use plain formatter)
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        plain_formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(plain_formatter)
        file_handler.setLevel(log_level) # Ensure file handler respects the level

        # Avoid adding the same file handler multiple times if setup_logging is called again
        has_file_handler = any(isinstance(h, logging.FileHandler) and h.baseFilename == file_handler.baseFilename for h in logger.handlers)
        if not has_file_handler:
             logger.addHandler(file_handler)
             logger.info(f"日志将写入文件: {log_file}") # Log this after adding handler
        else:
            logger.debug(f"文件处理器已存在: {log_file}")

    except Exception as e:
        # Log error to console if file handler fails
        logger.error(f"无法创建或添加文件日志处理器: {e}")
        print(f"错误：无法设置文件日志记录: {e}")

    return logger 