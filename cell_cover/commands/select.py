# -*- coding: utf-8 -*-
import os
import logging

# 从 utils 导入必要的函数和常量
from ..utils.image_splitter import split_image_into_four
from ..utils.filesystem_utils import IMAGE_DIR, read_last_job_id
from ..utils.image_metadata import find_initial_job_info

logger = logging.getLogger(__name__)

def handle_select(args, logger):
    """处理 'select' 命令。"""
    image_file_path = args.image_path

    # --- Determine the image file path --- #
    if image_file_path is None:
        logger.info("未提供 image_path，尝试读取上一个 Job ID...")
        last_job_id = read_last_job_id(logger)
        if not last_job_id:
            logger.error("错误：必须提供 image_path 或确保之前有成功的操作记录 (last_job.json)。")
            print("错误：必须提供图片路径或确保之前有成功的操作记录。")
            return 1
        
        logger.info(f"使用上一个 Job ID: {last_job_id} 来查找图片路径...")
        job_info = find_initial_job_info(logger, last_job_id)
        if not job_info or not job_info.get('filepath'):
            logger.error(f"无法根据上一个 Job ID '{last_job_id}' 找到对应的文件路径信息。")
            print(f"错误：无法找到上一个任务 '{last_job_id}' 对应的文件路径。请检查元数据。")
            return 1
        
        image_file_path = job_info.get('filepath')
        logger.info(f"从元数据获取到图片路径: {image_file_path}")
    
    # --- Validate file existence --- #
    if not image_file_path or not os.path.exists(image_file_path):
        error_msg = f"最终确定的图片文件不存在或无效: {image_file_path}"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        return 1

    # --- Proceed with splitting --- #
    output_directory = args.output_dir or os.path.dirname(image_file_path) # Default output dir to same as input
    logger.info(f"正在切割图片: {image_file_path} 到目录: {output_directory}")
    print(f"正在切割图片: {os.path.basename(image_file_path)}...")

    split_results = split_image_into_four(image_file_path, output_directory)

    if not any(split_results):
        error_msg = "图片切割失败。"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        return 1

    print("图片切割完成。")

    if args.select:
        selected_count = 0
        total_requested = len(args.select)
        # Construct the message string separately
        select_msg = f"选择要保存的部分: {', '.join(args.select)}"
        print(select_msg)
        for i, part_path in enumerate(split_results):
            part_key = f'u{i+1}'
            if part_path and part_key in args.select:
                logger.info(f"已选择并保留: {part_path}")
                print(f"  - 保留: {os.path.basename(part_path)}")
                selected_count += 1

        # Always return success now if splitting worked, as we don't delete
        print(f"已标记 {selected_count} 个选定部分。所有切割文件均已保留。")
        return 0
    else:
        print("未指定选择 (-s)，所有切割部分已保存在输出目录。")
        for part_path in split_results:
            if part_path:
                 print(f"  - {os.path.basename(part_path)}")
        return 0
