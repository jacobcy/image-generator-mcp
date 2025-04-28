# -*- coding: utf-8 -*-
import logging
import os
import uuid
from typing import Optional

# 从 utils 导入必要的函数 - 使用统一的元数据管理模块
from ..utils.metadata_manager import find_initial_job_info, save_image_metadata
# download_and_save_image now handles saving metadata via metadata_manager
from ..utils.image_handler import download_and_save_image
from ..utils.api import normalize_api_response
from ..utils.api_client import poll_for_result, call_action_api
from ..utils.filesystem_utils import write_last_job_id, write_last_succeed_job_id, read_last_job_id, read_last_succeed_job_id
from ..utils.image_metadata import load_all_metadata, _build_metadata_index
from ..utils.metadata_manager import _generate_expected_filename

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

from typing import Optional
def handle_action(args, logger, api_key) -> int:
    """处理 'action' 命令，对现有任务执行操作。"""
    # Access parameters from the args object
    action_code = args.action_code
    identifier = args.identifier
    last_job = args.last_job
    last_succeed = args.last_succeed
    hook_url = args.hook_url
    wait = args.wait
    mode = args.mode
    # api_key is passed directly, not in args
    
    # logger is passed directly
    global logger_in_func # Avoid shadowing, use a different name or rely on passed logger
    logger_in_func = logger 
    logger_in_func.info(f"开始处理 'action' 命令: action='{action_code}', identifier={identifier}, last_job={last_job}, last_succeed={last_succeed}, wait={wait}, mode={mode}")

    # 导入允许的 action_code 列表 - OK to import here
    from ..cli import ACTION_CHOICES, ACTION_DESCRIPTIONS

    # 验证 action_code 是否在允许的列表中 (Use the unpacked action_code)
    if action_code not in ACTION_CHOICES:
        logger_in_func.error(f"错误的 action code: '{action_code}'。请使用 'action --list' 查看所有可用的操作代码。")
        print(f"错误: '{action_code}' 不是有效的操作代码。")

        # 尝试找到相似的 action_code 作为建议 (Use the unpacked action_code)
        import difflib
        close_matches = difflib.get_close_matches(action_code, ACTION_CHOICES, n=3, cutoff=0.6)
        if close_matches:
            suggestions = ', '.join([f"'{match}' ({ACTION_DESCRIPTIONS.get(match, '无描述')})" for match in close_matches])
            print(f"您是否想要使用以下操作代码之一? {suggestions}")

        print("使用 'crc action --list' 查看所有可用的操作代码。")
        return 1

    # --- Determine the raw identifier --- #
    raw_identifier = None
    source_description = ""
    # Use unpacked variables from args
    if identifier:
        raw_identifier = identifier
        source_description = "提供的标识符"
        logger_in_func.info(f"使用 {source_description}: {raw_identifier}")
    elif last_succeed:
        source_description = "上一个成功任务 ID"
        logger_in_func.info(f"使用 {source_description}，尝试读取 last_succeed.json...")
        raw_identifier = read_last_succeed_job_id(logger_in_func)
        if not raw_identifier:
            logger_in_func.error(f"错误：无法读取 {source_description} (last_succeed.json)。")
            print(f"错误：找不到上次成功的任务 ID。")
            return 1
        logger_in_func.info(f"获取到 {source_description}: {raw_identifier}")
    else: # Default or last_job
        source_description = "上一个提交任务 ID"
        logger_in_func.info(f"未提供标识符或 --last-succeed，使用 {source_description}，尝试读取 last_job.json...")
        raw_identifier = read_last_job_id(logger_in_func)
        if not raw_identifier:
            logger_in_func.error(f"错误：无法读取 {source_description} (last_job.json)。")
            print(f"错误：找不到上次提交的任务 ID。请提供标识符或使用 --last-succeed。")
            return 1
        logger_in_func.info(f"获取到 {source_description}: {raw_identifier}")

    # --- Resolve Job ID from the raw identifier --- #
    original_job_id = None
    original_job_info = None # Store original info for later use if waiting

    if is_likely_job_id(raw_identifier): # Use the resolved raw_identifier
        logger_in_func.info(f"来自 '{source_description}' 的标识符 '{raw_identifier}' 看起来像 Job ID，将直接使用。")
        original_job_id = raw_identifier
        if wait:
            logger_in_func.info("--wait=True，尝试查找原始任务信息以便后续记录元数据...")
            original_job_info = find_initial_job_info(logger_in_func, original_job_id)
            if not original_job_info:
                logger_in_func.warning(f"(Wait Mode) 无法在本地找到原始 Job ID '{original_job_id}' 的元数据，后续保存的元数据信息可能不完整。")
    else:
        logger_in_func.info(f"来自 '{source_description}' 的标识符 '{raw_identifier}' 不像 Job ID，将尝试在元数据中查找以获取 Job ID...")
        original_job_info = find_initial_job_info(logger_in_func, raw_identifier)
        if not original_job_info or not original_job_info.get('job_id'):
            logger_in_func.error(f"无法根据来自 '{source_description}' 的标识符 '{raw_identifier}' 找到唯一的有效任务或其 Job ID。")
            print(f"错误：无法找到标识符 '{raw_identifier}' 对应的任务。请使用 'list-tasks' 查看或提供有效的 Job ID。")
            return 1
        original_job_id = original_job_info.get('job_id')
        logger_in_func.info(f"通过元数据查找，解析得到的原始任务 Job ID: {original_job_id}")

    # --- Final check for Job ID --- #
    if not original_job_id:
        # This case should only be reachable through complex errors now
        logger_in_func.error("未能确定要操作的 Job ID。")
        print("错误：未能确定要操作的任务 ID。")
        return 1

    # --- Call Action API --- #
    logger_in_func.info(f"准备调用 Action API: action={action_code}, job_id={original_job_id}, mode={mode}")
    new_job_id = call_action_api(
        logger=logger_in_func,
        api_key=api_key, # Use the directly passed api_key
        job_id=original_job_id, # Correct keyword for utils/api.py function
        action_code=action_code, # Use unpacked action_code
        hook_url=hook_url, # Use unpacked hook_url
        mode=mode # Use unpacked mode
    )

    if new_job_id:
        logger_in_func.info(f"Action API 调用成功，返回新的 Job ID: {new_job_id}")
        print(f"操作 '{action_code}' 已成功提交，新的任务 ID: {new_job_id}")
        # Update last job ID immediately after successful submission
        write_last_job_id(logger_in_func, new_job_id)

        # --- Wait, Poll, Download, and Save Metadata (if requested and no webhook) --- #
        if wait and not hook_url:
            logger_in_func.info(f"--wait 标志已设置且无 webhook，开始等待并轮询新任务 {new_job_id} 的结果...")
            print(f"等待并轮询任务 {new_job_id} 的结果...")
            poll_response = poll_for_result(logger_in_func, new_job_id, api_key)

            if poll_response:
                final_status, api_data = poll_response # Unpack the tuple

                # Check if polling was successful and got data
                if final_status == "SUCCESS" and isinstance(api_data, dict):
                    # Get URL from api_data (actual data dict)
                    image_url_key = 'url' if 'url' in api_data else 'cdnImage' # Prefer url after normalization potentially
                    image_url = api_data.get(image_url_key)

                    if image_url:
                        logger_in_func.info(f"任务 {new_job_id} 完成，图像 URL: {image_url}")

                        # 标准化API结果，以便保存 (use api_data)
                        normalized_result = normalize_api_response(logger_in_func, api_data)
                        normalized_result['job_id'] = new_job_id # Ensure job_id is in the dict
                        normalized_result['original_job_id'] = original_job_id # Ensure original job ID is recorded
                        normalized_result['action_code'] = action_code # Ensure action code is recorded

                        # --- 生成期望的文件名 --- #
                        try:
                            all_tasks = load_all_metadata(logger_in_func)
                            all_tasks_index = _build_metadata_index(all_tasks)
                            expected_filename = _generate_expected_filename(logger_in_func, normalized_result, all_tasks_index)
                        except Exception as e:
                            logger_in_func.error(f"为任务 {new_job_id} 生成期望文件名时出错: {e}，将使用 job_id 作为备用名。")
                            expected_filename = f"action_{new_job_id}.png"
                        # ---------------------- #

                        download_success, saved_path, image_seed = download_and_save_image(
                            logger_in_func,
                            image_url,
                            new_job_id, # Use the NEW job ID
                            normalized_result.get('prompt'),
                            expected_filename, # Pass generated filename
                            normalized_result.get('concept'),
                            normalized_result.get('variations'),
                            normalized_result.get('global_styles'),
                            original_job_id,
                            action_code,
                            None, # components
                            normalized_result.get('seed')
                        )
                        if download_success:
                            logger_in_func.info(f"操作 '{action_code}' 的图像和元数据已保存: {saved_path}")
                            print(f"操作 '{action_code}' 的图像和元数据已保存: {saved_path}")
                            write_last_succeed_job_id(logger_in_func, new_job_id)
                            return 0
                        else:
                            logger_in_func.error(f"操作 '{action_code}' 的图像下载或保存失败 (Job ID: {new_job_id})。")
                            print(f"错误：操作 '{action_code}' 的图像下载或保存失败。")
                            return 1 # Return failure, even though submission was ok
                    else:
                        # SUCCESS status but no image URL in api_data
                        logger_in_func.error(f"轮询操作 '{action_code}' (Job ID: {new_job_id}) 成功，但未获取到图像 URL。")
                        print(f"错误：轮询操作 '{action_code}' 成功，但未获取到图像 URL。")
                        # Save basic metadata anyway
                        normalized_result = normalize_api_response(logger_in_func, api_data or {})
                        save_image_metadata(
                            logger_in_func, None, new_job_id, None, None, None,
                            original_job_info.get("prompt", f"Action: {action_code} on {original_job_id}") if original_job_info else f"Action: {action_code} on {original_job_id}",
                            original_job_info.get("concept") if original_job_info and original_job_info.get("concept") else "action",
                            original_job_info.get("variations", []) if original_job_info else [],
                            original_job_info.get("global_styles", []) if original_job_info else [],
                            None, normalized_result.get("seed"), original_job_id,
                            action_code=action_code,
                            status=f"polling_success_no_url"
                        )
                        return 1 # Return failure
                elif final_status == "FAILED":
                    # Handle FAILED status returned by poll_for_result
                    # api_data here is the full error response from the API client
                    error_message = api_data.get('message', '未知错误') if isinstance(api_data, dict) else '未知错误'
                    logger_in_func.error(f"轮询操作 '{action_code}' (Job ID: {new_job_id}) 失败。API 消息: {error_message}")
                    print(f"错误：轮询操作 '{action_code}' 失败。API 消息: {error_message}")
                    # Save basic metadata for the failed attempt
                    normalized_result = normalize_api_response(logger_in_func, api_data or {})
                    save_image_metadata(
                        logger_in_func, None, new_job_id, None, None, None,
                        original_job_info.get("prompt", f"Action: {action_code} on {original_job_id}") if original_job_info else f"Action: {action_code} on {original_job_id}",
                        original_job_info.get("concept") if original_job_info and original_job_info.get("concept") else "action",
                        original_job_info.get("variations", []) if original_job_info else [],
                        original_job_info.get("global_styles", []) if original_job_info else [],
                        None, normalized_result.get("seed"), original_job_id,
                        action_code=action_code,
                        status=f"polling_failed: {final_status}" # Use final_status
                    )
                    return 1 # Return failure
                else:
                    # Handle unexpected status from poll_for_result (should not happen if API client is correct)
                    logger_in_func.error(f"轮询操作 '{action_code}' (Job ID: {new_job_id}) 返回意外状态: {final_status}")
                    print(f"错误：轮询操作 '{action_code}' 返回意外状态: {final_status}")
                    return 1 # Return failure
            else:
                # Handle poll_for_result returning None (timeout or other poll failure)
                logger_in_func.error(f"轮询操作 '{action_code}' (Job ID: {new_job_id}) 失败或超时。")
                print(f"错误：轮询操作 '{action_code}' 失败或超时。")
                # Save basic metadata for the failed attempt
                save_image_metadata(
                    logger_in_func, None, new_job_id, None, None, None,
                    original_job_info.get("prompt", f"Action: {action_code} on {original_job_id}") if original_job_info else f"Action: {action_code} on {original_job_id}",
                    original_job_info.get("concept") if original_job_info and original_job_info.get("concept") else "action",
                    original_job_info.get("variations", []) if original_job_info else [],
                    original_job_info.get("global_styles", []) if original_job_info else [],
                    None, None, original_job_id, # No seed available
                    action_code=action_code,
                    status="polling_timeout_or_error"
                )
                return 1 # Return failure
        elif not wait and not hook_url:
            # Default behavior: Submission successful, but no wait/poll requested
            logger_in_func.info("操作已提交，未请求等待 (--wait)。")
            # Optionally save basic pending metadata? Similar to webhook case.
            save_image_metadata(
                 logger_in_func, None, new_job_id, None, None, None,
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
            logger_in_func.info(f"提供了 Webhook URL ({hook_url})，任务将在后台处理。")
            save_image_metadata(
                logger_in_func, None, new_job_id, None, None, None,
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
        logger_in_func.error(f"Action API 调用失败或未返回新的 Job ID (原始 Job ID: {original_job_id})。")
        print(f"错误：提交操作 '{action_code}' 失败。请检查日志获取详细信息。")
        return 1 # Failure
