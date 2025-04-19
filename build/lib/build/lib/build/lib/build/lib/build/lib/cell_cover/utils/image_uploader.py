\
# -*- coding: utf-8 -*-
import os
import requests
import logging

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
        return result['url']
    else:
        error_msg = result.get('message', '未知错误')
        logger.error(f"参考图片上传失败: {error_msg}")
        print(f"错误：参考图片上传失败: {error_msg}")
        return None