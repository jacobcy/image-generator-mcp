#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration and API Key Utilities
-----------------------------------
Functions for loading configuration files and retrieving the API key.
"""

import os
import json
import sys
import logging # Import logging

# Note: logger needs to be passed into the functions

def load_config(logger, config_path):
    """加载指定的提示词配置文件

    参数:
    - logger: The logging object.
    - config_path: Path to the configuration file.
    """
    try:
        logger.debug(f"正在加载配置文件: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.debug(f"配置文件加载成功，包含 {len(config.get('concepts', {}))} 个概念")
            return config
    except FileNotFoundError:
        logger.error(f"错误：配置文件未找到 - {config_path}")
        print(f"错误：配置文件未找到 - {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"错误：配置文件格式错误 - {e}")
        print(f"错误：配置文件格式错误 - {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"错误：加载配置文件时出错 - {e}")
        print(f"错误：加载配置文件时出错 - {e}")
        sys.exit(1)

def get_api_key(logger, script_dir_for_env_fallback=None):
    """从环境变量或项目根目录的 .env 文件获取TTAPI密钥

    Args:
        logger: 日志记录器。
        script_dir_for_env_fallback: (不再推荐使用) 脚本目录，用于旧版 .env 查找。
                                      现在默认查找项目根目录。

    Returns:
        str: TTAPI 密钥，如果找到。
        None: 如果未找到。
    """
    api_key = os.environ.get("TTAPI_API_KEY") # Prefer env var first
    source = "环境变量"

    if api_key:
        logger.info(f"从 {source} 获取了 TTAPI_API_KEY。")
        return api_key

    # Fallback to .env in project root
    try:
        # Determine project root (assuming this file is utils/config.py)
        utils_dir = os.path.dirname(os.path.abspath(__file__))
        cell_cover_dir = os.path.dirname(utils_dir)
        project_root = os.path.dirname(cell_cover_dir)
        env_path = os.path.join(project_root, ".env")
        source = f"项目根目录的 {env_path} 文件"
        logger.info(f"环境变量 TTAPI_API_KEY 未设置，尝试从 {source} 加载。")

        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key == "TTAPI_API_KEY":
                            api_key = value
                            logger.info(f"从 {source} 获取了 TTAPI_API_KEY。")
                            break # Found it
            if not api_key:
                 logger.warning(f"在 {source} 中未找到 TTAPI_API_KEY=... 行。")
        else:
            logger.warning(f"未找到 {source}。")

    except Exception as e:
        logger.error(f"尝试从 {source} 加载 API 密钥时发生错误: {e}", exc_info=True)
        api_key = None # Ensure api_key is None on error

    if not api_key:
        error_msg = "错误：未设置 TTAPI_API_KEY 环境变量，且在项目根目录 .env 文件中也未找到。"
        logger.critical(error_msg)
        print(error_msg)
        print("请设置环境变量 TTAPI_API_KEY=<your_api_key> 或在项目根目录 .env 文件中添加该变量。")
        # Returning None, let the caller handle exit
        return None

    return api_key 