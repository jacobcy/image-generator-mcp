# -*- coding: utf-8 -*-
import os
import logging
from typing import Optional, List
import typer # Need typer for Exit

# 从 utils 导入必要的函数和常量
from ..utils.image_splitter import split_image_into_four
from ..utils.filesystem_utils import IMAGE_DIR, read_last_job_id, read_last_succeed_job_id
from ..utils.image_metadata import find_initial_job_info

logger = logging.getLogger(__name__)

def handle_select(args, logger):
    """处理 'select' 命令，基于 job_id 查找并切割图片。"""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    job_id = args.job_id
    select_parts = args.select # Renamed variable from cli
    output_dir = args.output_dir
    
    logger.info(f"开始处理 select 命令，目标 Job ID: {job_id}")

    # --- Find the image file path using job_id --- #
    image_file_path = None
    job_info = find_initial_job_info(logger, job_id)
    
    if not job_info:
        error_msg = f"无法在元数据中找到 Job ID '{job_id}' 的记录。"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        raise typer.Exit(code=1)

    image_file_path = job_info.get('filepath')

    if not image_file_path:
        error_msg = f"元数据中 Job ID '{job_id}' 的记录缺少有效的 'filepath'。"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        raise typer.Exit(code=1)
        
    logger.info(f"根据 Job ID '{job_id}' 在元数据中找到图片路径: {image_file_path}")

    # --- Validate file existence --- #
    if not os.path.exists(image_file_path):
        error_msg = f"文件系统上找不到图片文件: {image_file_path} (来自 Job ID: '{job_id}')"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        raise typer.Exit(code=1)

    # --- Proceed with splitting --- #
    output_directory = output_dir or os.path.dirname(image_file_path) # Default output dir to same as input
    logger.info(f"正在切割图片: {image_file_path} 到目录: {output_directory}")
    print(f"正在切割图片: {os.path.basename(image_file_path)}...")

    split_results = split_image_into_four(image_file_path, output_directory)

    if not any(split_results):
        error_msg = "图片切割失败。"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        raise typer.Exit(code=1)

    print("图片切割完成。")

    if select_parts: # Use the renamed variable
        selected_count = 0
        total_requested = len(select_parts)
        # Construct the message string separately
        select_msg = f"选择要保存的部分: {', '.join(select_parts)}"
        print(select_msg)
        for i, part_path in enumerate(split_results):
            part_key = f'u{i+1}'
            if part_path and part_key in select_parts:
                logger.info(f"已选择并保留: {part_path}")
                print(f"  - 保留: {os.path.basename(part_path)}")
                selected_count += 1

        # Always return success now if splitting worked, as we don't delete
        print(f"已标记 {selected_count} 个选定部分。所有切割文件均已保留。")
        # Use typer.Exit(code=0) for explicit success exit
        raise typer.Exit(code=0)
    else:
        print("未指定选择 (-s)，所有切割部分已保存在输出目录。")
        for part_path in split_results:
            if part_path:
                 print(f"  - {os.path.basename(part_path)}")
        # Use typer.Exit(code=0) for explicit success exit
        raise typer.Exit(code=0)

# Remove or comment out the old parameter list
# def handle_select(
#     image_path: Optional[str] = None,
#     last_succeed: bool = False,
#     output_dir: Optional[str] = None,
#     select: Optional[List[str]] = None,
#     logger=None
# ):
