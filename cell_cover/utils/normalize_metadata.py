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

# 添加父目录到PATH，以便导入cell_cover模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cell_cover.utils.metadata_manager import (
    load_all_metadata, 
    # update_job_metadata # 不再使用逐条更新
)
# 需要导入底层的保存函数
from cell_cover.utils.image_metadata import _save_metadata_file 
from cell_cover.utils.api import normalize_api_response
from cell_cover.utils.filesystem_utils import METADATA_FILENAME, META_DIR

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('normalize_metadata')

def normalize_all_metadata(backup=True, dry_run=False):
    """读取并规范化所有元数据记录，确保字段命名一致。
    
    Args:
        backup (bool): 是否创建备份
        dry_run (bool): 是否只模拟运行不实际修改
        
    Returns:
        tuple: (成功规范化数量, 总记录数)
    """
    logger.info("开始规范化元数据...")
    
    # 1. 加载所有元数据
    all_tasks = load_all_metadata(logger)
    if not all_tasks:
        logger.error("无法加载元数据或元数据为空")
        return (0, 0)
    
    total_count = len(all_tasks)
    logger.info(f"已加载{total_count}条元数据记录")
    
    # 2. 如果需要，创建备份
    if backup and not dry_run:
        try:
            backup_path = f"{METADATA_FILENAME}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # 读取原始文件内容进行备份
            original_content = None
            if os.path.exists(METADATA_FILENAME):
                with open(METADATA_FILENAME, 'r', encoding='utf-8') as f_in:
                    try:
                        original_content = json.load(f_in)
                    except json.JSONDecodeError:
                        logger.warning("原始元数据文件解析失败，备份可能不完整")
                        # If JSON invalid, copy file directly
                        shutil.copy2(METADATA_FILENAME, backup_path)
                        logger.info(f"已将无法解析的元数据文件复制到: {backup_path}")
                        original_content = None # Reset to avoid dumping invalid JSON

            if original_content:
                with open(backup_path, 'w', encoding='utf-8') as f_out:
                    json.dump(original_content, f_out, indent=4, ensure_ascii=False)
                logger.info(f"已创建元数据备份: {backup_path}")
            elif not os.path.exists(METADATA_FILENAME):
                 logger.info("原始元数据文件不存在，无需备份")
            # Else: file exists but couldn't be parsed, backup already handled

        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            # 不应因为备份失败而中止规范化，继续执行
            # return (0, total_count)
    
    # 3. 统一处理每条记录，构建新的列表
    normalized_tasks_list = []
    processed_count = 0
    skipped_count = 0
    
    for task in all_tasks:
        original_task_copy = task.copy() # 用于比较
        job_id = task.get('job_id')
        if not job_id:
            logger.warning(f"跳过缺少job_id的记录: {task.get('id') or '未知ID'}")
            skipped_count += 1
            continue
        
        # 使用normalize_api_response函数统一格式化
        normalized = normalize_api_response(logger, task)
        
        # 确保保留关键字段
        if not normalized:
            logger.warning(f"规范化任务{job_id}失败，跳过")
            skipped_count += 1
            continue
            
        # --- 确保关键字段存在 --- #
        normalized['job_id'] = job_id # 确保job_id最终存在
        
        # 确保id存在
        if 'id' not in normalized or not normalized['id']:
            normalized['id'] = str(uuid.uuid4()) # 生成新的本地ID
            logger.debug(f"任务{job_id}缺少本地id，已生成: {normalized['id']}")
        
        # 确保有正确的时间戳
        if 'created_at' not in normalized:
            # 尝试从旧字段恢复，否则使用当前时间
            creation_time = task.get('metadata_added_at') or task.get('restored_at') or datetime.now().isoformat()
            normalized['created_at'] = creation_time
            logger.debug(f"任务{job_id}缺少created_at，已设置: {creation_time}")

        # 确保有正确的状态
        if 'status' not in normalized or not normalized['status']:
            # 根据是否有URL判断，否则设为unknown
            if task.get('url') or task.get('cdnImage'):
                normalized['status'] = 'completed'
            else:
                normalized['status'] = 'unknown'
            logger.debug(f"任务{job_id}缺少status，已推断: {normalized['status']}")

        # 处理special case: 如果是action结果，确保original_job_id和action_code存在
        if task.get('original_job_id') and 'original_job_id' not in normalized:
            normalized['original_job_id'] = task['original_job_id']
        if task.get('action_code') and 'action_code' not in normalized:
            normalized['action_code'] = task['action_code']
            
        # --- 打印差异 --- #
        diff_found = False
        diff_log = [f"任务 {job_id} (ID: {normalized.get('id')}) 规范化差异:"]
        all_keys = sorted(list(set(list(original_task_copy.keys()) + list(normalized.keys()))))
        
        for key in all_keys:
            original_value = original_task_copy.get(key)
            normalized_value = normalized.get(key)
            
            if original_value is None and normalized_value is not None:
                 diff_log.append(f"  + {key}: {normalized_value}")
                 diff_found = True
            elif original_value is not None and normalized_value is None:
                 diff_log.append(f"  - {key}: {original_value}")
                 diff_found = True
            elif original_value != normalized_value:
                 diff_log.append(f"  * {key}: {original_value} -> {normalized_value}")
                 diff_found = True
                 
        if diff_found:
            logger.info("\n".join(diff_log))
        else:
             logger.debug(f"任务 {job_id} (ID: {normalized.get('id')}) 无需规范化")
             
        # 添加到新列表
        normalized_tasks_list.append(normalized)
        processed_count += 1
    
    # 4. 构建最终的元数据结构并保存
    final_metadata_structure = {
        "images": normalized_tasks_list,
        "version": "1.1" # Increment version after normalization
    }
    
    if not dry_run:
        logger.info("准备覆盖写入规范化后的元数据...")
        # 使用底层的保存函数来覆盖写入
        save_success = _save_metadata_file(logger, METADATA_FILENAME, final_metadata_structure)
        if save_success:
            logger.info(f"元数据规范化完成: 共处理{processed_count}条记录，跳过{skipped_count}条。文件已更新: {METADATA_FILENAME}")
        else:
            logger.error("写入规范化后的元数据失败！请检查备份文件。")
            return (0, total_count) # Indicate failure
    else:
        logger.info(f"[DRY RUN] 元数据规范化模拟: 将处理{processed_count}条记录，跳过{skipped_count}条。")
        # Optionally print the structure in dry run
        # print(json.dumps(final_metadata_structure, indent=4, ensure_ascii=False))
    
    return (processed_count, total_count)

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description='元数据规范化工具')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    parser.add_argument('--dry-run', action='store_true', help='仅模拟运行不实际修改')
    
    args = parser.parse_args()
    
    processed_count, total_count = normalize_all_metadata(
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