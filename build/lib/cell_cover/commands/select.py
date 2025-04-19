# -*- coding: utf-8 -*-
import os
import logging

# 从 utils 导入必要的函数和常量
from ..utils.image_splitter import split_image_into_four
from ..utils.file_handler import IMAGE_DIR

logger = logging.getLogger(__name__)

def handle_select(args, logger):
    """处理 'select' 命令。"""
    if not os.path.exists(args.image_path):
        error_msg = f"指定的图片文件不存在: {args.image_path}"
        logger.error(error_msg)
        print(f"错误: {error_msg}")
        return 1

    output_directory = args.output_dir or IMAGE_DIR
    logger.info(f"正在切割图片: {args.image_path} 到目录: {output_directory}")
    print(f"正在切割图片: {os.path.basename(args.image_path)}...")

    split_results = split_image_into_four(args.image_path, output_directory)

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
            elif part_path:
                try:
                    os.remove(part_path)
                    logger.info(f"已删除未选择的部分: {part_path}")
                except OSError as e:
                    # Construct the message string separately
                    warning_msg = f"无法删除未选择的部分 {part_path}: {e}"
                    logger.warning(warning_msg)
                    print(f"警告: 无法删除未选择的部分 {os.path.basename(part_path)}")

        if selected_count == total_requested:
            print(f"成功保存 {selected_count} 个选定部分。")
            return 0
        else:
            # Construct the message string separately
            warning_msg = f"实际保存了 {selected_count} 个部分，请求了 {total_requested} 个。"
            logger.warning(warning_msg)
            print(f"警告: {warning_msg}")
            return 1
    else:
        print("未指定选择 (-s)，所有切割部分已保存在输出目录。")
        for part_path in split_results:
            if part_path:
                 print(f"  - {os.path.basename(part_path)}")
        return 0
