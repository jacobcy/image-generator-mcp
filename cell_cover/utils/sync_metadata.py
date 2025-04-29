# 请替换 cell_cover/utils/sync_metadata.py 中的 sync_tasks 函数

import logging
from typing import List, Dict, Any, Optional, Tuple
import os
from datetime import datetime
import uuid # 需要导入 uuid 用于备用文件名
from .normalize_metadata import _generate_expected_filename

from .image_metadata import (
    _load_metadata_file, _save_metadata_file,
    update_job_metadata, upsert_job_metadata,
    load_all_metadata,
    _build_metadata_index,
    trace_job_history,
    remove_job_metadata
)
from .image_handler import download_and_save_image
from .metadata_manager import find_initial_job_info

# 区分 api.py (包含 normalize_api_response) 和 api_client.py (包含实际 API 调用)
from .api import normalize_api_response
from .api_client import poll_for_result
# from .api import poll_for_result, normalize_api_response # 旧的导入方式

from .config import get_api_key
from .filesystem_utils import (
    # META_DIR, METADATA_FILENAME, IMAGE_DIR, # Removed
    ensure_directories, write_last_succeed_job_id,
    sanitize_filename
)
from .file_handler import MAX_FILENAME_LENGTH

def sync_tasks(
    logger: logging.Logger,
    api_key: str,
    metadata_dir: str, # Added
    output_dir: str,   # Added
    state_dir: str,    # Added (for write_last_succeed_job_id)
    all_tasks: Optional[List[Dict[str, Any]]] = None,
    silent: bool = False
) -> Tuple[int, int, int]:
    """同步本地任务状态和源任务信息。

    Args:
        logger: 日志记录器
        api_key: API密钥
        metadata_dir: 元数据文件所在目录 (e.g., /path/to/.crc/metadata)
        output_dir: 图片输出目录 (e.g., /path/to/.crc/output)
        state_dir: 状态文件目录 (e.g., /path/to/.crc/state)
        all_tasks: 可选的预加载任务列表，如果未提供则会从元数据文件加载
        silent: 是否静默运行（不输出彩色终端信息）

    Returns:
        tuple: (成功同步数, 跳过数, 失败数)
    """
    # 定义元数据文件名
    metadata_filename = os.path.join(metadata_dir, "images_metadata.json")

    # 如果未提供任务列表，从元数据加载
    if all_tasks is None:
        # Pass metadata_dir to load_all_metadata (assuming it's modified)
        all_tasks = load_all_metadata(logger, metadata_dir)

    if not all_tasks:
        logger.warning("没有任务可同步")
        return (0, 0, 0)

    # 使用 logger 替代 print_status
    logger.info("开始同步任务状态...")

    # 统计变量
    success_count = 0
    skipped_count = 0
    failed_count = 0

    # 定义需要主动查询 API 的状态
    api_check_trigger_statuses = {
        'pending', 'submitted', 'submitted_webhook', 'pending_queue', 'on_queue',
        'error', 'sync_error', 'polling_failed', 'unknown',
        None, '' # Also check tasks with missing or empty status
    }

    # 1. 找出需要检查 API 或文件状态的任务
    tasks_to_process = []

    for task in all_tasks:
        status = task.get('status')
        filepath = task.get('filepath')
        job_id = task.get('job_id')
        if not job_id:
            skipped_count += 1
            continue # Skip tasks without job_id

        # 状态触发 API 检查
        if status in api_check_trigger_statuses:
            tasks_to_process.append(task)
        # 已完成但文件丢失，需要检查 API 并尝试下载
        elif status == 'completed' and (not filepath or not os.path.exists(filepath)):
             logger.info(f"任务 {job_id[:6]} 状态为 completed 但文件丢失，加入处理队列。")
             task['reason_to_process'] = 'completed_file_missing' # Mark reason
             tasks_to_process.append(task)
        # 明确跳过 file_missing (我们假设它之前已确认失败下载)
        elif status == 'file_missing':
             logger.debug(f"任务 {job_id[:6]} 状态为 file_missing，跳过本次同步检查。")
             skipped_count += 1
        # 其他状态 (如 download_failed, url_outdated, rename_failed) 也暂时跳过，除非明确要重新检查
        else:
            skipped_count += 1

    # 处理需要检查状态或文件的任务
    if tasks_to_process:
        logger.info(f"找到 {len(tasks_to_process)} 个任务需要检查 API 状态或文件。")

        for i, task in enumerate(tasks_to_process):
            job_id = task.get('job_id') # Already checked not None

            logger.info(f"[{i+1}/{len(tasks_to_process)}] 处理任务 {job_id[:6]}... (当前状态: {task.get('status', 'None')}) ")

            try:
                poll_response = poll_for_result(logger, job_id, api_key) # Renamed variable

                if poll_response:
                    final_status, api_data = poll_response # Unpack tuple
                    logger.debug(f"任务 {job_id} 的 API 轮询结果: status={final_status}, data={api_data!r}") # Log unpacked result

                    # 使用标准化函数处理 API 响应数据 (api_data)
                    normalized_result = normalize_api_response(logger, api_data if isinstance(api_data, dict) else {}) # Handle non-dict api_data
                    if not normalized_result and final_status != 'FAILED': # Don't fail just because FAILED response couldn't normalize fully
                        logger.warning(f"规范化来自 API 的任务 {job_id} 的数据失败。")
                        # Pass metadata_dir (assuming modified)
                        update_job_metadata(logger, job_id, {'status': 'sync_error'}, metadata_dir)
                        failed_count += 1
                        continue

                    # 检查标准化后的数据是否包含 components 字段，如果有，将其移除 (already done in normalize)
                    # if "components" in normalized_result:
                    #    logger.debug(f"从标准化结果中移除 components 字段: {normalized_result['components']}")
                    #    del normalized_result["components"]

                    normalized_result['job_id'] = job_id # Ensure job_id
                    # Use the reliable final_status from the tuple
                    api_status_from_poll = final_status

                    # === 核心处理逻辑 ===
                    if api_status_from_poll == 'FAILED':
                        error_message = api_data.get('message', '未知原因') if isinstance(api_data, dict) else '未知原因'
                        logger.error(f"任务 {job_id} 在 API 端失败 (原因: {error_message})，将从本地元数据中移除。")
                        # Pass metadata_dir (assuming modified)
                        if remove_job_metadata(logger, job_id, metadata_dir):
                            logger.info(f"已从元数据中删除失败的任务 {job_id}")
                            if not silent: print(f"已从元数据中删除失败的任务 {job_id}")
                        else:
                            logger.warning(f"无法从元数据中删除失败的任务 {job_id}")
                            if not silent: print(f"警告：无法从元数据中删除失败的任务 {job_id}")
                        failed_count += 1
                        continue # 处理下一个任务

                    elif api_status_from_poll == 'SUCCESS':
                        # 更新元数据为 API 的最新状态 (use normalized_result)
                        # Pass metadata_dir (assuming modified)
                        upsert_job_metadata(logger, job_id, normalized_result, metadata_dir)

                        image_url = normalized_result.get('url')
                        if image_url:
                            logger.info(f"任务 {job_id} API状态为 SUCCESS，尝试下载图像...")
                            # --- 生成期望的文件名 --- #
                            try:
                                # Pass metadata_dir (assuming modified)
                                current_metadata_for_naming = load_all_metadata(logger, metadata_dir)
                                all_tasks_index = _build_metadata_index(current_metadata_for_naming)
                                # Assuming _generate_expected_filename is also modified if needed
                                expected_filename = _generate_expected_filename(logger, normalized_result, all_tasks_index)
                            except Exception as e:
                                logger.error(f"为任务 {job_id} 生成期望文件名时出错: {e}，将使用 job_id 作为备用名。")
                                expected_filename = f"{job_id}.png"
                            # ---------------------- #

                            # Pass output_dir to download_and_save_image (assuming modified)
                            download_success, download_result_info, _ = download_and_save_image(
                                logger,
                                image_url,
                                job_id,
                                output_dir, # Pass output_dir
                                expected_filename, # Pass expected filename (without dir)
                                # --- Metadata needed for potential saving --- #
                                normalized_result.get('prompt') or "",
                                normalized_result.get('concept'),
                                normalized_result.get('variations'),
                                normalized_result.get('global_styles'),
                                normalized_result.get('original_job_id'),
                                normalized_result.get('action_code'),
                                None, # components
                                normalized_result.get('seed')
                            )
                            if download_success:
                                filepath = download_result_info # Should be the full path from download_and_save_image
                                logger.info(f"任务 {job_id}: 图像下载成功，保存至 {filepath}")
                                filename = os.path.basename(filepath) if filepath else None
                                # Update status to completed *after* successful download
                                # Pass metadata_dir (assuming modified)
                                update_job_metadata(logger, job_id, {'status': 'completed', 'filepath': filepath, 'filename': filename}, metadata_dir)
                                # Write last succeed job ID using state_dir
                                write_last_succeed_job_id(logger, job_id, state_dir)
                                success_count += 1
                            else:
                                logger.warning(f"任务 {job_id}: 图像下载失败 ({download_result_info})。状态标记为 'file_missing'。")
                                # Pass metadata_dir (assuming modified)
                                update_job_metadata(logger, job_id, {'status': 'file_missing', 'filepath': None, 'filename': None}, metadata_dir)
                                failed_count += 1
                        else:
                             # API SUCCESS 但无 URL
                            logger.warning(f"任务 {job_id}: API状态为 SUCCESS 但没有图像 URL。状态标记为 'completed_no_url'。")
                            # Pass metadata_dir (assuming modified)
                            update_job_metadata(logger, job_id, {'status': 'completed_no_url', 'filepath': None, 'filename': None}, metadata_dir)
                            skipped_count += 1

                    else: # API 返回其他状态 (pending, submitted, etc.)
                        # Use the status directly from the poll response tuple
                        logger.info(f"任务 {job_id}: API状态为 {api_status_from_poll}，更新本地状态。")
                        # Pass metadata_dir (assuming modified)
                        update_job_metadata(logger, job_id, {'status': api_status_from_poll}, metadata_dir)
                        skipped_count += 1 # 算作跳过，因为没有最终成功

                else:
                    # poll_for_result returned None (timeout or other poll failure)
                    logger.warning(f"任务 {job_id}: API 查询失败或超时。标记为 polling_failed。")
                    # Pass metadata_dir (assuming modified)
                    update_job_metadata(logger, job_id, {'status': 'polling_failed'}, metadata_dir)
                    skipped_count += 1 # Count as skipped as no final state determined

            except Exception as e:
                logger.exception(f"处理任务 {job_id} 时发生意外错误: {str(e)}")
                try:
                    # Pass metadata_dir (assuming modified)
                    update_job_metadata(logger, job_id, {'status': 'sync_error'}, metadata_dir)
                except Exception as update_err:
                    logger.error(f"尝试将任务 {job_id} 状态更新为 sync_error 时失败: {update_err}")
                failed_count += 1
    else:
        logger.info("没有需要检查 API 状态或文件的任务。")

    # 再次加载 all_tasks 以获取最新状态，用于处理源任务
    all_tasks = load_all_metadata(logger)
    if all_tasks is None: # Check if loading failed
        logger.error("无法重新加载元数据以处理源任务，跳过源任务同步。")
    else:
        task_id_index = _build_metadata_index(all_tasks)
        missing_original_ids = set()
        tasks_referencing_missing = []

        for task in all_tasks:
            original_job_id = task.get('original_job_id')
            if original_job_id and original_job_id not in task_id_index:
                # Skip potentially invalid IDs early
                if not (len(original_job_id) == 36 and original_job_id.count('-') == 4):
                     job_id_prefix = task.get('job_id', '')[:6] or 'unknown'
                     logger.warning(f"跳过任务 {job_id_prefix} 中无效的 original_job_id: '{original_job_id}'，格式不符合预期。")
                     continue

                if original_job_id not in missing_original_ids:
                    missing_original_ids.add(original_job_id)
                    tasks_referencing_missing.append(original_job_id) # Store the ID to fetch

        if tasks_referencing_missing:
            logger.warning(f"找到 {len(tasks_referencing_missing)} 个未知的源任务 ID，尝试同步...")

            for i, original_job_id in enumerate(tasks_referencing_missing):
                logger.info(f"[{i+1}/{len(tasks_referencing_missing)}] 同步源任务 {original_job_id[:6]}...")

                try:
                    poll_response = poll_for_result(logger, original_job_id, api_key) # Call poll

                    if poll_response:
                        final_status, api_data = poll_response # Unpack
                        logger.debug(f"源任务 {original_job_id} 的 API 轮询结果: status={final_status}, data={api_data!r}")

                        # Normalize API data
                        normalized_result = normalize_api_response(logger, api_data if isinstance(api_data, dict) else {})
                        if not normalized_result and final_status != 'FAILED':
                            logger.warning(f"无法规范化来自 API 的源任务 {original_job_id} 的数据。")
                            failed_count += 1
                            continue

                        normalized_result['job_id'] = original_job_id # Ensure job_id
                        api_status_from_poll = final_status

                        if api_status_from_poll == 'FAILED':
                            error_message = api_data.get('message', '未知原因') if isinstance(api_data, dict) else '未知原因'
                            logger.error(f"源任务 {original_job_id} 在 API 端失败 (原因: {error_message})。不会在本地创建记录。")
                            # We don't have it locally, so nothing to remove
                            failed_count += 1
                            continue

                        # Add source-specific fields and save
                        normalized_result.update({
                            "concept": normalized_result.get("concept") or "source_task",
                            "prompt": normalized_result.get("prompt") or f"Source task: {original_job_id}"
                        })
                        upsert_job_metadata(logger, original_job_id, normalized_result, metadata_dir)
                        logger.info(f"源任务 {original_job_id}: 基本信息已保存/更新 (状态: {api_status_from_poll})。")

                        if api_status_from_poll == 'SUCCESS':
                            image_url = normalized_result.get('url')
                            if image_url:
                                 # --- Generate filename --- #
                                 try:
                                     # Pass metadata_dir (assuming modified)
                                     current_metadata_for_naming = load_all_metadata(logger, metadata_dir)
                                     all_tasks_index_for_naming = _build_metadata_index(current_metadata_for_naming)
                                     expected_filename = _generate_expected_filename(logger, normalized_result, all_tasks_index_for_naming)
                                 except Exception as e:
                                     logger.error(f"为源任务 {original_job_id} 生成期望文件名时出错: {e}，将使用 job_id 作为备用名。")
                                     expected_filename = f"source_{original_job_id}.png"
                                 # ---------------------- #

                                 download_success, download_result_info, _ = download_and_save_image(
                                    logger,
                                    image_url,
                                    original_job_id,
                                    output_dir, # Pass output_dir
                                    expected_filename, # Pass expected filename (without dir)
                                    normalized_result.get("concept"),
                                    normalized_result.get("variations", ""),
                                    normalized_result.get("global_styles", ""),
                                    None, None, None, # No original_id, action, components for source itself
                                    normalized_result.get("seed")
                                )

                                 if download_success:
                                     filepath = download_result_info
                                     filename = os.path.basename(filepath) if filepath else None
                                     update_job_metadata(logger, original_job_id, {'status': 'completed', 'filepath': filepath, 'filename': filename})
                                     logger.info(f"源任务 {original_job_id}: 成功 (信息和图像已保存)")
                                     success_count += 1
                                 else:
                                     logger.warning(f"源任务 {original_job_id}: 信息已保存，但图像下载失败 ({download_result_info})。状态标记为 'file_missing'。")
                                     update_job_metadata(logger, original_job_id, {'status': 'file_missing', 'filepath': None, 'filename': None})
                                     failed_count += 1
                            else:
                                logger.info(f"源任务 {original_job_id}: API状态为 SUCCESS 但没有图像URL。状态标记为 'completed_no_url'。")
                                update_job_metadata(logger, original_job_id, {'status': 'completed_no_url', 'filepath': None, 'filename': None})
                                success_count += 1 # Count info sync as success
                        # No need for specific elif for FAILED as it's handled above
                        elif api_status_from_poll != 'SUCCESS': # Other statuses (pending etc)
                            logger.info(f"源任务 {original_job_id}: API 状态为 {api_status_from_poll}，本地记录已更新。")
                            # Status already set during upsert
                            skipped_count += 1
                    else:
                        # poll_for_result failed for the source task
                        logger.warning(f"无法从API获取源任务 {original_job_id} 的信息 (轮询失败/超时)。标记为 'source_poll_failed'。")
                        # Save placeholder metadata to avoid re-polling constantly?
                        placeholder_data = {
                            'job_id': original_job_id,
                            'status': 'source_poll_failed',
                            'concept': 'source_task',
                            'prompt': f'Source task, poll failed: {original_job_id}',
                            'metadata_added_at': datetime.now().isoformat()
                        }
                        upsert_job_metadata(logger, original_job_id, placeholder_data)
                        skipped_count += 1

                except Exception as e:
                    logger.exception(f"同步源任务 {original_job_id} 时发生意外错误: {str(e)}")
                    # Save placeholder metadata with error status?
                    placeholder_data = {
                        'job_id': original_job_id,
                        'status': 'source_sync_error',
                        'concept': 'source_task',
                        'prompt': f'Source task, sync error: {original_job_id}',
                        'metadata_added_at': datetime.now().isoformat()
                    }
                    upsert_job_metadata(logger, original_job_id, placeholder_data)
                    failed_count += 1
        else:
            if not silent: logger.info("没有发现引用未知源任务的任务")

    # 打印同步统计
    logger.info("同步完成统计:")
    logger.info(f"  - 成功(完成并下载/信息更新): {success_count}个任务")
    logger.info(f"  - 跳过(状态无需同步/API未完成): {skipped_count}个任务")
    logger.info(f"  - 失败(API失败/下载失败/同步错误): {failed_count}个任务")

    return (success_count, skipped_count, failed_count)
