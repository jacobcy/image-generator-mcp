\
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
元数据恢复与同步工具
------------------
1. 从TTAPI获取的任务列表恢复本地缺失的元数据
2. 同步本地状态不确定的任务和引用但找不到的源任务
"""

import os
import json
import uuid
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# 从其他utils模块导入常量和函数
from .filesystem_utils import (
    META_DIR, METADATA_FILENAME, IMAGE_DIR,
    ensure_directories, write_last_succeed_job_id,
    sanitize_filename
)
from .image_metadata import (
    _load_metadata_file, _save_metadata_file, 
    update_job_metadata, upsert_job_metadata,
    load_all_metadata,
    _build_metadata_index,
    trace_job_history
)
from .api import poll_for_result, normalize_api_response
from .image_handler import download_and_save_image

def restore_metadata_from_remote(logger: logging.Logger, job_list: List[Dict[str, Any]], api_key: Optional[str] = None) -> Optional[int]:
    """从TTAPI获取的任务列表恢复本地缺失的元数据。
    
    Args:
        logger: 日志记录器
        job_list: 从TTAPI获取的任务列表
        api_key: API密钥，用于获取更多任务详情（可选）
    
    Returns:
        int: 恢复的记录数，如果发生错误则返回None
    """
    target_filename = METADATA_FILENAME
    logger.info(f"开始从TTAPI任务列表恢复缺失的元数据到{target_filename}...")

    # 1. 加载现有的本地元数据
    all_tasks = load_all_metadata(logger)
    if all_tasks is None:
        logger.critical("无法加载本地元数据，无法继续恢复操作")
        return None

    # 2. 构建任务ID索引
    existing_job_ids = {task.get('job_id') for task in all_tasks if task.get('job_id')}
    logger.info(f"已加载{len(existing_job_ids)}条现有本地元数据记录")

    # 3. 处理远程任务列表，找出缺失的任务
    restored_count = 0
    for remote_task in job_list:
        job_id = remote_task.get("job_id") or remote_task.get("jobId")
        if not job_id:
            logger.warning("远程任务缺少job_id，跳过")
            continue
            
        # 如果任务在本地不存在，则恢复
        if job_id not in existing_job_ids:
            # 标准化API响应
            normalized_data = normalize_api_response(logger, remote_task)
            if not normalized_data:
                logger.warning(f"无法标准化任务{job_id}的数据，跳过")
                continue
                
            # 确保有job_id
            normalized_data["job_id"] = job_id
            
            # 如果需要并且有API密钥，获取更多任务详情
            if api_key and normalized_data.get("status") == "completed":
                try:
                    logger.info(f"从API获取任务{job_id}的详细信息...")
                    api_result = poll_for_result(logger, job_id, api_key)
                    if api_result:
                        # 更新标准化数据
                        api_normalized = normalize_api_response(logger, api_result)
                        normalized_data.update(api_normalized)
                except Exception as e:
                    logger.warning(f"获取任务{job_id}的详情时出错: {str(e)}")
            
            # 添加恢复标记
            normalized_data["restored_at"] = datetime.now().isoformat()
            
            # 如果没有concept，设置为"restored"
            if not normalized_data.get("concept"):
                normalized_data["concept"] = "restored"
                
            # 保存到元数据
            success = upsert_job_metadata(logger, job_id, normalized_data)
            if success:
                restored_count += 1
                logger.info(f"已恢复任务{job_id}的元数据")
                
                # 如果有图像URL，尝试下载
                image_url = normalized_data.get("url")
                if image_url and api_key:
                    try:
                        # 收集下载所需信息
                        prompt_text = normalized_data.get("prompt", f"Job: {job_id}")
                        concept = normalized_data.get("concept", "restored")
                        variations = normalized_data.get("variations", "")
                        styles = normalized_data.get("global_styles", "")
                        original_job_id = normalized_data.get("original_job_id")
                        action_code = normalized_data.get("action_code")
                        
                        # 下载图像
                        download_success, saved_path, _ = download_and_save_image(
                            logger,
                            image_url,
                            job_id,
                            prompt_text,
                            concept,
                            variations,
                            styles,
                            original_job_id,
                            action_code,
                            None,  # 不传递components
                            normalized_data.get("seed")
                        )
                        
                        if download_success:
                            logger.info(f"已下载并保存任务{job_id}的图像: {saved_path}")
                            # 记录成功任务ID
                            write_last_succeed_job_id(logger, job_id)
                    except Exception as e:
                        logger.warning(f"下载任务{job_id}的图像时出错: {str(e)}")
            else:
                logger.error(f"保存任务{job_id}的元数据失败")

    logger.info(f"共恢复了{restored_count}个任务的元数据")
    return restored_count

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
    
    # 设置终端颜色
    C_GREEN = "\033[92m"
    C_RED = "\033[91m"
    C_YELLOW = "\033[93m"
    C_BLUE = "\033[94m"
    C_CYAN = "\033[96m"
    C_RESET = "\033[0m"
    
    # 打印函数，根据silent决定是否输出
    def print_status(message, end='\n', flush=False):
        if not silent:
            print(message, end=end, flush=flush)
    
    print_status(f"\n{C_CYAN}开始同步任务状态...{C_RESET}")
    
    # 统计变量
    sync_count = 0
    skipped_count = 0
    failed_count = 0
    
    # 1. 找出状态不确定的任务
    pending_tasks = []
    for task in all_tasks:
        status = task.get('status')
        # 确保状态是字符串类型
        if isinstance(status, bool):
            status_str = str(status).lower()
        else:
            status_str = str(status).lower() if status else ''
            
        # 如果状态为空、pending、submitted等，需要同步
        if not status_str or status_str in ['pending', 'pending_queue', 'on_queue', 'submitted', 'submitted_webhook', 'polling_failed', 'false']:
            pending_tasks.append(task)
    
    # 2. 找出有原始任务ID但在本地找不到的任务
    tasks_with_missing_original = []
    task_id_index = {task.get('job_id'): task for task in all_tasks if task.get('job_id')}
    
    for task in all_tasks:
        original_job_id = task.get('original_job_id')
        if original_job_id and original_job_id not in task_id_index:
            tasks_with_missing_original.append(task)
    
    # 处理状态不确定的任务
    if pending_tasks:
        print_status(f"\n{C_YELLOW}找到{len(pending_tasks)}个状态不确定的任务{C_RESET}")
        
        for i, task in enumerate(pending_tasks):
            job_id = task.get('job_id')
            if not job_id:
                logger.warning(f"任务缺少Job ID，跳过同步")
                skipped_count += 1
                continue
            
            print_status(f"[{i+1}/{len(pending_tasks)}] 同步任务{job_id[:6]}... ", end='', flush=True)
            
            try:
                result = poll_for_result(logger, job_id, api_key)
                
                if result:
                    # 使用标准化函数处理API返回值
                    normalized_result = normalize_api_response(logger, result)
                    
                    # 更新本地元数据
                    update_job_metadata(logger, job_id, normalized_result)
                    
                    # 如果有图像URL，下载并保存图像
                    image_url = normalized_result.get('url')
                    if image_url:
                        prompt_text = task.get("prompt", f"Job: {job_id}")
                        concept = task.get("concept", "unknown")
                        variations = task.get("variations", "")
                        styles = task.get("global_styles", "")
                        original_job_id_link = task.get("original_job_id")
                        action_code_done = task.get("action_code")
                        
                        download_success, saved_path, _ = download_and_save_image(
                            logger,
                            image_url,
                            job_id,
                            prompt_text,
                            concept,
                            variations,
                            styles,
                            original_job_id_link,
                            action_code_done,
                            None,  # 不传递components
                            normalized_result.get("seed")
                        )
                        
                        if download_success:
                            write_last_succeed_job_id(logger, job_id)
                            print_status(f"{C_GREEN}成功 (图像已保存){C_RESET}")
                        else:
                            print_status(f"{C_YELLOW}成功 (API状态已更新，但图像下载失败){C_RESET}")
                    else:
                        print_status(f"{C_YELLOW}成功 (API状态已更新，但没有图像URL){C_RESET}")
                    
                    sync_count += 1
                else:
                    # API调用成功但未返回结果，可能任务仍在处理中
                    print_status(f"{C_YELLOW}跳过 (任务仍在处理中或已失败){C_RESET}")
                    skipped_count += 1
            
            except Exception as e:
                logger.error(f"同步任务{job_id}时出错: {str(e)}")
                print_status(f"{C_RED}失败: {str(e)}{C_RESET}")
                failed_count += 1
    else:
        print_status(f"{C_GREEN}没有发现状态不确定的任务{C_RESET}")
    
    # 处理有原始任务ID但在本地找不到的任务
    if tasks_with_missing_original:
        print_status(f"\n{C_YELLOW}找到{len(tasks_with_missing_original)}个任务引用了未知的源任务{C_RESET}")
        
        for i, task in enumerate(tasks_with_missing_original):
            original_job_id = task.get('original_job_id')
            job_id = task.get('job_id')
            
            print_status(f"[{i+1}/{len(tasks_with_missing_original)}] 同步源任务{original_job_id[:6]} (被引用于{job_id[:6]})... ", end='', flush=True)
            
            try:
                # 尝试获取源任务信息
                result = poll_for_result(logger, original_job_id, api_key)
                
                if result:
                    # 使用标准化函数处理API返回值
                    normalized_result = normalize_api_response(logger, result)
                    
                    # 添加源任务特有的字段
                    normalized_result.update({
                        "job_id": original_job_id,
                        "concept": normalized_result.get("concept") or "source_task",  # 优先使用API返回的概念
                        "prompt": normalized_result.get("prompt") or f"Source for: {job_id}"
                    })
                    
                    # 保存源任务的元数据
                    update_job_metadata(logger, original_job_id, normalized_result)
                    
                    # 如果有图像URL，下载并保存图像
                    image_url = normalized_result.get('url')
                    if image_url:
                        download_success, saved_path, _ = download_and_save_image(
                            logger,
                            image_url,
                            original_job_id,
                            normalized_result.get("prompt"),
                            normalized_result.get("concept"),
                            "",
                            "",
                            None,
                            None,
                            None,  # 不传递components
                            normalized_result.get("seed")
                        )
                        
                        if download_success:
                            print_status(f"{C_GREEN}成功 (源任务信息和图像已保存){C_RESET}")
                        else:
                            print_status(f"{C_YELLOW}成功 (源任务信息已保存，但图像下载失败){C_RESET}")
                    else:
                        print_status(f"{C_YELLOW}成功 (源任务信息已保存，但没有图像URL){C_RESET}")
                    
                    sync_count += 1
                else:
                    # API调用成功但未返回结果
                    print_status(f"{C_YELLOW}跳过 (源任务未找到或已失败){C_RESET}")
                    skipped_count += 1
            
            except Exception as e:
                logger.error(f"同步源任务{original_job_id}时出错: {str(e)}")
                print_status(f"{C_RED}失败: {str(e)}{C_RESET}")
                failed_count += 1
    else:
        print_status(f"{C_GREEN}没有发现引用未知源任务的任务{C_RESET}")
    
    # 打印同步统计
    print_status(f"\n{C_CYAN}同步完成:{C_RESET}")
    print_status(f"  - {C_GREEN}成功:{C_RESET} {sync_count}个任务")
    print_status(f"  - {C_YELLOW}跳过:{C_RESET} {skipped_count}个任务")
    print_status(f"  - {C_RED}失败:{C_RESET} {failed_count}个任务")
    
    return (sync_count, skipped_count, failed_count)

# --- 文件名生成辅助函数 --- #

def _generate_expected_filename(logger: logging.Logger, task_data: Dict[str, Any], all_tasks_index: Dict[str, Dict[str, Any]]) -> str:
    """根据规范生成期望的文件名。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = task_data.get('job_id')
    job_id_part = job_id[:6] if job_id else "nojobid"
    filename = ""
    prefix = task_data.get("prefix", "") # Handle potential prefix from recreate

    action_code = task_data.get('action_code')
    original_job_id = task_data.get('original_job_id')

    # 清理变体和风格
    variations = task_data.get('variations', [])
    styles = task_data.get('global_styles', [])
    clean_variations = [v for v in variations if v] if isinstance(variations, list) else ([variations] if variations else [])
    clean_styles = [s for s in styles if s] if isinstance(styles, list) else ([styles] if styles else [])

    if action_code and original_job_id:
        # --- Action 任务命名 --- #
        # 尝试从原始任务获取concept，需要追溯
        original_concept = "unknown"
        try:
            history = trace_job_history(logger, original_job_id, all_tasks_index) # 使用索引优化查找
            if history:
                root_task = history[0]
                if root_task.get('concept') and root_task.get('concept') not in ["action", "unknown", "restored", "source_task"]:
                    original_concept = root_task.get('concept')
                else:
                    # 如果根任务 concept 不可用，尝试用原始任务的 prompt 生成
                    original_task = all_tasks_index.get(original_job_id)
                    if original_task and original_task.get("prompt"):
                         original_concept = f"from_prompt_{original_job_id[:6]}"
                    else:
                         original_concept = f"from_{original_job_id[:6]}"
            else:
                 original_concept = f"no_history_{original_job_id[:6]}"
        except Exception as e:
            logger.warning(f"为任务 {job_id} 追溯原始概念时出错: {e}")
            original_concept = f"trace_error_{original_job_id[:6]}"
            
        base_concept = sanitize_filename(original_concept)
        orig_job_id_part = original_job_id[:6]
        safe_action_code = sanitize_filename(action_code)
        filename = f"{prefix}{base_concept}-{orig_job_id_part}-{safe_action_code}-{timestamp}.png"
    else:
        # --- 原始任务命名 --- #
        concept = task_data.get('concept', 'direct')
        base_concept = sanitize_filename(concept)
        parts = [prefix + base_concept, job_id_part]
        if clean_variations:
            parts.append("-".join(map(sanitize_filename, clean_variations)))
        if clean_styles:
            parts.append("-".join(map(sanitize_filename, clean_styles)))
        parts.append(timestamp)
        filename = "-".join(parts) + ".png"

    # Limit overall filename length
    filename = filename[:MAX_FILENAME_LENGTH]
    if not filename.lower().endswith('.png'):
         filename = filename[:MAX_FILENAME_LENGTH - 4] + ".png"
         
    return filename

