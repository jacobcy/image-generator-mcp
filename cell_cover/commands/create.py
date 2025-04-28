# -*- coding: utf-8 -*-
import os
import logging
import uuid
from datetime import datetime
import re
from typing import Optional, List, Dict, Any

# 从 utils 导入必要的函数
# Use the centralized metadata_manager
from ..utils.metadata_manager import (
    save_image_metadata,
    # find_initial_job_info # Needed if we pre-check concept? - 暂时未使用
)
from ..utils.api import normalize_api_response
from ..utils.api_client import call_imagine_api, poll_for_result, check_prompt
from ..utils.prompt import generate_prompt_text, save_text_prompt, copy_to_clipboard, PYPERCLIP_AVAILABLE
# download_and_save_image now handles saving metadata via metadata_manager
from ..utils.image_handler import download_and_save_image
from ..utils.image_uploader import process_cref_image
# Import file_handler only for directory constants/functions if needed
from ..utils.file_handler import OUTPUT_DIR
from ..utils.image_metadata import load_all_metadata, _build_metadata_index
from ..utils.normalize_metadata import _generate_expected_filename

logger = logging.getLogger(__name__)

def handle_create(
    config: Dict[str, Any],
    logger: logging.Logger,
    api_key: str,
    concept: str = None,
    prompt: str = None,
    variation: str = None,
    style: str = None,
    aspect: str = None,
    quality: str = None,
    version: str = None,
    cref: str = None,
    clipboard: bool = False,
    save_prompt: bool = False,
    mode: str = None,
    hook_url: str = None,
    notify_id: str = None,
):
    """处理 'create' 命令。"""
    if config is None:
        print("FATAL ERROR: Config object is None in handle_create.")
        if logger:
            logger.critical("Config object is None!")
        return 1

    if logger is None:
        print("WARNING: Logger object is None in handle_create.")

    log_func = logger.info if logger else print

    # --- 1. 处理参考图片 (Cref) ---
    cref_url = None
    if cref:
        # process_cref_image handles logging and printing errors
        cref_url = process_cref_image(logger, cref)
        if not cref_url:
            return 1 # Exit if cref processing failed
        else:
            logger.info(f"使用处理后的 Cref URL: {cref_url}")

    # --- 2. 生成提示词 --- #
    base_prompt = ""  # 初始化基础提示词
    concept_key_for_save = None # 用于文件名（如果需要保存prompt文件）
    concept_for_metadata = None # 用于元数据

    # 步骤 1 & 2: 获取概念提示词和追加用户提示词
    if concept:
        if "concepts" not in config or concept not in config["concepts"]:
            logger.error(f"错误：在配置中未找到概念 '{concept}'")
            print(f"错误：在配置中未找到概念 '{concept}'")
            return 1
        concept_prompt = config["concepts"][concept].get("midjourney_prompt", "")
        concept_prompt = re.sub(r'--\w+\s+[^\s]+', '', concept_prompt).strip()
        base_prompt = re.sub(r'\s+', ' ', concept_prompt).strip()
        concept_key_for_save = concept
        concept_for_metadata = concept # 记录使用的概念
        logger.info(f"从概念 '{concept}' 加载核心提示词。")
    # --- 添加处理未指定 concept 的情况 --- #
    else:
        concept_for_metadata = "temp" # 如果没有指定 concept，元数据中记录为 "temp"
        logger.info("未指定 --concept，元数据中的概念将记录为 'temp'。")
    # ------------------------------------ #

    if prompt:
        cleaned_user_prompt = re.sub(r'--\w+\s+[^\s]+', '', prompt).strip()
        cleaned_user_prompt = re.sub(r'\s+', ' ', cleaned_user_prompt).strip()
        if base_prompt:
            base_prompt += " " + cleaned_user_prompt
            logger.info(f"将清理后的用户 --prompt 追加到概念提示词。")
        else:
            base_prompt = cleaned_user_prompt
            logger.info(f"使用清理后的用户 --prompt 作为基础提示词。")

    if not base_prompt:
        logger.error("错误：必须提供 --concept 或 --prompt 才能生成提示词。")
        print("错误：必须提供 --concept 或 --prompt 才能生成提示词。")
        return 1

    # 步骤 4: 收集并附加参数
    params_to_append = []

    # 附加 cref URL (如果处理成功)
    if cref_url:
        params_to_append.append(f"--cref {cref_url}")

    # 附加 aspect_ratio, quality, version 参数
    aspect_ratios = config.get("aspect_ratios", {})
    quality_settings = config.get("quality_settings", {})
    style_versions = config.get("style_versions", {})
    
    aspect_param = aspect_ratios.get(aspect)
    quality_param = quality_settings.get(quality)
    version_param = style_versions.get(version)

    if aspect_param: params_to_append.append(aspect_param)
    if quality_param: params_to_append.append(quality_param)
    if version_param: params_to_append.append(version_param)

    # 附加 style 参数 (处理 variation 和 style 选项)
    if style:
        global_styles = config.get("global_styles", {})
        style_text = global_styles.get(style, style)
        if not style_text.strip().startswith("--s"):
             base_prompt += " " + style_text # Style text is descriptive, append
        else:
            params_to_append.append(style_text) # Style text is a parameter (--s)
        logger.info(f"应用了样式: {style}")
    elif variation and concept: # Apply variation only if concept specified and no global style
        # Check concept exists before accessing variations
        if concept and concept in config.get("concepts", {}):
             variations = config["concepts"][concept].get("variations", {})
             variation_text = variations.get(variation)
             if variation_text:
                 cleaned_variation_text = re.sub(r'--\w+\s+[^\s]+', '', variation_text).strip()
                 cleaned_variation_text = re.sub(r'\s+', ' ', cleaned_variation_text).strip()
                 base_prompt += " " + cleaned_variation_text # Append cleaned variation text
                 logger.info(f"应用了概念 '{concept}' 的变体: {variation}")
             else:
                 logger.warning(f"警告：在概念 '{concept}' 中未找到变体 '{variation}'")
                 print(f"警告：在概念 '{concept}' 中未找到变体 '{variation}'")
        else:
             logger.warning(f"警告：尝试应用变体 '{variation}' 但未提供有效概念 '{concept}'")
             print(f"警告：尝试应用变体 '{variation}' 但未提供有效概念 '{concept}'")
    
    # 步骤 5: 组合最终提示词
    prompt_text = base_prompt
    if params_to_append:
        prompt_text += " " + " ".join(params_to_append)
    
    # 去除多余空格
    prompt_text = re.sub(r'\s+', ' ', prompt_text).strip()
    
    # --- 后续处理不变 --- #

    # 检查版本与 cref 的兼容性
    if cref_url and version_param and "--v 6" not in version_param and "--v 7" not in version_param:
        logger.warning("警告：--cref 参数通常与 Midjourney v6 或 v7 一起使用。")
        print("警告：--cref 参数通常与 Midjourney v6 或 v7 一起使用。")

    logger.info(f"最终生成的提示词: {prompt_text}")
    display_text = prompt_text
    print(f'''Generated Prompt:
---
{display_text}
---''')

    if clipboard:
        if PYPERCLIP_AVAILABLE:
            copy_to_clipboard(logger, display_text)
            logger.info("提示词已复制到剪贴板。")
        else:
            logger.warning("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
            print("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
    if save_prompt:
        filename_base = concept_key_for_save if concept_key_for_save else f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_text_prompt(logger, OUTPUT_DIR, display_text, filename_base)

    # --- 3. 检查提示词安全 --- #
    logger.info("正在检查提示词安全性...")
    is_safe = check_prompt(logger, display_text, api_key)
    if not is_safe:
        error_message = "提示词安全检查未通过或检查过程中发生错误。请检查日志获取详细信息。"
        logger.error(error_message)
        print(f"错误：{error_message}")
        return 1
    logger.info("提示词安全检查通过。")

    # --- 4. 提交任务到 API --- #
    prompt_data = {"prompt": display_text, "mode": mode}
    logger.info(f"准备提交任务到 TTAPI (模式: {mode})...")
    print(f"正在提交任务 (模式: {mode})...")

    submit_result = call_imagine_api(
        logger, prompt_data, api_key,
        hook_url=hook_url,
        notify_id=notify_id
    )

    if submit_result:
        job_id = submit_result
        logger.info(f"任务提交成功，Job ID: {job_id}")
        job_id_for_save = job_id
        # --- 修改元数据保存逻辑 --- #
        # prompt_for_metadata = prompt if prompt else None # 不再需要这个
        # concept_for_metadata 已经在前面设置好了 (如果 concept 为 None 则设为 "temp")
        variation_for_metadata = variation if variation and concept else None # 保持不变
        style_for_metadata = style if style else None # 保持不变
        
        from ..utils.filesystem_utils import write_last_job_id
        write_last_job_id(logger, job_id)
        logger.info(f"已将任务 ID {job_id} 写入 last_job 文件")

        # 写入基本元数据
        save_image_metadata(
            logger, None, job_id_for_save, None, None, None,
            display_text, # 完整的最终提示词
            concept_for_metadata, # 使用已设置好的 concept_for_metadata ("temp" or a real concept)
            variation_for_metadata,
            style_for_metadata,
            None, None, None, # components, seed, original_job_id
            # 移除 prompt_text 参数
        )
        logger.info(f"已将任务 {job_id} 的基本元数据写入数据库")
        # -------------------------- #

        # --- 5. 处理结果 (轮询或 Webhook) --- #
        if not hook_url:
            logger.info("未提供 Webhook URL，将开始轮询结果...")
            print("Polling for result...")
            poll_response = poll_for_result(logger, job_id, api_key)

            if poll_response:
                final_status, api_data = poll_response

                if final_status == "SUCCESS" and isinstance(api_data, dict):
                    image_url_key = 'url' if 'url' in api_data else 'cdnImage'
                    image_url = api_data.get(image_url_key)

                    if image_url:
                        logger.info(f"任务完成，图像 URL: {image_url}")
                        normalized_result = normalize_api_response(logger, api_data)
                        normalized_result['job_id'] = job_id
                        try:
                            all_tasks = load_all_metadata(logger)
                            all_tasks_index = _build_metadata_index(all_tasks)
                            expected_filename = _generate_expected_filename(logger, normalized_result, all_tasks_index)
                        except Exception as e:
                            logger.error(f"为任务 {job_id} 生成期望文件名时出错: {e}，将使用 job_id 作为备用名。")
                            expected_filename = f"{job_id}.png"
                        image_url_for_download = normalized_result.get('url')
                        if image_url_for_download:
                            logger.info("下载图像...")
                            # download_and_save_image 内部也会调用 save_image_metadata
                            # 确保 download_and_save_image 也不传递 prompt_text 参数 (如果它直接调用的话)
                            # (检查 download_and_save_image 的实现，它似乎直接构造元数据字典传递，应该没问题)
                            download_success, saved_path, image_seed = download_and_save_image(
                                logger,
                                image_url_for_download,
                                job_id,
                                normalized_result.get('prompt') or "",
                                expected_filename,
                                normalized_result.get('concept') or concept_for_metadata, # Pass concept info
                                normalized_result.get('variations') or variation_for_metadata,
                                normalized_result.get('global_styles') or style_for_metadata,
                                None, None, None,
                                normalized_result.get('seed')
                            )
                            if download_success:
                                logger.info(f"成功! 图像已保存: {saved_path}")
                                print(f"成功! 图像已保存: {saved_path}")
                                from ..utils.filesystem_utils import write_last_succeed_job_id
                                write_last_succeed_job_id(logger, job_id)
                                return 0
                            else:
                                logger.error("图像下载或保存失败。")
                                print("错误：图像下载或保存失败。")
                                return 1
                        else:
                            logger.error("成功轮询后未能提取图像 URL 用于下载。")
                            print("错误：成功轮询后未能提取图像 URL。")
                            # 更新元数据，移除 prompt_text 参数
                            save_image_metadata(
                                logger, None, job_id, None, None, None,
                                display_text, concept_for_metadata, variation_for_metadata, style_for_metadata,
                                None, normalized_result.get("seed"), None,
                                status="polling_success_no_url_for_download",
                                # 移除 prompt_text
                            )
                            return 1
                    else:
                        logger.error(f"轮询任务结果成功，但未获取到图像 URL。")
                        print(f"错误：轮询任务结果成功，但未获取到图像 URL。")
                        normalized_result = normalize_api_response(logger, api_data or {})
                        # 更新元数据，移除 prompt_text 参数
                        save_image_metadata(
                            logger, None, job_id, None, None, None,
                            display_text, concept_for_metadata, variation_for_metadata, style_for_metadata,
                            None, normalized_result.get("seed"), None,
                            status="polling_success_no_url",
                            # 移除 prompt_text
                        )
                        return 1
                elif final_status == "FAILED":
                    error_message = api_data.get('message', '未知错误') if isinstance(api_data, dict) else '未知错误'
                    logger.error(f"轮询任务结果失败。API 消息: {error_message}")
                    print(f"错误：轮询任务结果失败。API 消息: {error_message}")
                    return 1
                else:
                    logger.error(f"轮询任务结果返回意外状态: {final_status}")
                    print(f"错误：轮询任务结果返回意外状态: {final_status}")
                    return 1
            else:
                logger.error(f"轮询任务 {job_id} 失败或超时。")
                print(f"错误：轮询任务 {job_id} 失败或超时。")
                return 1
        else: # Webhook provided
            logger.info("提供了 Webhook URL，任务将在后台处理。")
            print("提供了 Webhook URL，任务将在后台处理。")
            logger.info(f"任务 {job_id_for_save} 已提交到后台处理，元数据已保存。")
            return 0
    else: # Submit failed
        error_msg = "任务提交失败 (API 调用未返回 Job ID)"
        logger.error(error_msg)
        print(f"错误：{error_msg}")
        return 1
