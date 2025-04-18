#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cell Cover Generator using TTAPI
--------------------------------
这个脚本用于生成Cell杂志封面的Midjourney提示词，
并通过 TTAPI 调用 Midjourney API 来生成实际图像，
最终将图像保存到 images 目录。
"""

import json
import os
import argparse
import sys
import time
import logging
from datetime import datetime
import uuid

# 尝试导入必要的库
try:
    import requests
except ImportError:
    print("错误：缺少 'requests' 库。请使用 'uv pip install requests' 安装。")
    sys.exit(1)

# 检查 pyperclip 模块是否可用
try:
    import importlib.util
    PYPERCLIP_AVAILABLE = importlib.util.find_spec("pyperclip") is not None
except ImportError:
    PYPERCLIP_AVAILABLE = False

# 注意：我们已经移除了对 utils 模块的依赖，使用内置函数实现所有功能

# --- 配置日志 ---
def setup_logging(verbose=False):
    """配置日志记录器"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=log_level, format=log_format)

    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"警告：无法创建日志目录 {log_dir} - {e}")

    # 添加文件处理程序
    log_file = os.path.join(log_dir, f"cover_generator_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(file_handler)

    return logging.getLogger()

# --- 配置常量 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "prompts_config.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs") # 用于保存原始提示词（可选）
IMAGE_DIR = os.path.join(SCRIPT_DIR, "images")   # 用于保存生成的图像
META_DIR = os.path.join(SCRIPT_DIR, "metadata")  # 用于保存图像元数据
META_FILE = os.path.join(META_DIR, "images_metadata.json") # 元数据文件
TTAPI_BASE_URL = "https://api.ttapi.io/midjourney/v1"
POLL_INTERVAL_SECONDS = 10  # 轮询间隔
FETCH_TIMEOUT_SECONDS = 360 # 获取结果的总超时时间 (根据模式调整, e.g., relax可能需要更久)

# 初始化日志记录器
logger = setup_logging()

# --- 辅助函数 ---

def load_config():
    """加载提示词配置文件"""
    try:
        logger.debug(f"正在加载配置文件: {CONFIG_PATH}")
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.debug(f"配置文件加载成功，包含 {len(config.get('concepts', {}))} 个概念")
            return config
    except FileNotFoundError:
        logger.error(f"错误：配置文件未找到 - {CONFIG_PATH}")
        print(f"错误：配置文件未找到 - {CONFIG_PATH}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"错误：配置文件格式错误 - {e}")
        print(f"错误：配置文件格式错误 - {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"错误：加载配置文件时出错 - {e}")
        print(f"错误：加载配置文件时出错 - {e}")
        sys.exit(1)

def get_api_key():
    """从环境变量或 .env 文件获取TTAPI密钥"""
    # 先尝试从环境变量获取
    logger.debug("正在获取 TTAPI API 密钥")
    api_key = os.environ.get("TTAPI_API_KEY")

    if api_key:
        logger.debug("从环境变量中成功获取 API 密钥")
        return api_key

    # 如果环境变量中没有，尝试从 .env 文件加载
    env_path = os.path.join(SCRIPT_DIR, ".env")
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

def list_concepts(config):
    """列出所有可用的创意概念"""
    logger.info("列出所有可用的创意概念")
    print("可用的创意概念:")
    concepts = config.get("concepts", {})
    if not concepts:
        logger.warning("配置文件中没有找到任何概念")
        print("  配置文件中没有找到任何概念。")
        return

    logger.debug(f"找到 {len(concepts)} 个概念")
    for key, concept in concepts.items():
        print(f"  - {key}: {concept.get('name', 'N/A')}")
        print(f"    {concept.get('description', '无描述')}")
        print()

def list_variations(config, concept_key):
    """列出指定概念的所有变体"""
    logger.info(f"列出概念 '{concept_key}' 的所有变体")
    concepts = config.get("concepts", {})
    if concept_key not in concepts:
        logger.error(f"找不到创意概念 '{concept_key}'")
        print(f"错误：找不到创意概念 '{concept_key}'")
        return

    concept = concepts[concept_key]
    variations = concept.get("variations", {})
    print(f"'{concept.get('name', concept_key)}'的可用变体:")
    if not variations:
        logger.warning(f"概念 '{concept_key}' 没有定义变体")
        print("  此概念没有定义变体。")
        return

    logger.debug(f"找到 {len(variations)} 个变体")
    for key, desc in variations.items():
        print(f"  - {key}: {desc}")
    print()

def generate_prompt_text(config, concept_key, variation_key=None, aspect_ratio="cell_cover", quality="high", version="v6"):
    """生成用于API的Midjourney提示词文本和参数字典

    返回值:
        成功时返回字典，包含 prompt 和各种参数
        失败时返回 None
    """
    logger.info(f"正在生成提示词，概念: {concept_key}, 变体: {variation_key or 'None'}")

    # 初始化结果字典
    result = {
        "prompt": "",
        "aspect_ratio": None,
        "quality": None,
        "version": None,
        "concept": concept_key,
        "variation": variation_key
    }

    concepts = config.get("concepts", {})
    if concept_key not in concepts:
        error_msg = f"错误：找不到创意概念 '{concept_key}'"
        logger.error(error_msg)
        print(error_msg)
        return None

    concept = concepts[concept_key]
    base_prompt = concept.get("midjourney_prompt", "")
    if not base_prompt:
        error_msg = f"错误：概念 '{concept_key}' 没有定义 'midjourney_prompt'。"
        logger.error(error_msg)
        print(error_msg)
        return None

    result["prompt"] = base_prompt
    logger.debug(f"基础提示词: {base_prompt}")

    # 添加变体修饰词
    if variation_key:
        variations = concept.get("variations", {})
        if variation_key in variations:
            result["prompt"] += f" {variations[variation_key]}"
            logger.debug(f"添加变体 '{variation_key}': {variations[variation_key]}")
        else:
            warning_msg = f"警告：找不到变体 '{variation_key}' 用于概念 '{concept_key}'，将忽略变体。"
            logger.warning(warning_msg)
            print(warning_msg)

    # 添加宽高比
    aspect_ratios = config.get("aspect_ratios", {})
    if aspect_ratio in aspect_ratios:
        aspect_value = aspect_ratios[aspect_ratio]
        result["prompt"] += f" {aspect_value}"
        result["aspect_ratio"] = aspect_value.replace("--ar ", "")
        logger.debug(f"添加宽高比 '{aspect_ratio}': {aspect_value}")
    else:
        warning_msg = f"警告：找不到宽高比设置 '{aspect_ratio}'，将使用默认。"
        logger.warning(warning_msg)
        print(warning_msg)

    # 添加质量设置
    quality_settings = config.get("quality_settings", {})
    if quality in quality_settings:
        quality_value = quality_settings[quality]
        result["prompt"] += f" {quality_value}"
        result["quality"] = quality_value.replace("--q ", "")
        logger.debug(f"添加质量设置 '{quality}': {quality_value}")
    else:
        warning_msg = f"警告：找不到质量设置 '{quality}'，将使用默认。"
        logger.warning(warning_msg)
        print(warning_msg)

    # 添加版本设置
    style_versions = config.get("style_versions", {})
    if version in style_versions:
        version_value = style_versions[version]
        result["prompt"] += f" {version_value}"
        result["version"] = version_value.replace("--v ", "")
        logger.debug(f"添加版本设置 '{version}': {version_value}")
    else:
        warning_msg = f"警告：找不到版本设置 '{version}'，将使用默认。"
        logger.warning(warning_msg)
        print(warning_msg)

    # 去除首尾空格
    result["prompt"] = result["prompt"].strip()
    logger.info(f"提示词生成成功，长度: {len(result['prompt'])}")

    return result

def save_text_prompt(prompt_text, concept_key, variation_key=None):
    """保存生成的文本提示词到文件（可选）"""
    # 目录已由 ensure_directories 函数创建
    logger.info(f"正在保存提示词文本，概念: {concept_key}, 变体: {variation_key or 'None'}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    variation_str = f"_{variation_key}" if variation_key else ""
    filename = f"{concept_key}{variation_str}_prompt_{timestamp}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    logger.debug(f"保存提示词到文件: {filepath}")

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(prompt_text)
        success_msg = f"提示词文本已保存到: {filepath}"
        logger.info(success_msg)
        print(success_msg)
        return filepath
    except IOError as e:
        error_msg = f"错误：无法保存提示词文本到 {filepath} - {e}"
        logger.error(error_msg)
        print(error_msg)
        return None

def copy_to_clipboard(text):
    """将文本复制到剪贴板"""
    logger.debug("尝试复制文本到剪贴板")
    if not PYPERCLIP_AVAILABLE:
        warning_msg = "警告: pyperclip 模块不可用，无法复制到剪贴板。"
        logger.warning(warning_msg)
        print(warning_msg)
        print("请使用 'uv pip install pyperclip' 安装。")
        return False
    try:
        import pyperclip
        pyperclip.copy(text)
        logger.info("文本已成功复制到剪贴板")
        return True
    except Exception as e:
        error_msg = f"无法复制到剪贴板: {e}"
        logger.error(error_msg)
        print(error_msg)
        return False

def call_imagine_api(prompt_data, api_key, hook_url=None, notify_id=None, max_retries=1):
    """调用TTAPI的 /imagine 接口

    参数:
    - prompt_data: 包含提示词和参数的字典
    - api_key: TTAPI API密钥
    - hook_url: 可选的webhook URL，用于接收任务完成通知
    - notify_id: 可选的通知ID，用于识别回调请求
    - max_retries: 最大重试次数（默认为1）
    """
    url = f"{TTAPI_BASE_URL}/imagine"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    # 获取生成模式，默认为 fast
    mode = prompt_data.get("mode", "fast")
    logger.info(f"准备调用 /imagine API，模式: {mode}")

    # 根据模式设置超时时间
    if mode == "relax":
        timeout = 600  # relax模式默认超时时间更长
    else:
        timeout = 300  # fast和turbo模式默认超时时间

    # 构建请求体
    payload = {
        "prompt": prompt_data["prompt"],
        "mode": mode,
        "timeout": timeout
    }

    # 添加 webhook 相关参数
    if hook_url:
        payload["hookUrl"] = hook_url
        logger.info(f"使用 webhook URL: {hook_url}")
        if notify_id:
            payload["notifyId"] = notify_id
            logger.debug(f"使用通知ID: {notify_id}")

    logger.info(f"正在调用 /imagine API...")
    logger.debug(f"请求参数: {payload}")
    print(f"正在调用 /imagine API...")
    print(f"请求参数: {payload}")

    # 重试逻辑
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"第 {attempt} 次重试调用 /imagine API...")
                print(f"第 {attempt} 次重试调用 /imagine API...")
                time.sleep(2)  # 重试前等待 2 秒

            response = requests.post(url, headers=headers, json=payload, timeout=30) # 增加请求超时

            # 打印详细的响应信息以便调试
            logger.debug(f"API 响应状态码: {response.status_code}")
            print(f"API 响应状态码: {response.status_code}")

            try:
                response_json = response.json()
                logger.debug(f"API 响应内容: {response_json}")
                print(f"API 响应内容: {response_json}")
            except:
                logger.warning(f"API 响应不是有效的 JSON: {response.text}")
                print(f"API 响应文本: {response.text}")

            response.raise_for_status() # 对 >= 400 的状态码抛出异常

            result = response.json()
            if result.get("status") == "SUCCESS" and result.get("data", {}).get("jobId"):
                job_id = result["data"]["jobId"]
                success_msg = f"任务成功提交，Job ID: {job_id}"
                logger.info(success_msg)
                print(success_msg)
                return job_id
            else:
                error_msg = f"API 提交失败: {result.get('message', '未知错误')}"
                logger.error(error_msg)
                logger.error(f"完整响应: {result}")
                print(error_msg)
                print(f"完整响应: {result}")

                # 如果还有重试机会，继续重试
                if attempt < max_retries:
                    continue
                return None

        except requests.exceptions.RequestException as e:
            error_msg = f"调用 /imagine API 时出错: {e}"
            logger.error(error_msg)
            print(error_msg)

            # 如果还有重试机会，继续重试
            if attempt < max_retries:
                continue
            return None

        except json.JSONDecodeError as e:
            error_msg = f"错误：无法解析来自 /imagine API 的响应。"
            logger.error(error_msg)
            logger.error(f"解析错误: {e}")
            print(error_msg)
            print(f"解析错误: {e}")

            # 如果还有重试机会，继续重试
            if attempt < max_retries:
                continue
            return None

    # 如果所有重试都失败，返回 None
    logger.error("所有重试尝试均失败")
    return None

def poll_for_result(job_id, api_key, max_retries_per_poll=1):
    """轮询 /fetch 接口获取任务结果

    参数:
    - job_id: 任务ID
    - api_key: TTAPI API密钥
    - max_retries_per_poll: 每次轮询的最大重试次数（默认为1）
    """
    url = f"{TTAPI_BASE_URL}/fetch"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"jobId": job_id}
    start_time = time.time()

    logger.info(f"开始轮询任务结果，Job ID: {job_id}")
    logger.debug(f"轮询间隔: {POLL_INTERVAL_SECONDS}s, 超时: {FETCH_TIMEOUT_SECONDS}s")
    print(f"正在轮询任务结果 (Job ID: {job_id})... (间隔: {POLL_INTERVAL_SECONDS}s, 超时: {FETCH_TIMEOUT_SECONDS}s)")

    poll_count = 0
    while time.time() - start_time < FETCH_TIMEOUT_SECONDS:
        poll_count += 1
        logger.debug(f"轮询次数: {poll_count}")

        # 重试逻辑
        for attempt in range(max_retries_per_poll + 1):
            try:
                if attempt > 0:
                    logger.info(f"第 {attempt} 次重试轮询请求...")
                    print(f"  第 {attempt} 次重试轮询请求...")
                    time.sleep(1)  # 重试前等待 1 秒

                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()

                status = result.get("status")
                data = result.get("data", {})
                progress = data.get("progress", "N/A") if isinstance(data, dict) else "N/A" # data可能是空列表

                logger.debug(f"当前状态: {status}, 进度: {progress}%")
                print(f"  当前状态: {status}, 进度: {progress}%")

                if status == "SUCCESS":
                    success_msg = "任务成功完成!"
                    logger.info(success_msg)
                    print(success_msg)
                    if isinstance(data, dict) and data.get("cdnImage"):
                        image_url = data["cdnImage"]
                        logger.info(f"获取到图像 URL: {image_url}")
                        return image_url
                    else:
                        error_msg = "错误：任务成功但未找到 cdnImage URL。"
                        logger.error(error_msg)
                        logger.error(f"完整响应: {result}")
                        print(error_msg)
                        print(f"完整响应: {result}")
                        return None
                elif status == "FAILED":
                    error_msg = f"任务失败: {result.get('message', '未知原因')}"
                    logger.error(error_msg)
                    logger.error(f"完整响应: {result}")
                    print(error_msg)
                    print(f"完整响应: {result}")
                    return None
                # PENDING_QUEUE 或 ON_QUEUE，继续轮询
                elif status not in ["PENDING_QUEUE", "ON_QUEUE"]:
                    warning_msg = f"收到未知或意外的状态: {status}"
                    logger.warning(warning_msg)
                    logger.warning(f"完整响应: {result}")
                    print(warning_msg)
                    print(f"完整响应: {result}")
                    # 可以选择在这里停止或继续轮询

                # 如果没有返回或错误，跳出重试循环，继续轮询
                break

            except requests.exceptions.Timeout:
                logger.warning("  轮询请求超时。")
                print("  轮询请求超时，将在下次尝试。")
                # 如果还有重试机会，继续重试
                if attempt < max_retries_per_poll:
                    continue
            except requests.exceptions.RequestException as e:
                logger.error(f"  轮询 /fetch API 时出错: {e}")
                print(f"  轮询 /fetch API 时出错: {e}")
                # 如果还有重试机会，继续重试
                if attempt < max_retries_per_poll:
                    continue
            except json.JSONDecodeError as e:
                logger.error(f"错误：无法解析来自 /fetch API 的响应。")
                logger.error(f"解析错误: {e}")
                print(f"错误：无法解析来自 /fetch API 的响应。")
                # 如果还有重试机会，继续重试
                if attempt < max_retries_per_poll:
                    continue

        # 等待下一次轮询
        time.sleep(POLL_INTERVAL_SECONDS)

    error_msg = f"错误：获取任务结果超时 ({FETCH_TIMEOUT_SECONDS}秒)。"
    logger.error(error_msg)
    print(error_msg)
    return None

def save_image_metadata(image_id, job_id, filename, filepath, url, prompt, concept, variation=None, components=None, seed=None):
    """保存图像元数据到 metadata/images_metadata.json 文件"""
    logger.info(f"正在保存图像元数据，图像 ID: {image_id}")
    try:
        # 目录已由 ensure_directories 函数创建
        metadata_dir = META_DIR
        metadata_file = os.path.join(metadata_dir, "images_metadata.json")
        logger.debug(f"元数据文件路径: {metadata_file}")

        # 加载现有元数据或创建新的
        if os.path.exists(metadata_file):
            logger.debug("元数据文件已存在，正在加载")
            with open(metadata_file, 'r', encoding='utf-8') as f:
                try:
                    metadata_data = json.load(f)
                    logger.debug(f"已加载元数据，包含 {len(metadata_data.get('images', []))} 个图像条目")
                except json.JSONDecodeError:
                    logger.warning("元数据文件格式错误，创建新的元数据")
                    metadata_data = {"images": [], "version": "1.0"}
        else:
            logger.debug("元数据文件不存在，创建新的元数据")
            metadata_data = {"images": [], "version": "1.0"}

        # 添加新图像的元数据
        image_metadata = {
            "id": image_id,
            "job_id": job_id,
            "filename": filename,
            "filepath": filepath,
            "url": url,
            "prompt": prompt,
            "concept": concept,
            "variation": variation,
            "components": components or [],
            "seed": seed,
            "created_at": datetime.now().isoformat()
        }

        metadata_data["images"].append(image_metadata)
        logger.debug(f"添加新的元数据条目，现在共有 {len(metadata_data['images'])} 个条目")

        # 保存元数据
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=2, ensure_ascii=False)

        success_msg = f"图像元数据已保存到: {metadata_file}"
        logger.info(success_msg)
        print(success_msg)
        return True
    except Exception as e:
        error_msg = f"警告：保存元数据时出错 - {e}"
        logger.error(error_msg)
        print(error_msg)
        return False

def download_and_save_image(image_url, job_id, prompt, concept_key, variation_key=None, components=None, seed=None, max_retries=1):
    """下载图像并保存到 images 目录，同时保存元数据

    参数:
    - image_url: 图像 URL
    - job_id: 任务ID
    - prompt: 提示词文本
    - concept_key: 概念键
    - variation_key: 变体键（可选）
    - components: 组件列表（可选）
    - seed: 种子值（可选）
    - max_retries: 最大重试次数（默认为1）
    """
    logger.info(f"开始下载图像，概念: {concept_key}, 变体: {variation_key or 'None'}")
    print("开始下载图像...")
    # 目录已由 ensure_directories 函数创建

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    variation_str = f"_{variation_key}" if variation_key else ""
    # 尝试从 URL 获取文件扩展名，如果失败则默认为 .png
    try:
        file_ext = os.path.splitext(image_url.split('?')[0])[-1] or ".png" # 去掉查询参数再获取扩展名
        if not file_ext.startswith('.'): # 确保有 .
             file_ext = ".png"
    except:
        file_ext = ".png"

    filename = f"{concept_key}{variation_str}_image_{timestamp}{file_ext}"
    filepath = os.path.join(IMAGE_DIR, filename)
    logger.debug(f"图像将保存到: {filepath}")

    logger.info(f"正在从 {image_url} 下载图像...")
    print(f"正在从 {image_url} 下载图像...")

    # 重试逻辑
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"第 {attempt} 次重试下载图像...")
                print(f"第 {attempt} 次重试下载图像...")
                time.sleep(2)  # 重试前等待 2 秒

            response = requests.get(image_url, stream=True, timeout=60) # 增加下载超时
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            success_msg = f"图像已成功保存到: {filepath}"
            logger.info(success_msg)
            print(success_msg)

            # 生成唯一ID并保存元数据
            image_id = str(uuid.uuid4())
            logger.debug(f"生成图像 ID: {image_id}")
            save_image_metadata(
                image_id=image_id,
                job_id=job_id,
                filename=filename,
                filepath=filepath,
                url=image_url,
                prompt=prompt,
                concept=concept_key,
                variation=variation_key,
                components=components,
                seed=seed
            )

            return filepath

        except requests.exceptions.RequestException as e:
            error_msg = f"错误：下载图像时出错 - {e}"
            logger.error(error_msg)
            print(error_msg)
            # 清理可能已创建的不完整文件
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.debug(f"删除不完整的图像文件: {filepath}")
                except OSError as e:
                    logger.warning(f"无法删除不完整的图像文件: {e}")
                    pass # 忽略删除错误

            # 如果还有重试机会，继续重试
            if attempt < max_retries:
                continue
            return None

        except IOError as e:
            error_msg = f"错误：保存图像到 {filepath} 时出错 - {e}"
            logger.error(error_msg)
            print(error_msg)

            # 如果还有重试机会，继续重试
            if attempt < max_retries:
                continue
            return None

    # 如果所有重试都失败，返回 None
    logger.error("所有下载尝试均失败")
    return None

