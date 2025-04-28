# -*- coding: utf-8 -*-
import logging
from typing import Optional

# 区分 api.py 和 api_client.py
# Note: describe 似乎不需要 normalize_api_response
from ..utils.api_client import call_describe_api, poll_for_result
# from ..utils.api import call_describe_api, poll_for_result # 旧的导入方式
from ..utils.image_uploader import process_cref_image

logger = logging.getLogger(__name__)

def handle_describe(image_path_or_url: str, hook_url: Optional[str] = None, logger=None, api_key=None):
    """处理 'describe' 命令。"""
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info(f"准备提交 Describe 任务，图像: {image_path_or_url}")
    print("正在提交 Describe 任务...")
    submit_result = call_describe_api(
        logger=logger,
        api_key=api_key,
        image_path_or_url=image_path_or_url,
        hook_url=hook_url
    )

    if submit_result:
        job_id = submit_result
        logger.info(f"Describe 任务提交成功，Job ID: {job_id}")
        if not hook_url:
            logger.info("未提供 Webhook URL，将开始轮询 Describe 结果...")
            print("Polling for describe result...")
            poll_response = poll_for_result(logger, job_id, api_key)

            if poll_response:
                final_status, api_data = poll_response

                if final_status == "SUCCESS" and isinstance(api_data, dict):
                    generated_prompts_str = api_data.get("prompt", "")
                    if generated_prompts_str:
                        generated_prompts = generated_prompts_str.strip().split('\n')
                        logger.info("Describe 任务完成，获取到生成的提示词。")
                        print("--- API 生成的提示词 ---")
                        for i, p in enumerate(generated_prompts):
                            if p.strip():
                                print(f"{i+1}. {p.strip()}")
                        print("----------------------")
                        # TODO: Consider saving metadata for describe job
                        return 0
                    else:
                        logger.error("Describe 任务成功，但在结果中未找到提示词。")
                        print("错误：Describe 任务成功，但在结果中未找到提示词。")
                        return 1
                elif final_status == "FAILED":
                    error_message = api_data.get('message', '未知错误') if isinstance(api_data, dict) else '未知错误'
                    logger.error(f"轮询 Describe 任务结果失败。API 消息: {error_message}")
                    print(f"错误：轮询 Describe 任务结果失败。API 消息: {error_message}")
                    return 1
                else:
                    logger.error(f"轮询 Describe 任务结果返回意外状态: {final_status}")
                    print(f"错误：轮询 Describe 任务结果返回意外状态: {final_status}")
                    return 1
            else:
                logger.error(f"轮询 Describe 任务 {job_id} 失败或超时。")
                print(f"错误：轮询 Describe 任务 {job_id} 失败或超时。")
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
