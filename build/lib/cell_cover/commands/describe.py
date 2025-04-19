# -*- coding: utf-8 -*-
import logging

# 从 utils 导入必要的函数
from ..utils.api import call_describe_api, poll_for_result

logger = logging.getLogger(__name__)

def handle_describe(args, logger, api_key):
    """处理 'describe' 命令。"""
    logger.info(f"准备提交 Describe 任务，图像: {args.image_path_or_url}")
    print("正在提交 Describe 任务...")
    submit_result = call_describe_api(
        logger=logger,
        api_key=api_key,
        image_path_or_url=args.image_path_or_url,
        hook_url=args.hook_url
    )

    if submit_result:
        job_id = submit_result
        logger.info(f"Describe 任务提交成功，Job ID: {job_id}")
        if not args.hook_url:
            logger.info("未提供 Webhook URL，将开始轮询 Describe 结果...")
            print("Polling for describe result...")
            final_result = poll_for_result(logger, job_id, api_key)
            if final_result and final_result.get("prompt"):
                generated_prompts_str = final_result.get("prompt", "")
                generated_prompts = generated_prompts_str.strip().split('\\n')
                logger.info("Describe 任务完成，获取到生成的提示词。")
                print("--- API 生成的提示词 ---")
                for i, p in enumerate(generated_prompts):
                    if p.strip():
                        # Ensure the f-string formatting is simple
                        print(f"{i+1}. {p.strip()}")
                print("----------------------")
                # TODO: Consider saving metadata for describe job
                return 0
            else:
                status = final_result.get('status') if final_result else 'N/A'
                # Construct message separately
                error_msg = f"轮询 Describe 任务结果失败或未获取到提示词。最后状态: {status}"
                logger.error(error_msg)
                print(f"错误：{error_msg}")
                return 1
        else:
            logger.info("提供了 Webhook URL，Describe 任务将在后台处理。")
            print("提供了 Webhook URL，任务将在后台处理。") # Keep user feedback
            # TODO: Consider saving initial metadata for describe job
            return 0
    else:
        # Construct message separately
        error_msg = "Describe 任务提交失败 (API 调用未返回 Job ID)"
        logger.error(error_msg)
        print(f"错误：{error_msg}")
        return 1
