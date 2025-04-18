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

def get_api_key(logger, script_dir):
    """从环境变量或指定目录下的 .env 文件获取TTAPI密钥

    参数:
    - logger: The logging object.
    - script_dir: The directory where the .env file might be located.
    """
    # 先尝试从环境变量获取
    logger.debug("正在获取 TTAPI API 密钥")
    api_key = os.environ.get("TTAPI_API_KEY")

    if api_key:
        logger.debug("从环境变量中成功获取 API 密钥")
        return api_key

    # 如果环境变量中没有，尝试从 .env 文件加载
    env_path = os.path.join(script_dir, ".env")
    logger.debug(f"尝试从 .env 文件加载 API 密钥: {env_path}")

    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        if line.startswith("TTAPI_API_KEY="):
                            api_key = line.strip().split('=', 1)[1]
                            logger.debug("从 .env 文件中成功获取 API 密钥")
                            break
        except Exception as e:
            logger.warning(f"无法从 .env 文件加载 API 密钥: {e}")
            print(f"警告：无法从 .env 文件加载 API 密钥: {e}")

    # 如果仍然没有找到 API 密钥，报错
    if not api_key:
        error_msg = "错误：未设置 TTAPI_API_KEY 环境变量，且在 .env 文件中也未找到。"
        logger.error(error_msg)
        print(error_msg)
        print("请设置环境变量 TTAPI_API_KEY=<your_api_key> 或在 .env 文件中添加该变量。")
        sys.exit(1)

    return api_key 