# -*- coding: utf-8 -*-
import os
import logging
from typing import Optional, List
import typer # Need typer for Exit

# 从 utils 导入必要的函数和常量
from ..utils.image_splitter import split_image_into_four
from ..utils.filesystem_utils import read_last_job_id, read_last_succeed_job_id
from ..utils.image_metadata import find_initial_job_info
from ..utils.image_handler import download_and_save_image
from ..utils.file_handler import IMAGE_DIR

logger = logging.getLogger(__name__)

def is_image_path(identifier):
    """检查标识符是否是图片文件路径"""
    if not identifier:
        return False
    
    # 检查是否包含路径分隔符或以图片扩展名结尾
    return ('/' in identifier or '\\' in identifier or 
            identifier.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')))

def handle_select(args, logger, cwd, state_dir, default_output_base, metadata_dir):
    """处理 'select' 命令，基于 job_id 或图片路径查找并切割图片。"""
    if logger is None:
        logger = logging.getLogger(__name__)

    identifier = args.identifier
    select_parts = args.select_parts
    output_dir = args.output_dir

    # 如果没有提供标识符，尝试使用最近成功的任务
    if not identifier:
        logger.info("未提供标识符，尝试使用最近成功的任务...")
        identifier = read_last_succeed_job_id(logger, state_dir)
        if not identifier:
            error_msg = "未提供标识符且无法找到最近成功的任务 ID。"
            logger.error(error_msg)
            print(f"错误: {error_msg}")
            raise typer.Exit(code=1)
        logger.info(f"使用最近成功的任务 ID: {identifier}")

    logger.info(f"开始处理 select 命令，标识符: {identifier}")

    # --- 判断是图片路径还是 job_id --- #
    image_file_path = None
    
    if is_image_path(identifier):
        # 直接使用图片路径
        logger.info(f"标识符 '{identifier}' 被识别为图片路径")
        image_file_path = identifier
        
        # 如果是相对路径，尝试在当前目录和 images 目录中查找
        if not os.path.isabs(image_file_path):
            possible_paths = [
                os.path.join(cwd, image_file_path),
                os.path.join(cwd, 'images', image_file_path),
                image_file_path  # 原始路径
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    image_file_path = path
                    break
            else:
                error_msg = f"无法找到图片文件: {identifier}。已尝试查找路径: {possible_paths}"
                logger.error(error_msg)
                print(f"错误: {error_msg}")
                raise typer.Exit(code=1)
    else:
        # 通过元数据查找 job_id
        logger.info(f"标识符 '{identifier}' 被识别为 Job ID，在元数据中查找...")
        job_info = find_initial_job_info(logger, identifier, metadata_dir)

        if not job_info:
            error_msg = f"无法在元数据中找到标识符 '{identifier}' 的记录。"
            logger.error(error_msg)
            print(f"错误: {error_msg}")
            raise typer.Exit(code=1)

        image_file_path = job_info.get('filepath')

        if not image_file_path:
            error_msg = f"元数据中标识符 '{identifier}' 的记录缺少有效的 'filepath'。"
            logger.error(error_msg)
            print(f"错误: {error_msg}")
            raise typer.Exit(code=1)

        logger.info(f"根据标识符 '{identifier}' 在元数据中找到图片路径: {image_file_path}")

    # --- 验证文件存在性 --- #
    if not os.path.exists(image_file_path):
        error_msg = f"文件系统上找不到图片文件: {image_file_path}"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        raise typer.Exit(code=1)

    # --- 进行切割 --- #
    current_directory = args.output_dir or cwd  # Change to use cwd as default
    logger.info(f"正在切割图片: {image_file_path}，切割照片保存到images文件夹，选中照片保存到: {current_directory}")
    print(f"正在切割图片: {os.path.basename(image_file_path)}...")

    split_results = split_image_into_four(image_file_path, current_directory, select_parts)
    if isinstance(split_results, tuple) and len(split_results) > 0:
        paths = split_results[0]  # 假设第一个元素是路径列表
    else:
        paths = []

    if not any(paths):
        error_msg = "图片切割失败。"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        raise typer.Exit(code=1)

    print("图片切割完成。")

    if select_parts:
        selected_count = 0
        total_requested = len(select_parts)
        # Construct the message string separately
        select_msg = f"选择要保存的部分: {', '.join(select_parts)}"
        print(select_msg)
        for i, part_path in enumerate(paths):
            part_key = f'u{i+1}'
            if part_path and part_key in select_parts:
                logger.info(f"已选择并保留: {part_path}")
                print(f"  - 保留: {os.path.basename(part_path)}")
                selected_count += 1

        # Always return success now if splitting worked, as we don't delete
        images_dir = os.path.join(current_directory, "images")
        print(f"已标记 {selected_count} 个选定部分。")
        print(f"所有切割文件保存在: {images_dir}")
        print(f"选中文件保存在: {current_directory}")

        # 获取选中的文件路径（从split_results的第二个元素）
        if isinstance(split_results, tuple) and len(split_results) > 1:
            selected_paths = split_results[1]
            if selected_paths:
                print("选中的文件:")
                for selected_path in selected_paths:
                    print(f"  - {selected_path}")

        raise typer.Exit(code=0)
    else:
        images_dir = os.path.join(current_directory, "images")
        print(f"未指定选择 (-s)，所有切割部分已保存在目录: {images_dir}")
        for part_path in paths:
            if part_path:
                print(f"  - 保存路径: {part_path}")
        raise typer.Exit(code=0)

# Remove or comment out the old parameter list
# def handle_select(
#     image_path: Optional[str] = None,
#     last_succeed: bool = False,
#     output_dir: Optional[str] = None,
#     select: Optional[List[str]] = None,
#     logger=None
# ):
