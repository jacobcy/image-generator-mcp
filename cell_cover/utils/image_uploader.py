# -*- coding: utf-8 -*-
import os
import requests
import logging
import json
from datetime import datetime

# Import get_api_key from the config module in the parent directory
# Assume get_api_key can handle different service names
from .config import get_api_key

# Setup logger if used standalone, otherwise rely on parent logger
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def upload_to_imgbb(image_path, api_key):
    """
    Uploads an image file to ImgBB.

    Args:
        image_path (str): The path to the image file.
        api_key (str): Your ImgBB API key.

    Returns:
        dict: A dictionary containing the upload result.
              {'success': True, 'url': 'image_url'} on success.
              {'success': False, 'message': 'error_message'} on failure.
    """
    url = "https://api.imgbb.com/1/upload"
    try:
        with open(image_path, "rb") as file:
            payload = {
                "key": api_key,
            }
            files = {
                "image": file
            }
            response = requests.post(url, payload, files=files, timeout=60)
            response.raise_for_status()  # Raise HTTPError for bad responses

        result = response.json()

        if result.get("data") and result["data"].get("url"):
            return {"success": True, "url": result["data"]["url"]}
        else:
            error_message = result.get("error", {}).get("message", "Unknown error from ImgBB API")
            if isinstance(error_message, dict):
                error_message = error_message.get('message', str(error_message))
            logger.error(f"ImgBB upload failed: {error_message}")
            logger.debug(f"ImgBB API full response: {result}")
            return {"success": False, "message": f"ImgBB API Error: {error_message}"}

    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        return {"success": False, "message": "Image file not found"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error uploading image to ImgBB: {e}")
        return {"success": False, "message": f"Network or API error: {e}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred during ImgBB upload: {e}")
        return {"success": False, "message": f"Unexpected error: {e}"}


# 上传历史记录文件路径
# 假设存储在 metadata 目录下
UPLOAD_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "metadata", "upload_history.json")

def load_upload_history(logger):
    """加载上传历史记录

    Args:
        logger: 日志记录器

    Returns:
        list: 上传历史记录列表
    """
    if not os.path.exists(UPLOAD_HISTORY_FILE):
        logger.debug(f"上传历史记录文件不存在: {UPLOAD_HISTORY_FILE}")
        return []

    try:
        with open(UPLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
            logger.debug(f"成功加载上传历史记录，包含 {len(history)} 条记录")
            return history
    except Exception as e:
        logger.error(f"加载上传历史记录失败: {e}")
        return []

def save_upload_history(logger, history, new_entry):
    """保存上传历史记录

    Args:
        logger: 日志记录器
        history: 现有历史记录列表
        new_entry: 新的上传记录

    Returns:
        bool: 是否成功保存
    """
    # 确保 metadata 目录存在
    os.makedirs(os.path.dirname(UPLOAD_HISTORY_FILE), exist_ok=True)

    # 添加新记录
    history.insert(0, new_entry)  # 将新记录添加到列表开头

    try:
        with open(UPLOAD_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        logger.debug(f"成功保存上传历史记录，当前共 {len(history)} 条记录")
        return True
    except Exception as e:
        logger.error(f"保存上传历史记录失败: {e}")
        return False

def find_in_upload_history(logger, local_path):
    """在上传历史记录中查找指定文件的上传记录

    Args:
        logger: 日志记录器
        local_path: 本地文件路径

    Returns:
        dict: 如果找到，返回上传记录；否则返回 None
    """
    history = load_upload_history(logger)

    # 规范化路径以便于比较
    normalized_path = os.path.normpath(local_path)

    for entry in history:
        if os.path.normpath(entry.get("local_path", "")) == normalized_path:
            logger.info(f"在上传历史记录中找到文件: {local_path}")
            return entry

    logger.debug(f"在上传历史记录中未找到文件: {local_path}")
    return None

def process_cref_image(logger, cref_path):
    """处理参考图片，如果是本地文件则上传到图床

    Args:
        logger: 日志记录器
        cref_path: 参考图片路径或URL

    Returns:
        str: 图片URL，如果处理失败则返回None
    """
    # 如果是URL，直接返回
    if cref_path.startswith(('http://', 'https://')):
        logger.debug(f"Cref path is already a URL: {cref_path}")
        return cref_path

    # 检查本地文件是否存在
    if not os.path.exists(cref_path):
        logger.error(f"参考图片文件不存在: {cref_path}")
        # Use print for direct user feedback on critical errors
        print(f"错误：参考图片文件不存在: {cref_path}")
        return None

    # 先检查上传历史记录
    history_entry = find_in_upload_history(logger, cref_path)
    if history_entry and history_entry.get("result", {}).get("success") and history_entry.get("result", {}).get("url"):
        url = history_entry["result"]["url"]
        logger.info(f"从上传历史记录中找到图片URL: {url}")
        print(f"使用已上传的图片: {os.path.basename(cref_path)}")
        return url

    # 获取 ImgBB API 密钥
    # Pass the service name 'imgbb' to get_api_key
    imgbb_api_key = get_api_key(logger, service="imgbb") # Pass logger and service name
    if not imgbb_api_key:
        logger.error("未找到 ImgBB API 密钥，请设置环境变量 IMGBB_API_KEY")
        print("错误：未找到 ImgBB API 密钥，请设置环境变量 IMGBB_API_KEY")
        return None
    logger.debug("Successfully retrieved ImgBB API key.")

    # 上传图片到 ImgBB
    logger.info(f"正在上传参考图片到图床: {cref_path}")
    # Use print for progress indication visible to the user
    print(f"正在上传参考图片: {os.path.basename(cref_path)} ...") # Keep progress print

    result = upload_to_imgbb(cref_path, imgbb_api_key)
    if result["success"]:
        logger.info(f"参考图片上传成功: {result['url']}")

        # 保存上传记录
        history = load_upload_history(logger)
        new_entry = {
            "local_path": cref_path,
            "filename": os.path.basename(cref_path),
            "upload_time": datetime.now().isoformat(),
            "result": result
        }
        save_upload_history(logger, history, new_entry)

        return result['url']
    else:
        error_msg = result.get('message', '未知错误')
        logger.error(f"参考图片上传失败: {error_msg}")
        print(f"错误：参考图片上传失败: {error_msg}")
        return None