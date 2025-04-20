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
from .filesystem_utils import ensure_directories, sanitize_filename, IMAGE_DIR

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
        
        # 设置默认目录
        if directory is None:
            directory = IMAGE_DIR
        
        # 确保目录存在
        ensure_directories(directory)
        
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
    job_id: str, # 当前任务的Job ID (可能是原始的，也可能是Action的)
    prompt: str,
    concept: Optional[str] = None, # 当前任务的Concept
    variations: Optional[list] = None, # 当前任务的Variations
    styles: Optional[list] = None, # 当前任务的Styles
    original_job_id: Optional[str] = None, # 如果是Action，这是原始任务ID
    action_code: Optional[str] = None, # 如果是Action，这是执行的动作
    components: Optional[list] = None, # API 返回的 components (已弃用)
    seed: Optional[str] = None,
    # 新增参数以支持Action命名
    original_concept: Optional[str] = None, # 如果是Action，这是原始任务的Concept
    prefix: str = "" # 用于 recreate 等特殊情况
) -> tuple[bool, Optional[str], Optional[str]]:
    """Downloads an image, saves it using the standard naming convention, and saves metadata.

    Args:
        logger: Logger instance.
        image_url: URL of the image to download.
        job_id: The Job ID associated with this image.
        prompt: The prompt used.
        concept: The concept key (optional). **For actions, this should be inherited from original task.**
        variations: Variation keys used (optional).
        styles: Style keys used (optional).
        original_job_id: Original Job ID if this is a derived image (optional). **Critical for tracing action chains.**
        action_code: Action code if this resulted from an action (optional). **Identifies what action created this result.**
        components: Components list from API result (optional).
        seed: Seed value from API result (optional).
        original_concept: Original concept key if this is derived from an action.
        prefix: Prefix to add to the filename (e.g., 'recreate_').

    Returns:
        tuple[bool, Optional[str], Optional[str]]: (success status, saved filepath, seed used)
    """
    # Log entry point with improved logging for action chain info
    logger.debug(f"进入 download_and_save_image, job_id={job_id}, url='{image_url[:50]}...'")
    if action_code and original_job_id:
        logger.debug(f"这是一个 Action 结果: action_code={action_code}, original_job_id={original_job_id}, original_concept={original_concept}")
    if prefix:
        logger.debug(f"使用文件名前缀: {prefix}")

    if not image_url:
        logger.error("Image URL is empty, cannot download.")
        return False, None, None

    # 1. Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id_part = job_id[:6] if job_id else "nojobid"
    filename = ""

    # 清理变体和风格列表 (移除空字符串等)
    clean_variations = [v for v in variations if v] if variations else []
    clean_styles = [s for s in styles if s] if styles else []

    if action_code and original_job_id:
        # --- Action 任务命名 --- #
        # 使用传入的 original_concept，如果为空则尝试使用当前 concept 或 'unknown'
        base_concept = sanitize_filename(original_concept or concept or "unknown")
        orig_job_id_part = original_job_id[:6] if original_job_id else "noorigid"
        safe_action_code = sanitize_filename(action_code)
        filename = f"{prefix}{base_concept}-{orig_job_id_part}-{safe_action_code}-{timestamp}.png"
        logger.debug(f"生成 Action 文件名: {filename}")
    else:
        # --- 原始任务命名 --- #
        base_concept = sanitize_filename(concept or "direct")
        parts = [prefix + base_concept, job_id_part]
        if clean_variations:
            parts.append("-".join(map(sanitize_filename, clean_variations)))
        if clean_styles:
            parts.append("-".join(map(sanitize_filename, clean_styles)))
        parts.append(timestamp)
        filename = "-".join(parts) + ".png"
        logger.debug(f"生成原始任务文件名: {filename}")

    # Limit overall filename length (redundant if sanitize_filename works, but safe)
    filename = filename[:MAX_FILENAME_LENGTH] 
    if not filename.lower().endswith('.png'): # Ensure extension after potential truncation
         filename = filename[:MAX_FILENAME_LENGTH - 4] + ".png" 

    # Use IMAGE_DIR constant for the save directory
    save_dir = IMAGE_DIR
    filepath = os.path.join(save_dir, filename)

    logger.info(f"准备下载图像从 {image_url} 到 {filepath}")

    # 2. Ensure directory exists
    if not ensure_directories(logger, save_dir):
        logger.error(f"Failed to ensure save directory exists: {save_dir}")
        return False, None, None

    # 3. Download image
    try:
        response = requests.get(image_url, stream=True, timeout=60) # Add timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # 4. Save image
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Image successfully downloaded and saved to: {filepath}")
        
        # 5. Save Metadata (Included for compatibility)
        # Generate a local image ID if not provided (API result might have one)
        image_id = str(uuid.uuid4()) 
        
        # Use the seed passed in (likely from API result)
        final_seed = seed 

        # Log metadata saving with chain information if applicable
        if action_code and original_job_id:
            logger.info(f"保存 Action 结果元数据: action_code={action_code}, original_job_id={original_job_id}, original_concept={original_concept}")
            
        # Call the metadata saving function from image_metadata module
        # 确保传递所有关键参数，尤其是链条追踪需要的参数
        meta_success = save_image_metadata(
            logger,
            image_id=image_id, # Use generated local ID
            job_id=job_id,
            filename=filename, # 使用新生成的文件名
            filepath=filepath, # 使用新生成的路径
            url=image_url,
            prompt=prompt,
            concept=concept, # 传递当前任务的concept
            variations=variations, # 传递当前任务的variations
            global_styles=styles, # 传递当前任务的styles
            components=None, # Components removed
            seed=final_seed,
            original_job_id=original_job_id,
            action_code=action_code,
            status='completed'
        )
        if not meta_success:
            logger.error(f"Image downloaded to {filepath}, but failed to save metadata!")
            # Decide if this constitutes overall failure. Let's return True for download success.
            # The error is logged, and the user has the image file.
            
        return True, filepath, final_seed

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading image from {image_url}: {e}")
        return False, None, None
    except IOError as e:
        logger.error(f"Error saving image to {filepath}: {e}")
        return False, None, None
    except Exception as e:
        logger.error(f"An unexpected error occurred during image download/save: {e}", exc_info=True)
        return False, None, None