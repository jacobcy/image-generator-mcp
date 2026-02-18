# -*- coding: utf-8 -*-
import os
import logging
import uuid
from datetime import datetime
import re
from typing import Optional, Dict, Any

# 从 utils 导入必要的函数
# Use the centralized metadata_manager
from ..utils.metadata_manager import (
    save_image_metadata,
    # find_initial_job_info # Needed if we pre-check concept? - 暂时未使用
)
from ..utils.api import normalize_api_response
from ..utils.api_client import call_imagine_api, poll_for_result, check_prompt
from ..utils.prompt import save_text_prompt, copy_to_clipboard, PYPERCLIP_AVAILABLE
# download_and_save_image now handles saving metadata via metadata_manager
from ..utils.image_handler import download_and_save_image
from ..utils.image_uploader import process_cref_image
# Import file_handler only for directory constants/functions if needed
from ..utils.file_handler import OUTPUT_DIR
from ..utils.image_metadata import load_all_metadata, _build_metadata_index
from ..utils.normalize_metadata import _generate_expected_filename
# Import parameter parsing utilities
from ..utils.param_parser import (
    parse_prompt_parameters, 
    merge_parameters, 
    validate_midjourney_parameters,
    build_midjourney_params_string,
    extract_cli_parameters
)

logger = logging.getLogger(__name__)

