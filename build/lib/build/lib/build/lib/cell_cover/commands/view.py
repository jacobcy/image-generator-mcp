# -*- coding: utf-8 -*-
import logging

# 从 utils 导入必要的函数
from ..utils.file_handler import find_initial_job_info
from ..utils.api import poll_for_result

logger = logging.getLogger(__name__)

def handle_view(args, logger, api_key):
    """处理 'view' 命令。"""
    job_info = None
    job_id = None
    if not args.remote:
        logger.info(f"正在查找任务 '{args.identifier}' 的本地详细信息...")
        job_info = find_initial_job_info(logger, args.identifier)

        if not job_info:
            warning_msg = f"在本地元数据中找不到任务 '{args.identifier}' 的信息。将尝试直接从 API 获取。"
            logger.warning(warning_msg)
            print(f"警告：{warning_msg}")
            job_id = args.identifier
        else:
            job_id = job_info.get("job_id")
            if not job_id:
                 warning_msg = f"任务 '{args.identifier}' 的本地元数据缺少 Job ID。将尝试直接从 API 获取。"
                 logger.warning(warning_msg)
                 print(f"警告：{warning_msg}")
                 job_id = args.identifier
    else:
        logger.info(f"--remote 标志已设置，将直接使用 '{args.identifier}' 作为 Job ID 从 API 获取信息。")
        job_id = args.identifier

    if not job_id:
        error_msg = "无法确定要查询的 Job ID。"
        logger.error(error_msg)
        print(f"错误：{error_msg}")
        return 1

    print(f"正在从 API 获取任务 {job_id} 的最新状态...")
    latest_result = poll_for_result(logger, job_id, api_key)

    print("\\n--- 任务详情 ---")
    print(f"  标识符:     {args.identifier}")
    if job_id: print(f"  Job ID:     {job_id}")

    if not args.remote and job_info:
         print("  --- 本地元数据 ---")
         if job_info.get("filename"): print(f"  本地文件名: {job_info['filename']}")
         if job_info.get("concept"): print(f"  概念:       {job_info['concept']}")
         prompt_local = job_info.get("prompt")
         if prompt_local:
             truncated_prompt = prompt_local[:80] + ('...' if len(prompt_local) > 80 else '')
             print(f"  原始提示词: {truncated_prompt}")
         if job_info.get("seed") is not None: print(f"  Seed:       {job_info['seed']}")
         if job_info.get("action_code"): print(f"  触发动作:   {job_info['action_code']}")
         if job_info.get("original_job_id"): print(f"  源任务ID:   {job_info['original_job_id']}")

    if latest_result:
        print("  --- API 最新状态 ---")
        status = latest_result.get('status')
        progress = latest_result.get('progress')
        image_url = latest_result.get('image_url') or latest_result.get('cdnImage')
        seed = latest_result.get('seed')
        prompt_api = latest_result.get('prompt')
        actions = latest_result.get('actions')
        msg = latest_result.get('msg') or latest_result.get('message')

        if status: print(f"  状态:       {status}")
        if progress is not None: print(f"  进度:       {progress}%")
        if image_url: print(f"  图像 URL:   {image_url}")
        if seed is not None: print(f"  Seed:       {seed}")
        if prompt_api and prompt_api != "":
             truncated_prompt_api = prompt_api[:80] + ('...' if len(prompt_api) > 80 else '')
             print(f"  提示词:     {truncated_prompt_api}")
        if actions: print(f"  可用动作:   {', '.join(actions)}")
        if msg: print(f"  消息:       {msg}")

        logger.debug(f"Full API result for {job_id}: {latest_result!r}")
    else:
        warning_msg = f"无法从 API 获取任务 {job_id} 的最新状态。"
        logger.warning(warning_msg)
        if not args.remote:
             print(f"警告：{warning_msg}")
        else:
             print("未能从 API 获取任务状态。")

    print("-----------------")
    return 0 if latest_result else 1