# --- 元数据规范化核心逻辑 --- #

def normalize_all_metadata_records(logger: logging.Logger, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """规范化内存中的任务记录列表，并尝试重命名关联的文件。"""
    logger.info(f"开始规范化内存中的 {len(tasks)} 条任务记录，并尝试重命名文件...")
    normalized_tasks_list = []
    processed_count = 0
    skipped_count = 0
    
    # 构建任务索引以优化历史追溯
    all_tasks_index = _build_metadata_index(tasks)

    for task in tasks:
        original_task_copy = task.copy() # 用于比较和获取旧路径
        job_id = task.get('job_id')
        if not job_id:
            logger.warning(f"跳过缺少job_id的记录: {task.get('id') or '未知ID'}")
            skipped_count += 1
            continue

        # 标准化元数据记录
        normalized = normalize_api_response(logger, task)
        if not normalized:
            logger.warning(f"规范化任务 {job_id} 失败，跳过")
            skipped_count += 1
            continue
            
        normalized['job_id'] = job_id
        if 'id' not in normalized or not normalized['id']:
            normalized['id'] = str(uuid.uuid4())
        if 'created_at' not in normalized or not normalized['created_at']:
            creation_time = task.get('created_at') or task.get('metadata_added_at') or task.get('restored_at') or datetime.now().isoformat()
            normalized['created_at'] = creation_time
        if 'status' not in normalized or not normalized['status']:
            if task.get('url') or task.get('cdnImage'):
                normalized['status'] = 'completed'
            else:
                normalized['status'] = task.get('status', 'unknown')
        if task.get('original_job_id') and 'original_job_id' not in normalized:
            normalized['original_job_id'] = task['original_job_id']
        if task.get('action_code') and 'action_code' not in normalized:
            normalized['action_code'] = task['action_code']

        # --- 文件名和路径处理 --- #
        current_filepath = original_task_copy.get('filepath')
        current_filename = original_task_copy.get('filename')
        expected_filename = _generate_expected_filename(logger, normalized, all_tasks_index)
        expected_filepath = os.path.join(IMAGE_DIR, expected_filename)

        # 检查文件名是否需要更新
        if current_filename != expected_filename:
            logger.info(f"任务 {job_id}: 文件名需要更新: '{current_filename}' -> '{expected_filename}")
            # 检查旧文件是否存在并尝试重命名
            if current_filepath and os.path.exists(current_filepath):
                try:
                    os.rename(current_filepath, expected_filepath)
                    logger.info(f"  成功重命名文件: '{current_filepath}' -> '{expected_filepath}")
                    # 更新元数据中的路径信息
                    normalized['filename'] = expected_filename
                    normalized['filepath'] = expected_filepath
                except OSError as e:
                    logger.error(f"  重命名文件失败: {e}。元数据将更新为期望路径，但文件可能仍在旧位置。")
                    # 即使重命名失败，仍然更新元数据以反映期望状态
                    normalized['filename'] = expected_filename
                    normalized['filepath'] = expected_filepath
            else:
                logger.warning(f"  原始文件路径 '{current_filepath}' 不存在或未记录，仅更新元数据中的文件名和路径。")
                # 文件不存在，直接更新元数据为期望值
                normalized['filename'] = expected_filename
                normalized['filepath'] = expected_filepath
        else:
             # 文件名无需更新，但确保元数据中的路径是正确的
             if normalized.get('filepath') != expected_filepath:
                  logger.debug(f"任务 {job_id}: 文件名一致，但路径需要更新为 '{expected_filepath}")
                  normalized['filepath'] = expected_filepath
                  normalized['filename'] = expected_filename # 保持一致
             else:
                  logger.debug(f"任务 {job_id}: 文件名和路径已符合规范")
                  # 确保 filename 和 filepath 仍然存在于 normalized 字典中
                  if 'filename' not in normalized and current_filename:
                      normalized['filename'] = current_filename
                  if 'filepath' not in normalized and current_filepath:
                      normalized['filepath'] = current_filepath
                      
        # --- (打印差异的逻辑保持不变，但现在会包含 filename/filepath 的变化) --- #
        # ... (Diff printing logic remains largely the same) ...
        diff_found = False
        diff_log = [f"任务 {job_id} (ID: {normalized.get('id')}) 规范化差异:"]
        all_keys = sorted(list(set(list(original_task_copy.keys()) + list(normalized.keys()))))
        
        for key in all_keys:
            original_value = original_task_copy.get(key)
            normalized_value = normalized.get(key)
            
            # Skip comparing complex objects if necessary or format them
            # Example: compare timestamps by parsing them if they are strings
            
            if original_value != normalized_value:
                 if original_value is None:
                     diff_log.append(f"  + {key}: {normalized_value}")
                 elif normalized_value is None:
                     diff_log.append(f"  - {key}: {original_value}")
                 else:
                     diff_log.append(f"  * {key}: {original_value} -> {normalized_value}")
                 diff_found = True
                 
        if diff_found:
            logger.info("\n".join(diff_log))
        # else: # Reduce noise, only log if changed
        #      logger.debug(f"任务 {job_id} (ID: {normalized.get('id')}) 无需规范化")
             
        normalized_tasks_list.append(normalized)
        processed_count += 1

    logger.info(f"内存中规范化完成: 处理 {processed_count}, 跳过 {skipped_count}")
    return normalized_tasks_list
