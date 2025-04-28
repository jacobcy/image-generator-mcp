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
    # 尝试多个位置查找配置文件
    paths_to_try = [
        # 1. 首先尝试指定的路径
        config_path,
        # 2. 尝试当前工作目录
        os.path.join(os.getcwd(), 'prompts_config.json'),
        # 3. 尝试用户主目录
        os.path.join(os.path.expanduser('~'), 'prompts_config.json'),
        # 4. 尝试项目根目录 (假设当前目录是项目目录)
        os.path.join(os.getcwd(), 'cell_cover', 'prompts_config.json')
    ]

    # 去除重复路径
    paths_to_try = list(dict.fromkeys(paths_to_try))

    last_error = None
    for path in paths_to_try:
        try:
            logger.debug(f"尝试加载配置文件: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"配置文件加载成功: {path}，包含 {len(config.get('concepts', {}))} 个概念")
                return config
        except FileNotFoundError:
            logger.debug(f"配置文件未找到 - {path}")
            last_error = f"错误：配置文件未找到 - {path}"
            continue
        except json.JSONDecodeError as e:
            logger.error(f"错误：配置文件格式错误 - {path} - {e}")
            print(f"错误：配置文件格式错误 - {path} - {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"错误：加载配置文件时出错 - {path} - {e}")
            print(f"错误：加载配置文件时出错 - {path} - {e}")
            sys.exit(1)

    # 如果所有路径都失败，显示错误信息
    logger.error(f"错误：无法在任何位置找到配置文件")
    print(f"错误：无法在任何位置找到配置文件")
    print(f"尝试过以下路径:")
    for path in paths_to_try:
        print(f"  - {path}")
    print(f"请在以上任一位置创建 prompts_config.json 文件")
    sys.exit(1)

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