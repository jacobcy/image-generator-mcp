#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图像处理模块
-----------
提供图像处理相关功能，包括图像加载、保存和处理。
"""

import os
import logging
from PIL import Image
import numpy as np
from datetime import datetime
from typing import Optional
import requests
import uuid
import json

# 从 utils 导入必要的函数 - 使用统一的元数据管理模块
from .metadata_manager import save_image_metadata
from .filesystem_utils import (
    ensure_directories, sanitize_filename
)

# 定义 IMAGE_DIR 本地 (移除 - 应动态确定)
# IMAGE_DIR = 'images'  

logger = logging.getLogger(__name__)

def save_image(image, filename=None, directory=None):
    """
    保存图像到指定目录。
    
    Args:
        image: PIL Image对象或numpy数组
        filename: 文件名，如果未提供则使用时间戳
        directory: 保存目录，如果未提供则使用默认图像目录
        
    Returns:
        str: 保存的文件路径
    """
    try:
        # 确保图像是PIL Image对象
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        
        # 设置默认目录 - 这里也应该移除，由调用者指定
        # if directory is None:
        #     directory = IMAGE_DIR # Removed dependency on global constant
        if directory is None:
            logger.error("save_image: 必须提供保存目录参数 (directory)")
            return None
        
        # 确保目录存在
        ensure_directories(logger, directory)
        
        # 如果未提供文件名，使用时间戳创建
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"image_{timestamp}.png"
        else:
            # 清理文件名
            filename = sanitize_filename(filename)
            # 确保有扩展名
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                filename += '.png'
        
        # 构建完整路径
        filepath = os.path.join(directory, filename)
        
        # 保存图像
        image.save(filepath)
        logger.info(f"图像已保存至: {filepath}")
        
        return filepath
    
    except Exception as e:
        logger.error(f"保存图像时出错: {e}")
        return None

def load_image(filepath):
    """
    从文件路径加载图像。
    
    Args:
        filepath: 图像文件路径
        
    Returns:
        PIL.Image: 加载的图像对象，失败则返回None
    """
    try:
        if not os.path.exists(filepath):
            logger.error(f"图像文件不存在: {filepath}")
            return None
        
        image = Image.open(filepath)
        return image
    
    except Exception as e:
        logger.error(f"加载图像时出错: {e}")
        return None

def resize_image(image, width=None, height=None, maintain_aspect=True):
    """
    调整图像尺寸。
    
    Args:
        image: PIL Image对象
        width: 目标宽度
        height: 目标高度
        maintain_aspect: 是否保持纵横比
        
    Returns:
        PIL.Image: 调整后的图像
    """
    try:
        if width is None and height is None:
            return image
        
        if maintain_aspect:
            if width is None:
                # 根据高度等比例缩放
                aspect = image.width / image.height
                width = int(height * aspect)
            elif height is None:
                # 根据宽度等比例缩放
                aspect = image.height / image.width
                height = int(width * aspect)
            else:
                # 当同时指定宽高时，使用适合的尺寸并保持纵横比
                img_aspect = image.width / image.height
                target_aspect = width / height
                
                if img_aspect > target_aspect:
                    # 图像较宽，以宽度为基准
                    new_width = width
                    new_height = int(width / img_aspect)
                else:
                    # 图像较高，以高度为基准
                    new_height = height
                    new_width = int(height * img_aspect)
                
                width, height = new_width, new_height
        
        return image.resize((width, height), Image.LANCZOS)
    
    except Exception as e:
        logger.error(f"调整图像尺寸时出错: {e}")
        return image

def download_and_save_image(
    logger: logging.Logger,
    image_url: str,
    job_id: str,
    prompt: str,
    expected_filename: Optional[str] = None,
    concept: Optional[str] = None,
    variations: Optional[list] = None,
    styles: Optional[list] = None,
    original_job_id: Optional[str] = None,
    action_code: Optional[str] = None,
    components: Optional[list] = None,
    seed: Optional[str] = None
) -> tuple[bool, Optional[str], Optional[str]]:
    """下载图像并保存到指定位置，同时更新元数据。

    Args:
        logger: 日志记录器
        image_url: 图像URL
        job_id: 任务ID
        prompt: 生成提示词
        expected_filename: 期望的文件名（可选，如果未提供将基于job_id生成）
        concept: 创意概念（可选）
        variations: 变体列表（可选）
        styles: 风格列表（可选）
        original_job_id: 原始任务ID（如果是派生图像）
        action_code: 操作代码（如果是由操作产生的）
        components: API结果中的组件列表（可选）
        seed: API结果中的种子值（可选）

    Returns:
        tuple[bool, Optional[str], Optional[str]]: 
          (成功状态, 文件路径或错误信息, 使用的种子)
    """
    logger.debug(f"进入 download_and_save_image, job_id={job_id}, url='{image_url[:50]}...'")

    if not image_url:
        logger.error("图像URL为空，无法下载。")
        return False, "url_empty", None
    
    # 获取用户主目录下的.crc目录
    home_dir = os.path.expanduser("~")
    crc_base_dir = os.path.join(home_dir, '.crc')
    
    # 读取配置获取输出目录
    output_dir = None
    try:
        with open(os.path.join(crc_base_dir, 'state', 'config.json'), 'r') as f:
            import json
            user_config = json.load(f)
            output_dir = user_config.get('output_dir')
    except (FileNotFoundError, json.JSONDecodeError):
        # 如果配置不存在或解析失败，使用默认值
        output_dir = os.path.join(crc_base_dir, 'output')
    
    # 创建基于概念的子目录
    concept_dir = concept if concept and concept != 'unknown' else 'general'
    save_dir = os.path.join(output_dir, concept_dir)
    
    # 生成文件名
    if not expected_filename or expected_filename == job_id + '.png':
        # 如果没有提供预期文件名，或者只是默认的job_id，则生成一个更好的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_prompt = prompt.split(',')[0].strip()[:30]  # 只用prompt的第一部分作为文件名
        short_prompt = sanitize_filename(short_prompt)
        filename = f"{short_prompt}_{timestamp}.png"
    else:
        filename = expected_filename
        # 确保文件名有扩展名
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename += '.png'
    
    # 构建完整路径
    filepath = os.path.join(save_dir, filename)
    
    logger.info(f"准备下载图像从 {image_url} 到 {filepath}")

    # 确保目录存在
    if not ensure_directories(logger, save_dir):
        logger.error(f"无法创建或访问保存目录: {save_dir}")
        return False, "dir_creation_error", None

    # 下载图像
    try:
        response = requests.get(image_url, stream=True, timeout=30)
        response.raise_for_status()

        # 保存图像
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"图像下载成功并保存到: {filepath}")
        
        # 保存元数据
        metadata_dir = os.path.join(crc_base_dir, 'metadata')
        if metadata_dir:
            try:
                save_image_metadata(
                    logger=logger,
                    image_id=str(uuid.uuid4()),
                    job_id=job_id,
                    filename=filename,
                    filepath=filepath,
                    url=image_url,
                    prompt=prompt,
                    concept=concept,
                    metadata_dir=metadata_dir,
                    variations=variations,
                    global_styles=styles,
                    components=components,
                    seed=seed,
                    original_job_id=original_job_id,
                    action_code=action_code
                )
                logger.info(f"已保存图像元数据，job_id={job_id}")
            except Exception as e:
                logger.error(f"保存元数据时出错: {str(e)}")
                # 继续，因为图像下载已成功
        else:
            logger.warning("未提供元数据目录，跳过元数据保存")
            
        return True, filepath, seed
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        logger.error(f"HTTP错误 ({status_code}): {str(e)}")
        return False, f"{status_code}_error", None
    except requests.exceptions.RequestException as e:
        logger.error(f"请求错误: {str(e)}")
        return False, "request_error", None
    except IOError as e:
        logger.error(f"IO错误: {str(e)}")
        return False, "io_error", None
    except Exception as e:
        logger.error(f"下载或保存图像时发生未知错误: {str(e)}")
        return False, "unknown_error", None