def ensure_directories():
    """确保必要的目录存在"""
    logger.debug("检查并创建必要的目录")
    for directory in [OUTPUT_DIR, IMAGE_DIR, META_DIR]:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                success_msg = f"创建目录: {directory}"
                logger.info(success_msg)
                print(success_msg)
            except OSError as e:
                error_msg = f"警告：无法创建目录 {directory} - {e}"
                logger.error(error_msg)
                print(error_msg)
        else:
            logger.debug(f"目录已存在: {directory}")

def main():
    parser = argparse.ArgumentParser(
        description="使用 TTAPI 生成 Cell 杂志封面图像",
        epilog="需要设置环境变量 TTAPI_API_KEY"
    )

    # 基本命令行参数
    parser.add_argument("--list", action="store_true", help="列出所有可用的创意概念")
    parser.add_argument("--concept", type=str, help="要使用的创意概念的键")
    parser.add_argument("--list-variations", type=str, metavar='CONCEPT_KEY', help="列出指定概念的所有变体")
    parser.add_argument("--variation", type=str, help="要使用的变体的键 (可选)")
    parser.add_argument("--aspect", type=str, default="cell_cover", help="宽高比设置的键 (默认: cell_cover)")
    parser.add_argument("--quality", type=str, default="high", help="质量设置的键 (默认: high)")
    parser.add_argument("--version", type=str, default="v6", help="Midjourney 版本的键 (默认: v6)")
    parser.add_argument("--mode", type=str, default="fast", choices=["relax", "fast", "turbo"],
                      help="生成模式: relax(约120秒), fast(约60秒), turbo(约30秒) (默认: fast)")
    parser.add_argument("--clipboard", action="store_true", help="将生成的提示词复制到剪贴板")
    parser.add_argument("--save-prompt", action="store_true", help="同时保存生成的提示词文本到 outputs 目录")

    # Webhook 相关参数
    parser.add_argument("--hook-url", type=str, help="Webhook URL，用于接收任务完成通知（异步模式必需）")
    parser.add_argument("--notify-id", type=str, help="通知ID，用于识别回调请求（可选）")

    # 日志相关参数
    parser.add_argument("--verbose", action="store_true", help="显示详细的调试日志")

    args = parser.parse_args()

    # 根据命令行参数设置日志级别
    global logger
    logger = setup_logging(args.verbose)
    logger.info("脚本启动")

    config = load_config()
    api_key = get_api_key() # 在开始时检查 API Key

    # 确保必要的目录存在
    ensure_directories()

    # 处理列出创意概念命令
    if args.list:
        list_concepts(config)
        return

    # 处理列出变体命令
    if args.list_variations:
        list_variations(config, args.list_variations)
        return

    # 生成图像
    if not args.concept:
        parser.print_help()
        print("错误：生成图像时必须指定一个创意概念。使用 --list 查看可用概念。")
        sys.exit(1)

    # 检查异步模式所需的 webhook URL
    if not args.hook_url:
        warning_msg = "警告：未指定 --hook-url，将使用同步模式。建议使用异步模式以提高可靠性。"
        logger.warning(warning_msg)
        print(warning_msg)
        print("如果任务生成时间过长，脚本可能会超时。")

    # 1. 生成提示词数据
    prompt_data = generate_prompt_text(
        config,
        args.concept,
        args.variation,
        args.aspect,
        args.quality,
        args.version
    )

    if not prompt_data:
        sys.exit(1) # generate_prompt_text 内部会打印错误

    # 添加模式参数
    prompt_data["mode"] = args.mode

    print("生成的 Midjourney 提示词:")
    print("-" * 80)
    print(prompt_data["prompt"])
    print("-" * 80)

    # (可选) 保存提示词文本
    if args.save_prompt:
        save_text_prompt(prompt_data["prompt"], args.concept, args.variation)

    # (可选) 复制提示词到剪贴板
    if args.clipboard:
        if copy_to_clipboard(prompt_data["prompt"]):
            print("提示词文本已复制到剪贴板")

    # 2. 调用 /imagine API
    job_id = call_imagine_api(
        prompt_data=prompt_data,
        api_key=api_key,
        hook_url=args.hook_url,
        notify_id=args.notify_id
    )

    if not job_id:
        print("未能提交图像生成任务。")
        sys.exit(1)

    # 如果指定了 webhook URL，则使用异步模式
    if args.hook_url:
        logger.info(f"任务已提交，任务ID: {job_id}")
        logger.info(f"使用异步模式，结果将发送到: {args.hook_url}")

        print(f"任务已提交，任务ID: {job_id}")
        print(f"任务完成后，结果将发送到: {args.hook_url}")
        if args.notify_id:
            logger.debug(f"通知ID: {args.notify_id}")
            print(f"通知ID: {args.notify_id}")
        print("脚本将退出，您可以关闭终端或继续其他操作。")
        return
    else:
        # 如果没有指定 webhook URL，则使用同步模式（轮询）
        logger.info("使用同步模式，开始轮询任务结果...")
        print("使用同步模式，开始轮询任务结果...")
        result = poll_for_result(job_id, api_key)
        if not result:
            print("未能获取生成的图像 URL。")
            sys.exit(1)

        # 获取图像 URL
        image_url = result

        # 从轮询结果中提取可能的组件和种子值
        components = None
        seed = None
        # 注意：在实际实现中，这里应该从轮询结果中提取这些信息

        # 4. 下载并保存图像
        saved_image_path = download_and_save_image(
            image_url=image_url,
            job_id=job_id,
            prompt=prompt_data["prompt"],
            concept_key=args.concept,
            variation_key=args.variation,
            components=components,
            seed=seed
        )
        if not saved_image_path:
            print("未能成功下载或保存图像。")
            sys.exit(1)

        print("图像生成和保存流程完成!")

if __name__ == "__main__":
    main()