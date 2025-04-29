#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
元数据规范化脚本
--------------
读取images_metadata.json文件，标准化所有记录，应用统一的字段命名，
移除不必要的字段，确保元数据格式一致。
"""

import os
import sys
import json
import logging
import argparse
import uuid # Import uuid
from datetime import datetime
from pathlib import Path
import shutil
from typing import Dict, Any, List
from tqdm import tqdm
import re

# 添加父目录到PATH，以便导入cell_cover模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cell_cover.utils.metadata_manager import (
    load_all_metadata,
    # update_job_metadata # 不再使用逐条更新
)
# 需要导入底层的保存函数
from cell_cover.utils.image_metadata import _save_metadata_file, _build_metadata_index, trace_job_history
from cell_cover.utils.api import normalize_api_response
# from cell_cover.utils.filesystem_utils import METADATA_FILENAME, META_DIR, IMAGE_DIR, sanitize_filename # Commented out due to ImportError
from cell_cover.utils.filesystem_utils import sanitize_filename # Keep this one
from cell_cover.utils.file_handler import MAX_FILENAME_LENGTH
from cell_cover.utils.file_handler import _generate_expected_filename

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('normalize_metadata')

# --- 元数据规范化核心逻辑 --- #

def normalize_all_metadata_records(logger: logging.Logger, tasks: List[Dict[str, Any]], output_dir: str, metadata_dir: str) -> List[Dict[str, Any]]:
    """规范化内存中的任务记录列表（两阶段处理），并尝试重命名关联的文件。

    Args:
        logger: 日志记录器。
        tasks: 原始任务记录列表。
        output_dir: 图片文件期望存放的基础目录。
        metadata_dir: 元数据文件所在的目录 (用于追溯历史)。

    Returns:
        List[Dict[str, Any]]: 规范化后的任务记录列表。
    """
    if not tasks:
        logger.warning("传入的任务列表为空，无需规范化。")
        return []

    logger.info(f"开始两阶段规范化内存中的 {len(tasks)} 条任务记录...")

    # --- 阶段一：基础标准化 --- #
    logger.info("--- 阶段一：基础标准化 --- ")
    pass1_tasks = []
    pass1_skipped_count = 0
    for original_task in tqdm(tasks, desc="阶段一: 基础标准化", unit="任务"):
        task_id_log = original_task.get('job_id') or original_task.get('id') or '未知ID'
        job_id = original_task.get('job_id')

        if not job_id:
            logger.warning(f"跳过缺少job_id的记录: {task_id_log}")
            pass1_skipped_count += 1
            continue

        try:
            normalized = normalize_api_response(logger, original_task)
            if not normalized:
                logger.warning(f"基础标准化任务 {job_id} 失败，跳过")
                pass1_skipped_count += 1
                continue
        except Exception as e:
            logger.error(f"基础标准化任务 {job_id} 时发生错误: {e}，跳过")
            pass1_skipped_count += 1
            continue

        # 确保核心字段存在
        normalized['job_id'] = job_id
        if 'id' not in normalized or not normalized['id']:
            normalized['id'] = str(uuid.uuid4())
        if 'created_at' not in normalized or not normalized['created_at']:
            creation_time = original_task.get('created_at') or original_task.get('metadata_added_at') or original_task.get('restored_at') or datetime.now().isoformat()
            normalized['created_at'] = creation_time
        if 'status' not in normalized or not normalized['status']:
            # 基础状态推断（后续可能被文件检查覆盖）
            if normalized.get('url') or original_task.get('filepath'):
                 normalized['status'] = 'completed' # Tentative
            else:
                 normalized['status'] = 'unknown'
        if 'variations' not in normalized or normalized['variations'] is None:
            normalized['variations'] = ""
        if 'global_styles' not in normalized or normalized['global_styles'] is None:
            normalized['global_styles'] = ""
        # 保留原始文件信息，阶段二使用
        normalized['_original_filepath'] = original_task.get('filepath')
        normalized['_original_filename'] = original_task.get('filename')

        pass1_tasks.append(normalized)

    logger.info(f"阶段一完成。基础标准化: {len(pass1_tasks)} 条，跳过: {pass1_skipped_count} 条。")

    # --- 阶段二：概念继承、文件名生成、文件处理 --- #
    logger.info("--- 阶段二：概念/文件处理 --- ")
    if not pass1_tasks:
        logger.warning("阶段一后没有可处理的任务，规范化结束。")
        return []

    final_normalized_tasks = []
    processed_count = 0
    skipped_count = 0 # 阶段二跳过 (e.g., FAILED status)
    error_count = 0
    rename_failure_count = 0
    file_missing_count = 0

    # 基于阶段一结果构建索引
    logger.info("构建元数据索引用于概念追溯...")
    all_tasks_index = _build_metadata_index(pass1_tasks)
    logger.info("索引构建完成。")

    for task in tqdm(pass1_tasks, desc="阶段二: 概念/文件处理", unit="任务"):
        job_id = task['job_id'] # 此时 job_id 必然存在
        current_task = task.copy() # 使用阶段一结果

        # 1. 概念规范化
        try:
            normalized_with_concept = normalize_task_metadata(current_task, all_tasks_index, logger, metadata_dir)
            current_task.update(normalized_with_concept) # 更新 current_task
            logger.debug(f"任务 {job_id[:6]} 概念规范化完成: concept='{current_task.get('concept')}'")
        except Exception as e:
            logger.error(f"规范化任务 {job_id[:6]} 的概念时发生错误: {e}")
            error_count += 1
            current_task['status'] = 'normalization_error'
            # 即使概念出错，也尝试继续处理文件

        # 2. 文件名生成
        expected_filename = None
        expected_filepath = None
        try:
            expected_filename = _generate_expected_filename(logger, current_task, all_tasks_index)
            expected_filepath = os.path.join(output_dir, expected_filename)
        except Exception as e:
             logger.error(f"为任务 {job_id[:6]} 生成期望文件名时出错: {e}")
             error_count += 1
             current_task['status'] = 'filename_error'
             # 保留原始或置空
             current_task['filename'] = current_task.get('_original_filename')
             current_task['filepath'] = current_task.get('_original_filepath')
             # 出错也添加到最终列表，但不进行文件检查
             final_normalized_tasks.append(current_task)
             continue

        # 3. 文件存在性检查和重命名
        original_filepath = current_task.pop('_original_filepath', None) # 取出并移除临时字段
        original_filename = current_task.pop('_original_filename', None)
        current_status = current_task.get('status') # 获取当前任务状态 (可能来自阶段一)

        file_exists = False
        actual_filepath = None

        # 检查顺序：1. 原始路径 2. 期望路径
        if original_filepath and os.path.exists(original_filepath):
            file_exists = True
            actual_filepath = original_filepath
            logger.debug(f"任务 {job_id[:6]} 在原始路径找到文件: {original_filepath}")
        elif expected_filepath and os.path.exists(expected_filepath):
             # This case handles if file was somehow already at expected path
            file_exists = True
            actual_filepath = expected_filepath
            logger.debug(f"任务 {job_id[:6]} 在期望路径找到文件: {expected_filepath}")

        # 仅当任务状态最初是 'completed' 或被推断为 'completed' 时，才进行文件相关的状态更新
        if current_status == 'completed':
            if file_exists:
                current_task['filepath'] = actual_filepath # 确认文件路径
                current_task['filename'] = os.path.basename(actual_filepath)
                # 文件存在，检查是否需要重命名
                if actual_filepath != expected_filepath:
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                        shutil.move(actual_filepath, expected_filepath)
                        logger.info(f"文件已重命名: '{current_task['filename']}' -> '{expected_filename}'")
                        current_task['filename'] = expected_filename # 更新为新文件名
                        current_task['filepath'] = expected_filepath # 更新为新文件路径
                        current_task['status'] = 'completed' # 保持 completed
                    except OSError as e:
                        logger.error(f"重命名文件失败: 从 '{actual_filepath}' 到 '{expected_filepath}' - {e}")
                        # 保留重命名前的实际路径和文件名
                        current_task['status'] = 'rename_failed'
                        rename_failure_count += 1
                else:
                    # 文件存在且已在正确位置 (文件名和路径都符合预期)
                    current_task['filename'] = expected_filename
                    current_task['filepath'] = expected_filepath
                    current_task['status'] = 'completed'
                    logger.debug(f"任务 {job_id[:6]} 文件已在正确位置: {expected_filepath}")
            else:
                # 文件丢失
                logger.warning(f"已完成任务 {job_id[:6]} 的文件丢失。检查路径: {original_filepath} 和 {expected_filepath}")
                current_task['status'] = 'file_missing'
                current_task['filename'] = None
                current_task['filepath'] = None
                file_missing_count += 1
        else:
            # 对于非 'completed' 任务，保留原状态
            # 只更新记录中的 filename 和 filepath 为期望值，以便后续下载等操作使用
            current_task['filename'] = expected_filename
            current_task['filepath'] = expected_filepath
            logger.debug(f"保留非 completed 任务 {job_id[:6]} 的状态 '{current_status}'，设置期望路径: {expected_filepath}")

        # --- 最终状态检查（例如，跳过 FAILED） ---
        if current_task.get('status') == 'FAILED':
            logger.info(f"跳过 FAILED 状态的任务 {job_id[:6]}，不添加到最终列表")
            skipped_count += 1
            continue

        final_normalized_tasks.append(current_task)
        processed_count += 1

    logger.info(f"--- 阶段二完成 --- ")
    logger.info(f"  最终处理: {processed_count} 条")
    logger.info(f"  跳过 (FAILED): {skipped_count} 条")
    logger.info(f"  文件丢失: {file_missing_count} 条")
    logger.info(f"  重命名失败: {rename_failure_count} 条")
    logger.info(f"  错误 (概念/文件名): {error_count} 条")
    logger.info(f"总规范化完成。有效记录: {len(final_normalized_tasks)} 条。")

    return final_normalized_tasks

# --- 旧的 normalize_all_metadata 函数修改以接收路径 --- #
def normalize_all_metadata(metadata_dir: str, output_dir: str, backup=True, dry_run=False):
    """读取并规范化所有元数据记录（调用新的两阶段处理函数）。

    Args:
        metadata_dir: 元数据文件所在目录。
        output_dir: 图片文件期望存放的基础目录。
        backup (bool): 是否创建备份
        dry_run (bool): 是否只模拟运行不实际修改

    Returns:
        tuple: (成功规范化数量, 总记录数)
    """
    metadata_filename = "images_metadata.json"
    metadata_filepath = os.path.join(metadata_dir, metadata_filename)
    logger.info(f"开始规范化元数据 (调用两阶段处理): {metadata_filepath}")

    # 1. 加载所有元数据 (Pass metadata_dir)
    all_tasks = load_all_metadata(logger, metadata_dir)
    if not all_tasks:
        logger.error("无法加载元数据或元数据为空")
        return (0, 0)

    total_count = len(all_tasks)
    logger.info(f"已加载{total_count}条原始元数据记录")

    # 2. 如果需要，创建备份
    if backup and not dry_run:
        try:
            backup_path = f"{metadata_filepath}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # 直接复制原始文件进行备份，因为加载可能已丢失信息
            if os.path.exists(metadata_filepath):
                 shutil.copy2(metadata_filepath, backup_path)
                 logger.info(f"已创建元数据备份: {backup_path}")
            else:
                 logger.info(f"原始元数据文件 {metadata_filepath} 不存在，无需备份")
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            # 继续执行，不因备份失败而中止

    # 3. 调用新的两阶段规范化函数 (Pass output_dir and metadata_dir)
    normalized_tasks_list = normalize_all_metadata_records(logger, all_tasks, output_dir, metadata_dir)

    processed_count = len(normalized_tasks_list)
    # 注意：这里的 skipped 应该是总数减去最终处理数，包括阶段一和阶段二跳过的
    skipped_overall = total_count - processed_count

    # 4. 构建最终的元数据结构并保存
    final_metadata_structure = {
        "images": normalized_tasks_list,
        "version": "1.2" # Increment version after this significant change
    }

    if not dry_run:
        logger.info("准备覆盖写入规范化后的元数据...")
        save_success = _save_metadata_file(logger, metadata_dir, final_metadata_structure)
        if save_success:
            logger.info(f"元数据规范化完成: 共处理{processed_count}条记录，跳过{skipped_overall}条。文件已更新: {metadata_filepath}")
        else:
            logger.error("写入规范化后的元数据失败！请检查备份文件。")
            return (0, total_count) # Indicate failure
    else:
        logger.info(f"[DRY RUN] 元数据规范化模拟: 将处理{processed_count}条记录，跳过{skipped_overall}条。")
        # print(json.dumps(final_metadata_structure, indent=4, ensure_ascii=False))

    return (processed_count, total_count)


# --- normalize_task_metadata 修改以接收 metadata_dir --- #
def normalize_task_metadata(task: dict, all_tasks: dict, logger, metadata_dir: str) -> dict:
    """
    规范化单个任务的元数据，只处理概念（concept）字段，不处理type字段。
    总是尝试追溯到根任务来获取 concept, variations, global_styles。

    Args:
        task (dict): 需要规范化的任务数据
        all_tasks (dict): 所有任务数据的索引或列表 (期望是构建好的 index)
        logger: 日志记录器
        metadata_dir: 元数据目录 (用于 trace_job_history)

    Returns:
        dict: 规范化后的任务数据，主要是更新concept字段
    """
    if not task:
        logger.warning("传入的任务数据为空")
        return {}

    # 创建任务的副本以避免修改原始数据
    normalized_task = task.copy()
    job_id = task.get('job_id', 'unknown_id') # For logging

    # 处理概念 (concept), variations, global_styles
    original_concept = task.get('concept') # Store original for logging
    original_variations = task.get('variations')
    original_styles = task.get('global_styles')
    original_job_id = task.get('original_job_id')

    # 只要任务有 original_job_id，就尝试追溯根任务
    if original_job_id:
        logger.debug(f"Task {job_id[:6]}: 有 original_job_id ({original_job_id[:6]})，尝试追溯历史...")
        history_chain = trace_job_history(logger, original_job_id, metadata_dir, all_tasks)

        root_concept = "unknown" # Default concept if trace fails or root has no concept
        root_variations = ""
        root_styles = ""
        root_job_id = "unknown_root"

        if history_chain and len(history_chain) > 0:
            root_task = history_chain[0]
            root_job_id = root_task.get('job_id', 'unknown_root')
            logger.debug(f"Task {job_id[:6]}: 找到根任务 {root_job_id[:6]}")

            root_concept_candidate = root_task.get('concept')
            if root_concept_candidate:
                root_concept = root_concept_candidate
                root_variations = root_task.get('variations', '')
                root_styles = root_task.get('global_styles', '')
            else:
                logger.warning(f"Task {job_id[:6]}: 根任务 {root_job_id[:6]} 的 concept 无效 ('{root_concept_candidate}')")
                # root_concept remains "unknown"
        else:
            logger.warning(f"Task {job_id[:6]}: 无法追溯到 original_job_id ({original_job_id[:6]}) 的根任务")
            # root_concept remains "unknown"

        # --- 保持继承的 concept, variations, styles --- #
        normalized_task['concept'] = root_concept
        normalized_task['variations'] = root_variations
        normalized_task['global_styles'] = root_styles
        logger.info(f"Task {job_id[:6]}: 继承自根任务 {root_job_id[:6]}: "
                    f"concept='{root_concept}', vars='{root_variations}', styles='{root_styles}'")

        # --- 设置 Action Job 的 action 字段 (保持 action_code 不变) --- #
        action_code = task.get('action_code') # Use original action_code
        if action_code and original_job_id: # Ensure both exist
            short_orig_id = original_job_id[:6]
            new_action_field_value = f"{action_code}_{short_orig_id}"
            logger.info(f"Task {job_id[:6]}: 设置 action 字段 (Action Job): '{new_action_field_value}'")
            normalized_task['action'] = new_action_field_value
            # Ensure action_code field itself exists and is unchanged
            normalized_task['action_code'] = action_code
        elif action_code:
            logger.warning(f"Task {job_id[:6]}: 有 action_code ('{action_code}') 但缺少 original_job_id，无法生成拼接的 action 字段。将 action 设置为 action_code 本身。")
            normalized_task['action'] = action_code
            normalized_task['action_code'] = action_code # Ensure it exists
        elif original_job_id:
            logger.warning(f"Task {job_id[:6]}: 有 original_job_id 但缺少 action_code，无法生成拼接的 action 字段。将 action 设置为 'unknown_action'。")
            normalized_task['action'] = f"unknown_action_{original_job_id[:6]}"
            normalized_task['action_code'] = None # Explicitly set action_code to None
        else: # Should not happen in this block, but for safety
             normalized_task['action'] = 'error_case'
             normalized_task['action_code'] = None

    else:
        # --- 处理非 Action 任务 (原创任务 / Recreate) --- #
        # 保持 concept, variations, global_styles 的处理逻辑
        concept = task.get('concept')
        is_invalid_concept = not concept or concept == "unknown" or (isinstance(concept, str) and concept.startswith("from_"))

        if is_invalid_concept:
            if concept != "unknown":
                 logger.info(f"Task {job_id[:6]}: 原创任务概念无效 ('{concept}')，设置为 'unknown'")
            normalized_task['concept'] = "unknown"
            normalized_task['variations'] = ""
            normalized_task['global_styles'] = ""
        else:
            logger.debug(f"Task {job_id[:6]}: 原创任务，保持有效概念 '{concept}'")
            if 'variations' not in normalized_task or normalized_task['variations'] is None:
                normalized_task['variations'] = ""
            if 'global_styles' not in normalized_task or normalized_task['global_styles'] is None:
                normalized_task['global_styles'] = ""

        # --- 设置原生任务的 action 字段 --- #
        logger.debug(f"Task {job_id[:6]}: 设置 action 字段 (原生任务): 'create'")
        normalized_task['action'] = 'create' # Assume 'create' for all non-action jobs
        normalized_task['action_code'] = None # Ensure action_code is None for non-action jobs

    # --- 移除旧的 action 字段 (如果它与 action_code 混淆了) --- #
    # This logic might be redundant if normalize_api_response already handles it,
    # but double-checking here based on the potential confusion.
    # If the goal is JUST to set the 'action' field as derived above,
    # we might not need this removal. Let's comment it out for now.
    # if 'action' in normalized_task and 'action_code' in normalized_task and normalized_task['action'] == normalized_task['action_code']:
    #    # If old 'action' was just a copy of 'action_code', remove it before setting the new one?
    #    # Or maybe normalize_api_response should handle not copying 'action' if 'action_code' exists?
    #    pass # Revisit if needed

    return normalized_task

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description='元数据规范化工具')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    parser.add_argument('--dry-run', action='store_true', help='仅模拟运行不实际修改')
    # Add arguments for directories if run standalone
    parser.add_argument('--cwd', default=os.getcwd(), help='指定工作目录 (默认: 当前目录)')

    args = parser.parse_args()

    # Setup paths based on cwd
    cwd = args.cwd
    crc_base_dir = os.path.join(cwd, '.crc')
    metadata_dir = os.path.join(crc_base_dir, 'metadata')
    output_dir = os.path.join(crc_base_dir, 'output')

    # Ensure directories exist if run standalone
    from cell_cover.utils.filesystem_utils import ensure_directories # Local import for standalone
    if not ensure_directories(logger, metadata_dir, output_dir):
        print(f"错误: 无法创建必要的目录 {metadata_dir} 或 {output_dir}")
        return 1

    # Call the modified function with paths
    processed_count, total_count = normalize_all_metadata(
        metadata_dir=metadata_dir,
        output_dir=output_dir,
        backup=not args.no_backup,
        dry_run=args.dry_run
    )

    skipped = total_count - processed_count
    if processed_count == 0 and total_count > 0:
        print(f"错误: 未能规范化任何记录 (总记录数: {total_count}, 跳过: {skipped})")
        return 1
    elif total_count == 0:
         print("元数据文件为空或无法加载，未执行任何操作。")
         return 0
    else:
        result_msg = f"规范化处理完成。总记录: {total_count}, 已处理: {processed_count}, 已跳过: {skipped}。"
        if args.dry_run:
            print(f"[DRY RUN] {result_msg}")
        else:
            print(f"成功: {result_msg} 文件已更新。")
        return 0

if __name__ == "__main__":
    sys.exit(main())