def handle_create(
    config: Dict[str, Any],
    logger: logging.Logger,
    api_key: str,
    concept: Optional[str] = None,
    prompt: Optional[str] = None,
    variation: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    style: Optional[str] = None,
    stylize: Optional[int] = None,
    chaos: Optional[int] = None,
    weird: Optional[int] = None,
    seed: Optional[int] = None,
    version: Optional[str] = None,
    quality: Optional[str] = None,
    no: Optional[str] = None,
    tile: bool = False,
    video: bool = False,
    cref: Optional[str] = None,
    cref_weight: Optional[float] = None,
    sref: Optional[str] = None,
    sref_weight: Optional[float] = None,
    clipboard: bool = False,
    save_prompt: bool = False,
    mode: str = 'relax',
    hook_url: Optional[str] = None,
    notify_id: Optional[str] = None,
    skip_prompt_check: bool = False,
    cwd: Optional[str] = None,
    state_dir: Optional[str] = None,
    metadata_dir: Optional[str] = None,
):
    """处理 'create' 命令。"""
    if config is None:
        print("FATAL ERROR: Config object is None in handle_create.")
        if logger:
            logger.critical("Config object is None!")
        return 1

    if logger is None:
        print("WARNING: Logger object is None in handle_create.")

    # 如果未提供metadata_dir，则构造默认路径
    if not metadata_dir:
        if cwd and isinstance(cwd, str):
            metadata_dir = os.path.join(cwd, '.crc', 'metadata')
        else:
            cwd_fallback = os.getcwd()
            metadata_dir = os.path.join(cwd_fallback, '.crc', 'metadata')
        logger.info(f"Constructed metadata_dir: {metadata_dir}")

    # --- 1. 参数解析和合并 ---
    # 从提示词中解析参数
    cleaned_prompt, prompt_params = parse_prompt_parameters(prompt or "")
    
    # 提取 CLI 参数（去除 None 值）
    cli_params = extract_cli_parameters(
        aspect_ratio=aspect_ratio,
        style=style,
        stylize=stylize,
        chaos=chaos,
        weird=weird,
        seed=seed,
        version=version,
        quality=quality,
        no=no,
        tile=tile,
        video=video,
        cref=cref,
        cref_weight=cref_weight,
        sref=sref,
        sref_weight=sref_weight
    )
    
    # 合并参数：CLI 参数优先
    merged_params = merge_parameters(cli_params, prompt_params)
    
    # 验证参数
    is_valid, validation_errors = validate_midjourney_parameters(merged_params)
    if not is_valid:
        for error in validation_errors:
            logger.error(f"参数验证错误: {error}")
            print(f"错误: {error}")
        return 1
    
    # --- 2. 处理参考图片 (Cref/Sref) ---
    cref_url = None
    sref_url = None
    
    # 处理字符参考图像
    cref_to_process = merged_params.get('cref') or cref
    if cref_to_process:
        cref_url = process_cref_image(logger, cref_to_process)
        if not cref_url:
            return 1
        else:
            logger.info(f"使用处理后的 Cref URL: {cref_url}")
            merged_params['cref'] = cref_url
    
    # 处理风格参考图像
    sref_to_process = merged_params.get('sref') or sref
    if sref_to_process:
        sref_url = process_cref_image(logger, sref_to_process)
        if not sref_url:
            return 1
        else:
            logger.info(f"使用处理后的 Sref URL: {sref_url}")
            merged_params['sref'] = sref_url

    # --- 3. 生成提示词 --- #
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
        # 从概念提示词中移除参数，只保留描述性文本
        concept_prompt = re.sub(r'--\w+(?:\s+[^\s--]+)?', '', concept_prompt).strip()
        base_prompt = re.sub(r'\s+', ' ', concept_prompt).strip()
        concept_key_for_save = concept
        concept_for_metadata = concept # 记录使用的概念
        logger.info(f"从概念 '{concept}' 加载核心提示词。")
    else:
        concept_for_metadata = "temp" # 如果没有指定 concept，元数据中记录为 "temp"
        logger.info("未指定 --concept，元数据中的概念将记录为 'temp'。")

    # 添加清理后的用户提示词
    if cleaned_prompt:
        if base_prompt:
            base_prompt += " " + cleaned_prompt
            logger.info(f"将清理后的用户 --prompt 追加到概念提示词。")
        else:
            base_prompt = cleaned_prompt
            logger.info(f"使用清理后的用户 --prompt 作为基础提示词。")

    if not base_prompt:
        logger.error("错误：必须提供 --concept 或 --prompt 才能生成提示词。")
        print("错误：必须提供 --concept 或 --prompt 才能生成提示词。")
        return 1

    # 处理变体（如果指定了概念且没有全局样式）
    if variation and concept and not merged_params.get('style'):
        if concept in config.get("concepts", {}):
             variations = config["concepts"][concept].get("variations", {})
             variation_text = variations.get(variation)
             if variation_text:
                 # 从变体文本中移除参数，只保留描述性文本
                 cleaned_variation_text = re.sub(r'--\w+(?:\s+[^\s--]+)?', '', variation_text).strip()
                 cleaned_variation_text = re.sub(r'\s+', ' ', cleaned_variation_text).strip()
                 base_prompt += " " + cleaned_variation_text
                 logger.info(f"应用了概念 '{concept}' 的变体: {variation}")
             else:
                 logger.warning(f"警告：在概念 '{concept}' 中未找到变体 '{variation}'")
                 print(f"警告：在概念 '{concept}' 中未找到变体 '{variation}'")

    # --- 4. 设置默认参数 ---
    # 如果参数未指定，使用 param_parser.py 中的默认值
    if not merged_params.get('aspect_ratio'):
        merged_params['aspect_ratio'] = '16:9'  # 使用默认比例
        logger.info("使用默认纵横比: 16:9")
    
    if not merged_params.get('quality'):
        merged_params['quality'] = '1'  # 使用默认质量
        logger.info("使用默认质量: 1")
    
    if not merged_params.get('version'):
        merged_params['version'] = '6.1'  # 使用默认版本
        logger.info("使用默认版本: 6.1")

    # --- 5. 构建最终提示词 ---
    midjourney_params = build_midjourney_params_string(merged_params)
    prompt_text = base_prompt
    if midjourney_params:
        prompt_text += " " + midjourney_params

    # 去除多余空格
    prompt_text = re.sub(r'\s+', ' ', prompt_text).strip()

    # --- 6. 兼容性检查 ---
    # 检查版本与 cref 的兼容性
    if cref_url and merged_params.get('version'):
        version_str = str(merged_params.get('version')).lower()
        if 'v6' not in version_str and 'v7' not in version_str:
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
    if skip_prompt_check:
        logger.info("跳过提示词安全检查（用户指定 --skip-prompt-check）")
        print("警告：已跳过提示词安全检查。")
    else:
        logger.info("正在检查提示词安全性...")
        is_safe = check_prompt(logger, display_text, api_key)
        if not is_safe:
            error_message = "提示词安全检查未通过或检查过程中发生错误。请检查日志获取详细信息。"
            logger.error(error_message)
            print(f"错误：{error_message}")
            print("提示：如果 API 暂时无法访问，您可以使用 --skip-prompt-check 选项跳过检查。")
            return 1
        logger.info("提示词安全检查通过。")

    # --- 4. 提交任务到 API --- #
    prompt_data = {"prompt": display_text, "model": mode}  # 修复: 使用 "model" 而不是 "mode"
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
        write_last_job_id(logger, job_id, state_dir)
        logger.info(f"已将任务 ID {job_id} 写入 last_job 文件")

        # 保存任务的基本元数据
        save_image_metadata(
            logger=logger,
            image_id=str(uuid.uuid4()),
            job_id=job_id_for_save,
            filename=None,
            filepath=None,
            url=None,
            prompt=display_text,
            concept=concept_for_metadata,
            metadata_dir=metadata_dir,
            variations=variation_for_metadata,
            global_styles=style_for_metadata,
            components=None,
            seed=None,
            original_job_id=None,
            action_code=None,
            status="submitted"
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
                            all_tasks = load_all_metadata(logger, metadata_dir)
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
                            # Ensure variations and styles are lists or None
                            variations_param = normalized_result.get('variations')
                            if variations_param is None and variation_for_metadata:
                                variations_param = [variation_for_metadata] if isinstance(variation_for_metadata, str) else variation_for_metadata

                            styles_param = normalized_result.get('global_styles')
                            if styles_param is None and style_for_metadata:
                                styles_param = [style_for_metadata] if isinstance(style_for_metadata, str) else style_for_metadata

                            download_success, saved_path, _ = download_and_save_image(
                                logger,
                                image_url_for_download,
                                job_id,
                                normalized_result.get('prompt') or "",
                                expected_filename,
                                normalized_result.get('concept') or concept_for_metadata, # Pass concept info
                                variations_param,
                                styles_param,
                                None, None, None,
                                normalized_result.get('seed')
                            )
                            if download_success:
                                logger.info(f"成功! 图像已保存: {saved_path}")
                                print(f"成功! 图像已保存: {saved_path}")
                                from ..utils.filesystem_utils import write_last_succeed_job_id
                                write_last_succeed_job_id(logger, job_id, state_dir)
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
                                logger=logger,
                                image_id=str(uuid.uuid4()),
                                job_id=job_id,
                                filename=None,
                                filepath=None,
                                url=None,
                                prompt=display_text,
                                concept=concept_for_metadata,
                                metadata_dir=metadata_dir,
                                variations=variation_for_metadata,
                                global_styles=style_for_metadata,
                                components=None,
                                seed=normalized_result.get("seed"),
                                original_job_id=None,
                                action_code=None,
                                status="polling_success_no_url_for_download"
                            )
                            return 1
                    else:
                        logger.error(f"轮询任务结果成功，但未获取到图像 URL。")
                        print(f"错误：轮询任务结果成功，但未获取到图像 URL。")
                        normalized_result = normalize_api_response(logger, api_data or {})
                        # 更新元数据，移除 prompt_text 参数
                        save_image_metadata(
                            logger=logger,
                            image_id=str(uuid.uuid4()),
                            job_id=job_id,
                            filename=None,
                            filepath=None,
                            url=None,
                            prompt=display_text,
                            concept=concept_for_metadata,
                            metadata_dir=metadata_dir,
                            variations=variation_for_metadata,
                            global_styles=style_for_metadata,
                            components=None,
                            seed=normalized_result.get("seed"),
                            original_job_id=None,
                            action_code=None,
                            status="polling_success_no_url"
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
