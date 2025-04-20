# -*- coding: utf-8 -*-
import os
import logging
import uuid
from datetime import datetime

# 从 utils 导入必要的函数
# Use the centralized metadata_manager
from ..utils.metadata_manager import (
    save_image_metadata, 
    find_initial_job_info # Needed if we pre-check concept?
)
from ..utils.api import call_imagine_api, poll_for_result, check_prompt
from ..utils.prompt import generate_prompt_text, save_text_prompt, copy_to_clipboard, PYPERCLIP_AVAILABLE
# download_and_save_image now handles saving metadata via metadata_manager
from ..utils.image_handler import download_and_save_image 
from ..utils.image_uploader import process_cref_image
# Import file_handler only for directory constants/functions if needed
from ..utils.file_handler import OUTPUT_DIR

logger = logging.getLogger(__name__)

def handle_create(args, config, logger, api_key):
    """处理 'create' 命令。"""
    # --- 1. 处理参考图片 (Cref) ---
    cref_url = None
    if args.cref:
        # process_cref_image handles logging and printing errors
        cref_url = process_cref_image(logger, args.cref)
        if not cref_url:
            return 1 # Exit if cref processing failed
        else:
            logger.info(f"使用处理后的 Cref URL: {cref_url}")

    # --- 2. 生成提示词 ---
    prompt_text = None
    concept_key_for_save = None
    if args.concept:
        prompt_text = generate_prompt_text(
            logger, config, args.concept, args.variation, args.style,
            args.aspect, args.quality, args.version, cref_url
        )
        concept_key_for_save = args.concept
    elif args.prompt:
        # Direct prompt handling might need parameter appending logic similar to generate.py
        # For now, assume it includes necessary params or handle_create needs adjustment
        prompt_text = args.prompt
        # TODO: Add parameter appending logic if needed for direct prompts in create
    else:
        logger.error("使用 'create' 命令时，必须提供 --concept 或 --prompt 参数。")
        print("错误：使用 'create' 命令时，必须提供 --concept 或 --prompt 参数。")
        return 1

    if not prompt_text:
        logger.error("无法生成提示词文本。")
        print("错误：无法生成提示词文本。")
        return 1

    # 检查版本与 cref 的兼容性
    if cref_url and ("--v 6" not in prompt_text and "--v 7" not in prompt_text):
        logger.warning("警告：--cref 参数通常与 Midjourney v6 或 v7 一起使用。")
        print("警告：--cref 参数通常与 Midjourney v6 或 v7 一起使用。")

    logger.info(f"生成的提示词: {prompt_text}")
    print(f'''Generated Prompt:
---
{prompt_text}
---''')

    if args.clipboard:
        if PYPERCLIP_AVAILABLE:
            copy_to_clipboard(logger, prompt_text)
            logger.info("提示词已复制到剪贴板。")
        else:
            logger.warning("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
            print("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
    if args.save_prompt:
        # 使用 OUTPUT_DIR 作为输出目录
        filename_base = concept_key_for_save if concept_key_for_save else f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_text_prompt(logger, OUTPUT_DIR, prompt_text, filename_base)

    # --- 3. 检查提示词安全 --- (假设在 utils.api 中)
    # TODO: Verify location of check_prompt if utils.api doesn't exist or lacks it
    logger.info("正在检查提示词安全性...")
    # 确保 prompt_text 是字符串
    prompt_str = prompt_text["prompt"] if isinstance(prompt_text, dict) else prompt_text
    is_safe = check_prompt(logger, prompt_str, api_key)
    if not is_safe:
        # Error message is generic as check_prompt only returns boolean
        error_message = "提示词安全检查未通过或检查过程中发生错误。请检查日志获取详细信息。"
        logger.error(error_message)
        print(f"错误：{error_message}")
        return 1
    logger.info("提示词安全检查通过。")

    # --- 4. 提交任务到 API ---
    # 确保我们使用正确的提示词字符串
    prompt_str = prompt_text["prompt"] if isinstance(prompt_text, dict) else prompt_text
    prompt_data = {"prompt": prompt_str, "mode": args.mode}
    logger.info(f"准备提交任务到 TTAPI (模式: {args.mode})...")
    print(f"正在提交任务 (模式: {args.mode})...")

    # Use the corrected function name call_imagine_api
    # 注意：我们不需要再次传递 cref_url，因为它已经包含在 prompt_text 中了
    submit_result = call_imagine_api(
        logger, prompt_data, api_key,
        hook_url=args.hook_url,
        notify_id=args.notify_id
    )

    if submit_result:
        job_id = submit_result
        logger.info(f"任务提交成功，Job ID: {job_id}")
        job_id_for_save = job_id
        prompt_text_for_save = prompt_text
        seed_for_save = None # Seed is unknown until task completes

        # --- 5. 处理结果 (轮询或 Webhook) ---
        if not args.hook_url:
            logger.info("未提供 Webhook URL，将开始轮询结果...")
            print("Polling for result...")
            # Use the corrected function name poll_for_result
            final_result = poll_for_result(logger, job_id, api_key)

            if final_result and (final_result.get("image_url") or final_result.get("cdnImage")):
                image_url = final_result.get("image_url") or final_result.get("cdnImage")
                logger.info(f"任务完成，图像 URL: {image_url}")

                # --- 6. 下载并保存结果 ---
                download_success, saved_path, image_seed = download_and_save_image(
                    logger, image_url, job_id, prompt_text_for_save, concept_key_for_save,
                    args.variation, args.style, None, # original_job_id
                    None, # action_code
                    final_result.get("components"),
                    final_result.get("seed")
                )
                if download_success:
                    seed_for_save = image_seed # Use seed from download if available
                    save_image_metadata(
                        logger, final_result.get("image_id", str(uuid.uuid4())),
                        job_id_for_save, os.path.basename(saved_path), saved_path,
                        image_url, prompt_text_for_save, concept_key_for_save,
                        args.variation, args.style,
                        final_result.get("components"), seed_for_save, None # original_job_id
                    )
                    logger.info(f"图像和元数据已保存: {saved_path}")
                    print(f"图像和元数据已保存: {saved_path}")
                    return 0
                else:
                    logger.error("图像下载或保存失败。")
                    print("错误：图像下载或保存失败。")
                    return 1
            else:
                status = final_result.get('status') if final_result else 'N/A'
                error_msg = f"轮询任务结果失败或未获取到图像 URL。最后状态: {status}"
                logger.error(error_msg)
                print(f"错误：{error_msg}")
                if job_id_for_save: # Save basic metadata even on failure
                     save_image_metadata(
                          logger, None, job_id_for_save, None, None, None,
                          prompt_text_for_save, concept_key_for_save, args.variation, args.style,
                          final_result, seed_for_save, None
                     )
                     logger.info(f"已保存任务 {job_id_for_save} 的基本元数据（无图像）。")
                return 1
        else: # Webhook provided
            logger.info("提供了 Webhook URL，任务将在后台处理。")
            print("提供了 Webhook URL，任务将在后台处理。")
            # Save initial metadata
            save_image_metadata(
                logger, None, job_id_for_save, None, None, None,
                prompt_text_for_save, concept_key_for_save, args.variation, args.style,
                submit_result, # Save job_id or initial result?
                seed_for_save, None
            )
            logger.info(f"已保存任务 {job_id_for_save} 的初始元数据（无图像）。")
            return 0
    else: # Submit failed
        error_msg = "任务提交失败 (API 调用未返回 Job ID)"
        logger.error(error_msg)
        print(f"错误：{error_msg}")
        return 1
