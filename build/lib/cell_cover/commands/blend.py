# -*- coding: utf-8 -*-
import os
import base64
import mimetypes
import logging
import uuid

# 从 utils 导入必要的函数
from ..utils.api import call_blend_api, poll_for_result
from ..utils.file_handler import download_and_save_image, save_image_metadata

logger = logging.getLogger(__name__)

def handle_blend(args, config, logger, api_key):
    """处理 'blend' 命令。"""
    if not (2 <= len(args.image_paths) <= 5):
        logger.error(f"混合需要 2 到 5 张图片，提供了 {len(args.image_paths)} 张。")
        print(f"错误：混合需要 2 到 5 张图片，提供了 {len(args.image_paths)} 张。")
        return 1

    base64_images = []
    for img_path in args.image_paths:
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
        dimensions=args.dimensions,
        mode=args.mode,
        hook_url=args.hook_url
    )

    if submit_result:
        job_id = submit_result
        logger.info(f"混合任务提交成功，Job ID: {job_id}")
        job_id_for_save = job_id
        prompt_text_for_save = f"blend: {', '.join(os.path.basename(p) for p in args.image_paths)}"

        if not args.hook_url:
            logger.info("未提供 Webhook URL，将开始轮询混合结果...")
            print("Polling for blend result...")
            final_result = poll_for_result(logger, job_id, api_key)
            if final_result and final_result.get("cdnImage"): # Use cdnImage
                image_url = final_result.get("cdnImage")
                logger.info(f"混合任务完成，图像 URL: {image_url}")
                download_success, saved_path, image_seed = download_and_save_image(
                    logger,
                    image_url,
                    job_id,
                    prompt_text_for_save,
                    "blend", # concept
                    None, # variations
                    None, # global_styles
                    None, # original_job_id
                    None, # action_code
                    final_result.get("components"),
                    final_result.get("seed")
                )
                if download_success:
                    seed_for_save = image_seed
                    save_image_metadata(
                        logger,
                        final_result.get("image_id", str(uuid.uuid4())),
                        job_id_for_save,
                        os.path.basename(saved_path),
                        saved_path,
                        image_url,
                        prompt_text_for_save,
                        "blend", # concept
                        None, # variations
                        None, # global_styles
                        final_result.get("components"),
                        seed_for_save,
                        None # original_job_id
                    )
                    logger.info(f"混合图像和元数据已保存: {saved_path}")
                    print(f"混合图像和元数据已保存: {saved_path}")
                    return 0
                else:
                    logger.error("混合图像下载或保存失败。")
                    print("错误：混合图像下载或保存失败。")
                    return 1
            else:
                status = final_result.get('status') if final_result else 'N/A'
                logger.error(f"轮询混合任务结果失败或未获取到图像 URL。最后状态: {status}")
                print(f"错误：轮询混合任务结果失败或未获取到图像 URL。最后状态: {status}")
                if job_id_for_save:
                     save_image_metadata(
                        logger,
                        None, # No image_id
                        job_id_for_save,
                        None, # filename
                        None, # filepath
                        None, # url
                        prompt_text_for_save,
                        "blend",
                        None, None, None, None, None # variations, styles, components, seed, original_job_id
                    )
                     logger.info(f"已保存混合任务 {job_id_for_save} 的基本元数据（无图像）。")
                return 1
        else: # Webhook provided
            logger.info("提供了 Webhook URL，混合任务将在后台处理。")
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
