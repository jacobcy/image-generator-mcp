# -*- coding: utf-8 -*-
import logging
import os
import uuid
from typing import Optional

# 从 utils 导入必要的函数 - 使用统一的元数据管理模块
from ..utils.metadata_manager import find_initial_job_info, save_image_metadata
# download_and_save_image now handles saving metadata via metadata_manager
from ..utils.image_handler import download_and_save_image
from ..utils.api import poll_for_result, call_action_api, normalize_api_response
from ..utils.filesystem_utils import write_last_job_id, write_last_succeed_job_id

logger = logging.getLogger(__name__)

def is_likely_job_id(identifier):
    """简单检查标识符是否可能是 UUID 格式的 Job ID。"""
    # Basic check: length 36, contains hyphens
    if isinstance(identifier, str) and len(identifier) == 36 and identifier.count('-') == 4:
        try:
            uuid.UUID(identifier)
            return True
        except ValueError:
            return False
    return False

def handle_action(action_code: str, job_id_or_identifier: str, hook_url: Optional[str], wait: bool, mode: str, logger: logging.Logger, api_key: str) -> int:
    """处理 'action' 命令，对现有任务执行操作。"""
    logger.info(f"开始处理 'action' 命令: action='{action_code}', identifier='{job_id_or_identifier}', wait={wait}, mode={mode}")

    original_job_id = None
    original_job_info = None # Store original info for later use if waiting

    # --- Resolve Job ID --- #
    if is_likely_job_id(job_id_or_identifier):
        logger.info(f"标识符 '{job_id_or_identifier}' 看起来像 Job ID，将直接使用。")
        original_job_id = job_id_or_identifier
        # ONLY try to get original info if wait=True, as it's needed for metadata/download later
        if wait:
            logger.info("--wait=True，尝试查找原始任务信息以便后续记录元数据...")
        original_job_info = find_initial_job_info(logger, original_job_id)
        if not original_job_info:
            logger.warning(f"(Wait Mode) 无法在本地找到原始 Job ID '{original_job_id}' 的元数据，后续保存的元数据信息可能不完整。")
    else:
        # If identifier is not a Job ID, we *always* need to find the info to get the real Job ID
        logger.info(f"标识符 '{job_id_or_identifier}' 不像 Job ID，将尝试在元数据中查找以获取 Job ID...")
        original_job_info = find_initial_job_info(logger, job_id_or_identifier)
        if not original_job_info or not original_job_info.get('job_id'):
            logger.error(f"无法根据标识符 '{job_id_or_identifier}' 找到唯一的有效任务或其 Job ID。")
            print(f"错误：无法找到标识符 '{job_id_or_identifier}' 对应的任务。请使用 'list-tasks' 查看或提供有效的 Job ID。")
            return 1
        original_job_id = original_job_info.get('job_id')
        logger.info(f"通过元数据查找，解析得到的原始任务 Job ID: {original_job_id}")

    # --- Final check for Job ID --- #
    if not original_job_id:
        # This case should only be reachable through complex errors now
        logger.error("未能确定要操作的 Job ID。")
        print("错误：未能确定要操作的任务 ID。")
        return 1

    # --- Call Action API --- #
    logger.info(f"准备调用 Action API: action={action_code}, job_id={original_job_id}, mode={mode}")
    new_job_id = call_action_api(
        logger=logger,
        api_key=api_key,
        job_id=original_job_id, # Correct keyword for utils/api.py function
        action_code=action_code, # Correct keyword for utils/api.py function
        hook_url=hook_url,
        mode=mode # Pass the mode
    )

    if new_job_id:
        logger.info(f"Action API 调用成功，返回新的 Job ID: {new_job_id}")
        print(f"操作 '{action_code}' 已成功提交，新的任务 ID: {new_job_id}")
        # Update last job ID immediately after successful submission
        write_last_job_id(logger, new_job_id)

        # --- Wait, Poll, Download, and Save Metadata (if requested and no webhook) --- #
        if wait and not hook_url:
            logger.info(f"--wait 标志已设置且无 webhook，开始等待并轮询新任务 {new_job_id} 的结果...")
            print(f"等待并轮询任务 {new_job_id} 的结果...")
            final_result = poll_for_result(logger, new_job_id, api_key)

            image_url_key = 'image_url' if 'image_url' in (final_result or {}) else 'cdnImage'
            if final_result and final_result.get(image_url_key):
                image_url = final_result.get(image_url_key)
                logger.info(f"任务 {new_job_id} 完成，图像 URL: {image_url}")
                
                # 标准化API结果，以便保存
                normalized_result = normalize_api_response(logger, final_result)

                # Prepare info needed for download/metadata from original job
                prompt_text_for_save = original_job_info.get("prompt", f"Action: {action_code} on {original_job_id}") if original_job_info else f"Action: {action_code} on {original_job_id}"
                # concept_key_for_save = original_job_info.get("concept") if original_job_info and original_job_info.get("concept") else "unknown"
                # 传递原始 concept 给 download_and_save_image 以便生成正确文件名
                original_concept_for_naming = original_job_info.get("concept") if original_job_info else None
                # 但保存元数据时，action 任务本身的 concept 仍然是 action
                concept_key_for_metadata = "action" 
                
                logger.info(f"原始 Concept (用于命名): {original_concept_for_naming}")
                variations_keys = original_job_info.get("variations", []) if original_job_info else []
                styles_keys = original_job_info.get("global_styles", []) if original_job_info else []

                download_success, saved_path, image_seed = download_and_save_image(
                    logger,
                    image_url,
                    new_job_id, # Use the NEW job ID
                    prompt_text_for_save, # Use original prompt or derived
                    concept=concept_key_for_metadata, # Save 'action' as concept in metadata
                    variations=variations_keys, # Use original variations
                    styles=styles_keys, # Use original styles
                    original_job_id=original_job_id, # Link to the original job ID that this action was performed on
                    action_code=action_code, # Store the action performed
                    seed=normalized_result.get("seed"), # Seed from normalized result
                    original_concept=original_concept_for_naming, # Pass original concept for naming
                    prefix="" # No prefix needed here
                )
                if download_success:
                    # Metadata is now saved inside download_and_save_image
                    logger.info(f"操作 '{action_code}' 的图像和元数据已保存: {saved_path}")
                    print(f"操作 '{action_code}' 的图像和元数据已保存: {saved_path}")
                    # --- Update Last Succeed Job ID --- #
                    write_last_succeed_job_id(logger, new_job_id)
                    # Last job ID already written upon submission, return success
                    return 0
                else:
                    logger.error(f"操作 '{action_code}' 的图像下载或保存失败 (Job ID: {new_job_id})。")
                    print(f"错误：操作 '{action_code}' 的图像下载或保存失败。")
                    return 1 # Return failure, even though submission was ok
            else:
                status = final_result.get('status') if final_result else 'N/A'
                logger.error(f"轮询操作 '{action_code}' (Job ID: {new_job_id}) 结果失败或未获取到图像 URL。最后状态: {status}")
                print(f"错误：轮询操作 '{action_code}' 结果失败或未获取到图像 URL。最后状态: {status}")
                # 标准化结果用于保存基本元数据
                normalized_result = normalize_api_response(logger, final_result or {})
                # Still save basic metadata to record the action attempt
                save_image_metadata(
                    logger, None, new_job_id, None, None, None,
                    original_job_info.get("prompt", f"Action: {action_code} on {original_job_id}") if original_job_info else f"Action: {action_code} on {original_job_id}",
                    original_job_info.get("concept") if original_job_info and original_job_info.get("concept") else "action", # 继承原始概念，如果没有则使用 "action"
                    original_job_info.get("variations", []) if original_job_info else [],
                    original_job_info.get("global_styles", []) if original_job_info else [],
                    None, # Components removed
                    normalized_result.get("seed"), # Seed from normalized result
                    original_job_id, # Link to original job
                    action_code=action_code, # 显式添加action_code
                    status=f"polling_failed: {status}" # Record poll status
                )
                return 1 # Return failure
        elif not wait and not hook_url:
            # Default behavior: Submission successful, but no wait/poll requested
            logger.info("操作已提交，未请求等待 (--wait)。")
            # Optionally save basic pending metadata? Similar to webhook case.
            save_image_metadata(
                 logger, None, new_job_id, None, None, None,
                 original_job_info.get("prompt", f"Action: {action_code} on {original_job_id}") if original_job_info else f"Action: {action_code} on {original_job_id}",
                 original_job_info.get("concept") if original_job_info and original_job_info.get("concept") else "action", # 继承原始概念，如果没有则使用 "action"
                 original_job_info.get("variations", []) if original_job_info else [],
                 original_job_info.get("global_styles", []) if original_job_info else [],
                 {"status": "submitted_no_wait"}, None,
                 original_job_id,
                 action_code=action_code, # 显式添加action_code
                 status="submitted_no_wait"
            )
            return 0 # Return success for submission
        elif hook_url:
            # Webhook provided, save basic metadata
            logger.info(f"提供了 Webhook URL ({hook_url})，任务将在后台处理。")
            save_image_metadata(
                logger, None, new_job_id, None, None, None,
                 original_job_info.get("prompt", f"Action: {action_code} on {original_job_id}") if original_job_info else f"Action: {action_code} on {original_job_id}",
                 original_job_info.get("concept") if original_job_info and original_job_info.get("concept") else "action", # 继承原始概念，如果没有则使用 "action"
                 original_job_info.get("variations", []) if original_job_info else [],
                 original_job_info.get("global_styles", []) if original_job_info else [],
                 {"status": "submitted_webhook"}, None,
                 original_job_id,
                 action_code=action_code, # 显式添加action_code
                 status="submitted_webhook"
            )
            return 0 # Return success for submission

    else: # API call failed
        logger.error(f"Action API 调用失败或未返回新的 Job ID (原始 Job ID: {original_job_id})。")
        print(f"错误：提交操作 '{action_code}' 失败。请检查日志获取详细信息。")
        return 1 # Failure
