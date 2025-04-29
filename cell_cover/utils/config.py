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
import copy # Import copy for deep merging
from typing import Optional

# Note: logger needs to be passed into the functions

def load_config(logger: logging.Logger, default_config_path: str, local_config_path: str) -> Optional[dict]:
    """加载配置文件，优先使用默认配置，并允许本地配置覆盖/合并。

    Args:
        logger: The logging object.
        default_config_path: Path to the default configuration file (usually in the install dir).
        local_config_path: Path to the local configuration file (in the current working directory).

    Returns:
        A dictionary containing the final configuration, or None if the default config fails.
    """
    config = None
    # 1. Load default config - This is mandatory
    try:
        logger.debug(f"尝试加载默认配置文件: {default_config_path}")
        with open(default_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info(f"默认配置文件加载成功: {default_config_path}")
    except FileNotFoundError:
        logger.critical(f"错误：默认配置文件未找到 - {default_config_path}")
        print(f"错误：默认配置文件未找到 - {default_config_path}")
        return None # Cannot proceed without default config
    except json.JSONDecodeError as e:
        logger.critical(f"错误：默认配置文件格式错误 - {default_config_path} - {e}")
        print(f"错误：默认配置文件格式错误 - {default_config_path} - {e}")
        return None # Cannot proceed with invalid default config
    except Exception as e:
        logger.critical(f"错误：加载默认配置文件时出错 - {default_config_path} - {e}")
        print(f"错误：加载默认配置文件时出错 - {default_config_path} - {e}")
        return None # Cannot proceed

    # 2. Load local config if it exists and merge/override
    if os.path.exists(local_config_path):
        try:
            logger.debug(f"发现本地配置文件，尝试加载: {local_config_path}")
            with open(local_config_path, 'r', encoding='utf-8') as f:
                local_config = json.load(f)
                logger.info(f"本地配置文件加载成功: {local_config_path}")
                # Merge strategy: Simple dictionary update (local overrides default)
                # For deeper merging, a recursive merge function would be needed.
                # Example: config.update(local_config)
                # Let's implement a basic deep merge for top-level keys like 'concepts'
                def deep_merge(source, destination):
                    """Recursively merges source dict into destination dict."""
                    for key, value in source.items():
                        if isinstance(value, dict):
                            # Get node or create one
                            node = destination.setdefault(key, {})
                            deep_merge(value, node)
                        else:
                            destination[key] = value
                    return destination

                # Perform the deep merge
                config = deep_merge(local_config, copy.deepcopy(config)) # Use deepcopy of base
                logger.info(f"本地配置已合并入默认配置。")

        except json.JSONDecodeError as e:
            logger.warning(f"警告：本地配置文件格式错误 - {local_config_path} - {e}。将忽略本地配置。")
            print(f"警告：本地配置文件格式错误 - {local_config_path} - {e}。将忽略本地配置。")
        except Exception as e:
            logger.warning(f"警告：加载本地配置文件时出错 - {local_config_path} - {e}。将忽略本地配置。")
            print(f"警告：加载本地配置文件时出错 - {local_config_path} - {e}。将忽略本地配置。")
    else:
        logger.debug(f"本地配置文件未找到: {local_config_path}")

    # Log final concept count
    if config:
        logger.info(f"最终配置包含 {len(config.get('concepts', {}))} 个概念")

    return config

def get_api_key(logger, script_dir_for_env_fallback=None, service="ttapi"):
    """从环境变量或项目根目录的 .env 文件获取API密钥

    Args:
        logger: 日志记录器。
        script_dir_for_env_fallback: (不再推荐使用) 脚本目录，用于旧版 .env 查找。
                                      现在默认查找项目根目录。
        service: 服务名称，用于确定环境变量名称。默认为 "ttapi"。
                支持的值: "ttapi" 或 "imgbb"

    Returns:
        str: API 密钥，如果找到。
        None: 如果未找到。
    """
    # 根据服务名称确定环境变量名称
    env_var_name = "TTAPI_API_KEY" if service.lower() == "ttapi" else "IMGBB_API_KEY"
    service_name = "TTAPI" if service.lower() == "ttapi" else "ImgBB"

    api_key = os.environ.get(env_var_name) # Prefer env var first
    source = "环境变量"

    if api_key:
        logger.info(f"从 {source} 获取了 {service_name}_API_KEY。")
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
                        if key == env_var_name:
                            api_key = value
                            logger.info(f"从 {source} 获取了 {env_var_name}。")
                            break # Found it
            if not api_key:
                 logger.warning(f"在 {source} 中未找到 {env_var_name}=... 行。")
        else:
            logger.warning(f"未找到 {source}。")

    except Exception as e:
        logger.error(f"尝试从 {source} 加载 API 密钥时发生错误: {e}", exc_info=True)
        api_key = None # Ensure api_key is None on error

    if not api_key:
        error_msg = f"错误：未设置 {env_var_name} 环境变量，且在项目根目录 .env 文件中也未找到。"
        logger.critical(error_msg)
        print(error_msg)
        print(f"请设置环境变量 {env_var_name}=<your_api_key> 或在项目根目录 .env 文件中添加该变量 ({service_name} 服务)。")
        # Returning None, let the caller handle exit
        return None

    return api_key