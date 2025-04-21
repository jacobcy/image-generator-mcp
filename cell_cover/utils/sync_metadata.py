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
from .api import poll_for_result, normalize_api_response
from .config import get_api_key
from .filesystem_utils import (
    META_DIR, METADATA_FILENAME, IMAGE_DIR,
    ensure_directories, write_last_succeed_job_id,
    sanitize_filename
)
from .file_handler import MAX_FILENAME_LENGTH

def sync_tasks(
    logger: logging.Logger,
    api_key: str,
    all_tasks: Optional[List[Dict[str, Any]]] = None,
    silent: bool = False
) -> Tuple[int, int, int]:
    """同步本地任务状态和源任务信息。

    Args:
        logger: 日志记录器
        api_key: API密钥
        all_tasks: 可选的预加载任务列表，如果未提供则会从元数据文件加载
        silent: 是否静默运行（不输出彩色终端信息）

    Returns:
        tuple: (成功同步数, 跳过数, 失败数)
    """
    # 如果未提供任务列表，从元数据加载
    if all_tasks is None:
        all_tasks = load_all_metadata(logger)

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
                result = poll_for_result(logger, job_id, api_key)

                if result:
                    # 打印原始 API 响应以便调试
                    logger.debug(f"任务 {job_id} 的 API 响应: {result}")

                    # 使用标准化函数处理 API 响应
                    normalized_result = normalize_api_response(logger, result)
                    if not normalized_result:
                        logger.warning(f"规范化来自 API 的任务 {job_id} 的数据失败。")
                        update_job_metadata(logger, job_id, {'status': 'sync_error'})
                        failed_count += 1
                        continue

                    # 检查标准化后的数据是否包含 components 字段，如果有，将其移除
                    if "components" in normalized_result:
                        logger.debug(f"从标准化结果中移除 components 字段: {normalized_result['components']}")
                        del normalized_result["components"]

                    normalized_result['job_id'] = job_id # Ensure job_id
                    api_status = normalized_result.get('status')

                    # === 核心处理逻辑 ===
                    if api_status == 'failed':
                        error_message = normalized_result.get('fail_reason', '未知原因')
                        logger.error(f"任务 {job_id} 在 API 端失败 (原因: {error_message})，将从本地元数据中移除。")
                        # 直接删除失败的任务记录，而不是添加到待删除列表
                        if remove_job_metadata(logger, job_id):
                            logger.info(f"已从元数据中删除失败的任务 {job_id}")
                            if not silent:
                                print(f"已从元数据中删除失败的任务 {job_id}")
                        else:
                            logger.warning(f"无法从元数据中删除失败的任务 {job_id}")
                            if not silent:
                                print(f"警告：无法从元数据中删除失败的任务 {job_id}")
                        failed_count += 1
                        continue # 处理下一个任务

                    elif api_status == 'completed':
                        # 更新元数据为 API 的最新状态
                        upsert_job_metadata(logger, job_id, normalized_result)

                        image_url = normalized_result.get('url')
                        if image_url:
                            # 尝试下载
                            logger.info(f"任务 {job_id} API状态为 completed，尝试下载图像...")
                            # --- 生成期望的文件名 --- #
                            try:
                                # 重新生成 index 可能效率不高，但确保数据最新
                                current_metadata_for_naming = load_all_metadata(logger)
                                all_tasks_index = _build_metadata_index(current_metadata_for_naming)
                                expected_filename = _generate_expected_filename(logger, normalized_result, all_tasks_index)
                            except Exception as e:
                                logger.error(f"为任务 {job_id} 生成期望文件名时出错: {e}，将使用 job_id 作为备用名。")
                                expected_filename = f"{job_id}.png"
                            # ---------------------- #

                            download_success, download_result_info, _ = download_and_save_image(
                                logger,
                                image_url,
                                job_id,
                                normalized_result.get('prompt') or "",
                                expected_filename,
                                normalized_result.get('concept'),
                                normalized_result.get('variations'),
                                normalized_result.get('global_styles'),
                                normalized_result.get('original_job_id'),
                                normalized_result.get('action_code'),
                                None, # components
                                normalized_result.get('seed')
                            )
                            if download_success:
                                filepath = download_result_info
                                logger.info(f"任务 {job_id}: 图像下载成功，保存至 {filepath}")
                                filename = os.path.basename(filepath) if filepath else None
                                update_job_metadata(logger, job_id, {'status': 'completed', 'filepath': filepath, 'filename': filename}) # 确认状态和路径
                                success_count += 1
                            else:
                                # 下载失败，直接标记为 file_missing
                                logger.warning(f"任务 {job_id}: 图像下载失败 ({download_result_info})。状态标记为 'file_missing'。")
                                update_job_metadata(logger, job_id, {'status': 'file_missing', 'filepath': None, 'filename': None}) # 清除路径信息
                                failed_count += 1 # 计入失败，因为目标是下载
                        else:
                             # API 完成但无 URL
                            logger.warning(f"任务 {job_id}: API状态为 completed 但没有图像 URL。状态标记为 'completed_no_url'。")
                            update_job_metadata(logger, job_id, {'status': 'completed_no_url', 'filepath': None, 'filename': None})
                            skipped_count += 1

                    else: # API 返回其他状态 (pending, submitted, etc.)
                        logger.info(f"任务 {job_id}: API状态为 {api_status}，更新本地状态。")
                        update_job_metadata(logger, job_id, {'status': api_status})
                        skipped_count += 1 # 算作跳过，因为没有最终成功

                else:
                    # API 调用成功但未返回结果 (可能仍在处理中)
                    logger.warning(f"任务 {job_id}: API 查询无结果 (可能仍在处理中)。标记为 polling_failed。")
                    update_job_metadata(logger, job_id, {'status': 'polling_failed'})
                    skipped_count += 1

            except Exception as e:
                logger.exception(f"处理任务{job_id}时发生意外错误: {str(e)}")
                try:
                    update_job_metadata(logger, job_id, {'status': 'sync_error'})
                except Exception as update_err:
                    logger.error(f"尝试将任务 {job_id} 状态更新为 sync_error 时失败: {update_err}")
                logger.error(f"任务 {job_id}: 同步失败: {str(e)}")
                failed_count += 1
    else:
        logger.info("没有需要检查 API 状态或文件的任务。")

    # 再次加载 all_tasks 以获取最新状态，用于处理源任务
    all_tasks = load_all_metadata(logger)
    if all_tasks is None: # Check if loading failed
        logger.error("无法重新加载元数据以处理源任务，跳过源任务同步。")
    else:
        task_id_index = _build_metadata_index(all_tasks)
        tasks_with_missing_original = []
        processed_original_ids = set()
        for task in all_tasks:
            original_job_id = task.get('original_job_id')
            # 检查 original_job_id 是否是有效的 UUID 格式 (通常是36个字符且包含连字符)
            # 或者至少是一个看起来像有效 job ID 的字符串 (不是操作代码如 'upsample3')
            if original_job_id and original_job_id not in task_id_index and original_job_id not in processed_original_ids:
                # 跳过明显是操作代码而不是 job ID 的值
                if original_job_id.startswith(('upsample', 'variation')) and len(original_job_id) < 20:
                    job_id_prefix = task.get('job_id', '')
                    job_id_prefix = job_id_prefix[:6] if job_id_prefix else 'unknown'
                    logger.warning(f"跳过任务 {job_id_prefix} 中无效的 original_job_id: '{original_job_id}'，这看起来是一个操作代码而不是 job ID")
                    continue
                tasks_with_missing_original.append(task) # Store the task that references the missing original
                processed_original_ids.add(original_job_id)

        # 处理引用未知源任务的情况 (逻辑类似，但下载失败标记为 file_missing)
        if tasks_with_missing_original:
            logger.warning(f"找到 {len(tasks_with_missing_original)} 个任务引用了未知的源任务，尝试同步...")

            for i, task_referencing in enumerate(tasks_with_missing_original):
                original_job_id = task_referencing.get('original_job_id') # The ID we need to check
                referencing_job_id = task_referencing.get('job_id')

                logger.info(f"同步源任务 {original_job_id} (被 {referencing_job_id} 引用)...")

                try:
                    logger.info(f"开始轮询源任务 {original_job_id}...")
                    # 添加额外的检查，确保 original_job_id 看起来像一个有效的 job ID
                    if not original_job_id or len(original_job_id) < 20 or original_job_id.startswith(('upsample', 'variation')):
                        logger.error(f"跳过轮询无效的 original_job_id: '{original_job_id}'，这看起来不是一个有效的 job ID")
                        failed_count += 1
                        continue
                    result = poll_for_result(logger, original_job_id, api_key)

                    if result:
                        logger.debug(f"源任务 {original_job_id} 的 API 响应: {result}")
                        # 使用标准化函数处理 API 响应
                        normalized_result = normalize_api_response(logger, result)
                        if not normalized_result:
                            logger.warning(f"无法规范化来自 API 的源任务 {original_job_id} 的数据。")
                            failed_count += 1
                            continue

                        # 检查标准化后的数据是否包含 components 字段，如果有，将其移除
                        if "components" in normalized_result:
                            logger.debug(f"从标准化结果中移除 components 字段: {normalized_result['components']}")
                            del normalized_result["components"]

                        normalized_result['job_id'] = original_job_id
                        api_status = normalized_result.get('status')

                        if api_status == 'failed':
                            error_message = normalized_result.get('fail_reason', '未知原因')
                            logger.error(f"源任务 {original_job_id} 在 API 端失败 (原因: {error_message})，将从本地元数据中移除。")
                            # 直接删除失败的源任务记录
                            if remove_job_metadata(logger, original_job_id):
                                logger.info(f"已从元数据中删除失败的源任务 {original_job_id}")
                                if not silent:
                                    print(f"已从元数据中删除失败的源任务 {original_job_id}")
                            else:
                                logger.warning(f"无法从元数据中删除失败的源任务 {original_job_id}")
                                if not silent:
                                    print(f"警告：无法从元数据中删除失败的源任务 {original_job_id}")
                            failed_count += 1
                            continue

                        # 添加源任务特有的字段，并使用 upsert 保存 (即使未完成也保存基本信息)
                        normalized_result.update({
                            "concept": normalized_result.get("concept") or "source_task",
                            "prompt": normalized_result.get("prompt") or f"Source for: {referencing_job_id}"
                        })
                        upsert_job_metadata(logger, original_job_id, normalized_result)

                        if api_status == 'completed':
                            image_url = normalized_result.get('url')
                            if image_url:
                                 # --- 生成期望的文件名 --- #
                                 try:
                                     current_metadata_for_naming = load_all_metadata(logger)
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
                                    normalized_result.get("prompt") or "",
                                    expected_filename,
                                    normalized_result.get("concept"),
                                    normalized_result.get("variations", ""),
                                    normalized_result.get("global_styles", ""),
                                    None, None, None,
                                    normalized_result.get("seed")
                                )

                                 # --- 修正这里的缩进 ---
                                 if download_success:
                                     filepath = download_result_info
                                     filename = os.path.basename(filepath) if filepath else None
                                     update_job_metadata(logger, original_job_id, {'status': 'completed', 'filepath': filepath, 'filename': filename})
                                     logger.info(f"源任务 {original_job_id}: 成功 (信息和图像已保存)")
                                     success_count += 1
                                 else:
                                     # 源任务下载失败 -> file_missing
                                     logger.warning(f"源任务 {original_job_id}: 信息已保存，但图像下载失败 ({download_result_info})。状态标记为 'file_missing'。")
                                     update_job_metadata(logger, original_job_id, {'status': 'file_missing', 'filepath': None, 'filename': None})
                                     failed_count += 1
                                 # --- 结束缩进修正 ---
                            else:
                                logger.info(f"源任务 {original_job_id}: API状态为 completed 但没有图像URL。状态标记为 'completed_no_url'。")
                                update_job_metadata(logger, original_job_id, {'status': 'completed_no_url', 'filepath': None, 'filename': None})
                                success_count += 1 # 算成功同步信息
                        elif api_status == 'failed':
                            logger.warning(f"源任务 {original_job_id}: API 状态为 failed。标记为 'api_failed'。")
                            update_job_metadata(logger, original_job_id, {'status': 'api_failed'}) # 先标记，最后统一处理
                            failed_count += 1
                        else:
                            # 源任务状态非 completed 或 failed
                            logger.info(f"源任务 {original_job_id}: API 状态为 {api_status}，已更新本地记录。")
                            update_job_metadata(logger, original_job_id, {'status': api_status})
                            skipped_count += 1
                    else:
                        # 无法获取源任务信息
                        logger.warning(f"无法从API获取源任务 {original_job_id} 的信息。标记为 'source_not_found' (不保存)。")
                        # 不再创建 placeholder 记录
                        skipped_count += 1

                except Exception as e:
                    # API调用失败，标记为要删除的源任务
                    logger.error(f"从 API 查询源任务 {original_job_id} 时发生意外错误: {str(e)}")
                    # 直接删除失败的源任务记录
                    if remove_job_metadata(logger, original_job_id):
                        logger.info(f"已从元数据中删除查询失败的源任务 {original_job_id}")
                        if not silent:
                            print(f"已从元数据中删除查询失败的源任务 {original_job_id}")
                    else:
                        logger.warning(f"无法从元数据中删除查询失败的源任务 {original_job_id}")
                        if not silent:
                            print(f"警告：无法从元数据中删除查询失败的源任务 {original_job_id}")
                    failed_count += 1
        # <<< 源任务处理循环结束
        else:
            if not silent: logger.info("没有发现引用未知源任务的任务")

    # 打印同步统计
    logger.info("同步完成统计:")
    logger.info(f"  - 成功(完成并下载/信息更新): {success_count}个任务")
    logger.info(f"  - 跳过(状态无需同步/API未完成): {skipped_count}个任务")
    logger.info(f"  - 失败(API失败/下载失败/同步错误): {failed_count}个任务")

    return (success_count, skipped_count, failed_count)
