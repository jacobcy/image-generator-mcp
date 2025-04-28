# -*- coding: utf-8 -*-
import os
import base64
import mimetypes
import logging
import uuid
from typing import List, Optional

# 从 utils 导入必要的函数 - 使用统一的元数据管理模块
from ..utils.metadata_manager import save_image_metadata

# 区分 api.py (包含 normalize_api_response) 和 api_client.py (包含实际 API 调用)
from ..utils.api import normalize_api_response
from ..utils.api_client import call_blend_api, poll_for_result
# from ..utils.api import call_blend_api, poll_for_result, normalize_api_response # 旧的导入方式

from ..utils.image_handler import download_and_save_image
from ..utils.image_metadata import load_all_metadata, _build_metadata_index
from ..utils.metadata_manager import _generate_expected_filename

logger = logging.getLogger(__name__)

def handle_blend(
    image_paths: List[str],
    dimensions: str = "1024x1024",
    mode: str = "relax",
    hook_url: Optional[str] = None,
    config=None,
    api_key=None
):
    """处理 'blend' 命令。"""
    if not (2 <= len(image_paths) <= 5):
        logger.error(f"混合需要 2 到 5 张图片，提供了 {len(image_paths)} 张。")
        print(f"错误：混合需要 2 到 5 张图片，提供了 {len(image_paths)} 张。")
        return 1

    base64_images = []
    for img_path in image_paths:
        if not os.path.exists(img_path):
            logger.error(f"提供的图片路径不存在: {img_path}")
            print(f"错误：提供的图片路径不存在: {img_path}")
            return 1
        try:
            mime_type, _ = mimetypes.guess_type(img_path)
            if not mime_type or not mime_type.startswith('image'):
                logger.warning(f"无法确定图片类型或文件不是图片: {img_path} (MIME: {mime_type}) - 正在尝试...")
                mime_type = 'image/png' # Default assumption

            with open(img_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                base64_images.append(f"data:{mime_type};base64,{encoded_string}")
            logger.info(f"已编码图片: {img_path}")
        except Exception as e:
            logger.error(f"编码图片时出错 {img_path}: {e}")
            print(f"错误：编码图片时出错 {img_path}: {e}")
            return 1

    logger.info(f"准备提交 {len(base64_images)} 张图片进行混合...")

    submit_result = call_blend_api(
        logger=logger,
        api_key=api_key,
        img_base64_array=base64_images,
        dimensions=dimensions,
        mode=mode,
        hook_url=hook_url
    )

    if submit_result:
        job_id = submit_result
        logger.info(f"混合任务提交成功，Job ID: {job_id}")
        job_id_for_save = job_id
        prompt_text_for_save = f"blend: {', '.join(os.path.basename(p) for p in image_paths)}"

        if not hook_url:
            logger.info("未提供 Webhook URL，将开始轮询混合结果...")
            print("Polling for blend result...")
            poll_response = poll_for_result(logger, job_id, api_key) # Renamed variable

            if poll_response:
                final_status, api_data = poll_response # Unpack the tuple

                # Check if polling was successful and got data
                if final_status == "SUCCESS" and isinstance(api_data, dict):
                    # Get URL from api_data (data dict)
                    image_url_key = 'url' if 'url' in api_data else 'cdnImage' # Prefer url after normalization potentially
                    image_url = api_data.get(image_url_key)

                    if image_url:
                        logger.info(f"混合任务完成，图像 URL: {image_url}")

                        # 标准化API结果 (use api_data)
                        normalized_result = normalize_api_response(logger, api_data)

                        # --- 生成期望的文件名 --- #
                        try:
                            all_tasks = load_all_metadata(logger)
                            all_tasks_index = _build_metadata_index(all_tasks)
                            # Blend tasks need special handling for filename? Assuming 'blend' concept for now.
                            normalized_result['job_id'] = job_id # Ensure job_id
                            normalized_result['concept'] = 'blend' # Set concept for filename generation
                            expected_filename = _generate_expected_filename(logger, normalized_result, all_tasks_index)
                        except Exception as e:
                            logger.error(f"为混合任务 {job_id} 生成期望文件名时出错: {e}，将使用 job_id 作为备用名。")
                            expected_filename = f"blend_{job_id}.png"
                        # ---------------------- #

                        download_success, saved_path, image_seed = download_and_save_image(
                            logger,
                            image_url,
                            job_id,
                            prompt_text_for_save,
                            expected_filename, # Use generated filename
                            "blend", # concept
                            None, # variations
                            None, # global_styles
                            None, # original_job_id
                            None, # action_code
                            None, # Components removed
                            normalized_result.get("seed") # Use seed from normalized
                        )
                        if download_success:
                            # Metadata is saved inside download_and_save_image
                            logger.info(f"混合图像和元数据已保存: {saved_path}")
                            print(f"混合图像和元数据已保存: {saved_path}")
                            # Update last succeed only if download is successful
                            write_last_succeed_job_id(logger, job_id)
                            return 0
                        else:
                            logger.error("混合图像下载或保存失败。")
                            print("错误：混合图像下载或保存失败。")
                            return 1
                    else:
                        # SUCCESS status but no image URL
                        logger.error(f"轮询混合任务结果成功，但未获取到图像 URL。")
                        print(f"错误：轮询混合任务结果成功，但未获取到图像 URL。")
                        # Save basic metadata anyway
                        normalized_result = normalize_api_response(logger, api_data or {})
                        save_image_metadata(
                            logger, None, job_id, None, None, None,
                            prompt_text_for_save, "blend", None, None, None,
                            normalized_result.get("seed"), None, status="polling_success_no_url"
                        )
                        return 1 # Return failure
                elif final_status == "FAILED":
                    # Handle FAILED status
                    error_message = api_data.get('message', '未知错误') if isinstance(api_data, dict) else '未知错误'
                    logger.error(f"轮询混合任务结果失败。API 消息: {error_message}")
                    print(f"错误：轮询混合任务结果失败。API 消息: {error_message}")
                    # Save basic metadata for failed attempt
                    normalized_result = normalize_api_response(logger, api_data or {})
                    save_image_metadata(
                        logger, None, job_id, None, None, None,
                        prompt_text_for_save, "blend", None, None, None,
                        normalized_result.get("seed"), None, status=f"polling_failed: {final_status}"
                    )
                    return 1 # Return failure
                else:
                    # Handle unexpected status
                    logger.error(f"轮询混合任务结果返回意外状态: {final_status}")
                    print(f"错误：轮询混合任务结果返回意外状态: {final_status}")
                    return 1 # Return failure
            else:
                # Handle poll_for_result returning None (timeout or other poll failure)
                logger.error(f"轮询混合任务 {job_id} 失败或超时。")
                print(f"错误：轮询混合任务 {job_id} 失败或超时。")
                # Save basic metadata for failed attempt
                save_image_metadata(
                    logger, None, job_id, None, None, None,
                    prompt_text_for_save, "blend", None, None, None, None, None,
                    status="polling_timeout_or_error"
                )
                return 1 # Return failure
        else: # Webhook provided
            logger.info("提供了 Webhook URL，混合任务将在后台处理。")
            # Save initial metadata (status will be updated by webhook handler later)
            save_image_metadata(
                logger,
                None, # No image_id yet
                job_id_for_save,
                None, # filename
                None, # filepath
                None, # url
                prompt_text_for_save,
                "blend",
                None, None, None, None, None # variations, styles, components, seed, original_job_id
            )
            logger.info(f"已保存混合任务 {job_id_for_save} 的初始元数据（无图像）。")
            return 0
    else: # 提交失败
         logger.error(f"混合任务提交失败 (API 调用未返回 Job ID)")
         print(f"错误：混合任务提交失败 (API 调用未返回 Job ID)")
         return 1
