# -*- coding: utf-8 -*-
import os
import uuid
import logging
from typing import Optional

# 从 utils 导入必要的函数 - 使用统一的元数据管理模块
from ..utils.metadata_manager import find_initial_job_info, save_image_metadata
# download_and_save_image now handles saving metadata via metadata_manager
from ..utils.image_handler import download_and_save_image
from ..utils.image_uploader import process_cref_image
from ..utils.api import check_prompt, call_imagine_api, poll_for_result, normalize_api_response
from ..utils.filesystem_utils import write_last_job_id, write_last_succeed_job_id
from ..utils.image_metadata import load_all_metadata, _build_metadata_index
from ..utils.metadata_manager import _generate_expected_filename

logger = logging.getLogger(__name__)

def handle_recreate(args, config, logger, api_key):
    """处理 'recreate' 命令。"""
    logger.info(f"正在查找任务 '{args.identifier}' 的原始信息...")
    original_job_info = find_initial_job_info(logger, args.identifier)

    if not original_job_info:
        error_msg = f"在本地元数据中找不到任务 '{args.identifier}' 的原始信息。"
        logger.error(error_msg)
        print(f"错误：{error_msg}") # Keep user feedback
        return 1

    original_prompt = original_job_info.get("prompt")
    original_seed = original_job_info.get("seed")
    original_concept = original_job_info.get("concept")
    original_job_id = original_job_info.get("job_id") # Needed for linking

    if not original_prompt or original_seed is None:
        error_msg = f"任务 '{args.identifier}' 的元数据缺少 Prompt 或 Seed。"
        logger.error(error_msg)
        print(f"错误：{error_msg}") # Keep user feedback
        return 1

    recreate_prompt = f"{original_prompt} --seed {original_seed}"
    print(f'''Recreating with Prompt:
---
{recreate_prompt}
---''') # Keep user feedback

    # Handle cref if provided for recreate
    cref_url = None
    if args.cref:
        # Construct the warning message separately
        if "--v 6" not in original_prompt:
             warning_msg = "警告：--cref 参数通常与 Midjourney v6 一起使用。"
             logger.warning(warning_msg)
             print(warning_msg) # Keep user feedback
        cref_url = process_cref_image(logger, args.cref)
        if not cref_url:
            # Error already logged/printed in process_cref_image
            return 1
        else:
            logger.info(f"使用处理后的 Cref URL: {cref_url}")

    # Check prompt safety
    is_safe = check_prompt(logger, recreate_prompt, api_key)
    if not is_safe:
        error_message = "重新生成提示词安全检查未通过或检查过程中发生错误。请检查日志获取详细信息。"
        logger.error(error_message)
        print(f"错误：{error_message}") # Keep user feedback
        return 1
    logger.info("重新生成提示词安全检查通过。")

    # Call Imagine API (default to relax mode for recreate)
    print("正在提交重新生成任务...") # Keep user feedback
    submit_result = call_imagine_api(
        logger,
        api_key,
        {"prompt": recreate_prompt, "mode": "relax"}, # Default mode
        hook_url=args.hook_url,
        cref_url=cref_url
    )

    if submit_result:
        job_id = submit_result
        logger.info(f"重新生成任务提交成功，新 Job ID: {job_id}")
        job_id_for_save = job_id
        prompt_text_for_save = recreate_prompt
        seed_for_save = original_seed
        concept_key_for_save = original_concept

        if not args.hook_url:
            logger.info("未提供 Webhook URL，将开始轮询结果...")
            print("Polling for recreate result...") # Keep user feedback
            final_result = poll_for_result(logger, job_id, api_key)
            if final_result and final_result.get("image_url"): # Use image_url
                logger.info(f"重新生成任务完成，图像 URL: {final_result['image_url']}")
                # 标准化结果用于保存和命名
                normalized_result = normalize_api_response(logger, final_result)
                normalized_result['job_id'] = job_id # Ensure job_id is in the dict
                normalized_result['original_job_id'] = original_job_id # Record original job for tracing
                normalized_result['prefix'] = "recreate_" # <--- Add prefix for naming
                
                # --- 生成期望的文件名 --- #
                try:
                    # 加载元数据以构建索引
                    all_tasks = load_all_metadata(logger)
                    all_tasks_index = _build_metadata_index(all_tasks)
                    # 传递 normalized_result (包含 prefix)
                    expected_filename = _generate_expected_filename(logger, normalized_result, all_tasks_index)
                except Exception as e:
                    logger.error(f"为任务 {job_id} 生成期望文件名时出错: {e}，将使用 job_id 作为备用名。")
                    expected_filename = f"recreate_{job_id}.png"
                # ---------------------- #

                image_url = normalized_result.get('url')
                if image_url:
                    logger.info("下载图像...")
                    download_success, saved_path, image_seed = download_and_save_image(
                        logger,
                        image_url,
                        job_id, # New job ID
                        normalized_result.get('prompt'),
                        expected_filename, # <--- Pass generated filename
                        normalized_result.get('concept'),
                        normalized_result.get('variations'),
                        normalized_result.get('global_styles'),
                        original_job_id, # Pass original job ID
                        None, # action_code is None for recreate
                        None, # components
                        normalized_result.get('seed')
                        # original_concept (handled by generator)
                        # prefix (handled by generator)
                    )

                    if download_success:
                        final_seed = image_seed if image_seed is not None else seed_for_save
                        save_image_metadata(
                            logger,
                            final_result.get("image_id", str(uuid.uuid4())),
                            job_id_for_save,
                            os.path.basename(saved_path),
                            saved_path,
                            final_result["image_url"],
                            prompt_text_for_save,
                            concept_key_for_save,
                            None, # variations
                            None, # styles
                            final_result.get("components"),
                            final_seed,
                            original_job_id # Link to original
                        )
                        logger.info(f"重新生成的图像和元数据已保存: {saved_path}")
                        print(f"重新生成的图像和元数据已保存: {saved_path}") # Keep user feedback
                        write_last_succeed_job_id(logger, job_id)
                        return 0
                    else:
                        # Error should be logged by download_and_save_image
                        # print("错误：重新生成的图像下载或保存失败。") # Redundant if logged in util
                        return 1
            else:
                status = final_result.get('status') if final_result else 'N/A'
                # Construct the message string separately
                error_msg = f"轮询重新生成任务结果失败或未获取到图像 URL。最后状态: {status}"
                logger.error(error_msg)
                print(f"错误：{error_msg}") # Keep user feedback
                if job_id_for_save:
                     save_image_metadata(
                          logger,
                          None, # image_id
                          job_id_for_save,
                          None, # filename
                          None, # filepath
                          None, # url
                          prompt_text_for_save,
                          concept_key_for_save,
                          None, # variations
                          None, # styles
                          final_result, # components (or full result? check usage)
                          seed_for_save,
                          original_job_id # Link to original
                     )
                     logger.info(f"已保存重新生成任务 {job_id_for_save} 的基本元数据（无图像）。")
                     write_last_job_id(logger, job_id)
                return 1
        else: # Webhook provided
            logger.info("提供了 Webhook URL，重新生成任务将在后台处理。")
            save_image_metadata(
                logger,
                None, # image_id
                job_id_for_save,
                None, # filename
                None, # filepath
                None, # url
                prompt_text_for_save,
                concept_key_for_save,
                None, # variations
                None, # styles
                submit_result, # Save job_id as initial components/result?
                seed_for_save,
                original_job_id # Link to original
            )
            logger.info(f"已保存重新生成任务 {job_id_for_save} 的初始元数据（无图像）。")
            write_last_job_id(logger, job_id)
            return 0
    else: # Submit failed
        error_msg = "重新生成任务提交失败 (API 调用未返回 Job ID)"
        logger.error(error_msg)
        print(f"错误：{error_msg}") # Keep user feedback
        return 1
