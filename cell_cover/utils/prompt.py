#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prompt Handling Utilities
-------------------------
Functions for generating, saving, and copying Midjourney prompts.
"""

import os
import logging
from datetime import datetime

# Handle optional pyperclip import
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    # Define a dummy pyperclip object if needed, or just check the flag
    class DummyPyperclip:
        def copy(self, text):
            pass # Do nothing
        def paste(self):
            return "" # Return empty
    pyperclip = DummyPyperclip()


def generate_prompt_text(logger, config, concept_key, variation_keys=None, global_style_keys=None, aspect_ratio="cell_cover", quality="high", version="v6", cref_url=None):
    """生成完整的 Midjourney 提示词文本。

    Args:
        logger: 日志记录器。
        config: 配置字典。
        concept_key: 创意概念的键。
        variation_keys: 变体的键列表 (可选)。
        global_style_keys: 全局风格修饰词列表 (可选)。
        aspect_ratio: 宽高比设置的键 (默认: cell_cover)。
        quality: 质量设置的键 (默认: high)。
        version: Midjourney 版本的键 (默认: v6)。
        cref_url: 图像参考 URL (可选，仅 v6 支持)。

    Returns:
        dict: 包含生成的提示词和其他相关信息的字典，如果生成失败则返回 None。
    """
    variation_log_str = '-'.join(variation_keys) if variation_keys else 'None'
    style_log_str = '-'.join(global_style_keys) if global_style_keys else 'None'
    logger.info(f"正在生成提示词，概念: {concept_key}, 变体: {variation_log_str}, 全局风格: {style_log_str}")
    print(f"正在生成提示词的步骤...")

    # Initialize result dictionary
    result = {
    "prompt": "",
    "aspect_ratio": None,
    "quality": None,
    "version": None,
    "concept": concept_key,
    "variations": variation_keys or [],
    "global_styles": global_style_keys or [] # Store applied global styles
    }

    concepts = config.get("concepts", {})
    if concept_key not in concepts:
        error_msg = f"错误：找不到创意概念 '{concept_key}'"
        logger.error(error_msg)
        print(error_msg)
        return None

    concept = concepts[concept_key]
    base_prompt = concept.get("midjourney_prompt", "")
    if not base_prompt:
        error_msg = f"错误：概念 '{concept_key}' 没有定义 'midjourney_prompt'。"
        logger.error(error_msg)
        print(error_msg)
        return None

    # Start building prompt parts
    # Start with the base prompt, remove trailing parameters if they exist in base_prompt itself
    # This is a simple check; might need refinement if base prompts have complex structures
    prompt_parts = base_prompt.split('--')
    main_description = prompt_parts[0].strip()
    technical_params_from_base = [f"--{p.strip()}" for p in prompt_parts[1:] if p.strip()]
    logger.debug(f"基础描述部分: {main_description}")
    logger.debug(f"基础提示词中的技术参数: {technical_params_from_base}")

    current_prompt_modifiers = []

    # --- RESTORING ORIGINAL CODE ---
    # Add concept-specific variation modifiers
    if variation_keys:
        variations = concept.get("variations", {})
        valid_variations = []
        all_valid = True
        for key in variation_keys:
            if key not in variations:
                error_msg = f"错误：在概念 '{concept_key}' 中找不到变体 '{key}'。"
                logger.error(error_msg)
                print(error_msg)
                all_valid = False
            else:
                 valid_variations.append(key)
        if not all_valid:
            print(f"由于概念 '{concept_key}' 的一个或多个变体键无效，提示词生成失败。")
            return None
        for key in valid_variations:
            variation_text = variations[key].strip()
            current_prompt_modifiers.append(variation_text)
            logger.debug(f"添加概念变体描述 '{key}': {variation_text}")
            result["variations"].append(key) # Ensure variations are stored

    # Add global style modifiers
    if global_style_keys:
        global_styles = config.get("global_styles", {})
        valid_global_styles = []
        all_valid = True
        for key in global_style_keys:
            if key not in global_styles:
                error_msg = f"错误：找不到全局风格 '{key}'。请检查 prompts_config.json 中的 global_styles 定义。"
                logger.error(error_msg)
                print(error_msg)
                all_valid = False
            else:
                valid_global_styles.append(key)
                result["global_styles"].append(key) # Store applied global styles
        if not all_valid:
            print(f"由于一个或多个全局风格键无效，提示词生成失败。")
            return None
        for key in valid_global_styles:
            style_text = global_styles[key].strip()
            # Avoid adding empty style text
            if style_text:
                 current_prompt_modifiers.append(style_text)
                 logger.debug(f"添加全局风格描述 '{key}': {style_text}")
    # --- END OF RESTORED CODE SECTION ---

    # Combine description and modifiers
    full_description = main_description.strip() # Ensure no trailing space
    if current_prompt_modifiers:
        # Join modifiers with commas
        modifier_string = ", ".join(filter(None, current_prompt_modifiers))
        # Append modifiers with a comma and space, unless description is empty
        if full_description:
            full_description += ", " + modifier_string
        else:
            full_description = modifier_string # Should not happen if base_prompt is required

    # Add technical parameters (aspect ratio, quality, version)
    final_technical_params = []
    # Aspect Ratio
    aspect_ratios = config.get("aspect_ratios", {})
    if aspect_ratio in aspect_ratios:
        aspect_value_str = aspect_ratios[aspect_ratio]
        final_technical_params.append(aspect_value_str)
        result["aspect_ratio"] = aspect_value_str.replace("--ar ", "")
        logger.debug(f"添加宽高比 '{aspect_ratio}': {aspect_value_str}")
    else:
        warning_msg = f"警告：找不到宽高比设置 '{aspect_ratio}'，将使用默认。"
        logger.warning(warning_msg)
        print(warning_msg)

    # Quality
    quality_settings = config.get("quality_settings", {})
    if quality in quality_settings:
        quality_value_str = quality_settings[quality]
        final_technical_params.append(quality_value_str)
        result["quality"] = quality_value_str.replace("--q ", "")
        logger.debug(f"添加质量设置 '{quality}': {quality_value_str}")
    else:
        warning_msg = f"警告：找不到质量设置 '{quality}'，将使用默认。"
        logger.warning(warning_msg)
        print(warning_msg)

    # Version
    style_versions = config.get("style_versions", {})
    if version in style_versions:
        version_value_str = style_versions[version]
        final_technical_params.append(version_value_str)
        result["version"] = version_value_str.replace("--v ", "")
        logger.debug(f"添加版本设置 '{version}': {version_value_str}")
    else:
        # 如果在 style_versions 中找不到，则直接使用版本号
        version_value_str = f"--v {version.replace('v', '')}"
        final_technical_params.append(version_value_str)
        result["version"] = version.replace('v', '')
        logger.debug(f"使用默认版本设置: {version_value_str}")

    # If cref_url is provided and version is v6 or v7, add it to the prompt
    if cref_url:
        if version in ["v6", "v7"]:
            # 将 cref_url 添加到提示词的开头
            full_description = f"{cref_url} {full_description}"
            logger.debug(f"添加图像参考 URL 到提示词开头: {cref_url}")
        else:
            logger.warning("图像参考 URL (--cref) 仅在 v6 或 v7 版本中支持，将被忽略。")

    # Combine description, base technical params (if any), and final technical params
    combined_parts = [full_description.strip()] + technical_params_from_base + final_technical_params
    result["prompt"] = " ".join(filter(None, combined_parts)).strip()
    logger.info(f"最终生成的提示词: {result['prompt']}")
    logger.info(f"提示词生成成功，长度: {len(result['prompt'])}")

    return result

def save_text_prompt(logger, output_dir, prompt_text, concept_key, variation_keys=None):
    """保存生成的文本提示词到指定目录

    Args:
        logger: The logging object.
        output_dir: The directory to save the prompt file in.
        prompt_text: The prompt string to save.
        concept_key: Key of the concept.
        variation_keys: List of variation keys (optional).
    """
    variation_log_str = '-'.join(variation_keys) if variation_keys else 'None'
    logger.info(f"正在保存提示词文本，概念: {concept_key}, 变体: {variation_log_str}")

    # Ensure output directory exists (moved from ensure_directories)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logger.info(f"创建目录: {output_dir}")
        except OSError as e:
            logger.error(f"错误：无法创建输出目录 {output_dir} - {e}")
            print(f"错误：无法创建输出目录 {output_dir} - {e}")
            return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create filename string from list of variations
    variation_str = f"_{'-'.join(variation_keys)}" if variation_keys else ""
    filename = f"{concept_key}{variation_str}_prompt_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)

    logger.debug(f"保存提示词到文件: {filepath}")

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(prompt_text)
        success_msg = f"提示词文本已保存到: {filepath}"
        logger.info(success_msg)
        print(success_msg)
        return filepath
    except IOError as e:
        error_msg = f"错误：无法保存提示词文本到 {filepath} - {e}"
        logger.error(error_msg)
        print(error_msg)
        return None

def copy_to_clipboard(logger, text):
    """将文本复制到剪贴板

    Args:
        logger: The logging object.
        text: The text to copy.
    """
    logger.debug("尝试复制文本到剪贴板")
    if not PYPERCLIP_AVAILABLE:
        warning_msg = "警告: pyperclip 模块不可用，无法复制到剪贴板。"
        logger.warning(warning_msg)
        print(warning_msg)
        print("请使用 'uv pip install pyperclip' 安装。")
        return False
    try:
        # pyperclip is already imported or a dummy object exists
        pyperclip.copy(text)
        logger.info("文本已成功复制到剪贴板")
        return True
    except Exception as e:
        # Catch potential pyperclip errors
        error_msg = f"无法复制到剪贴板: {e}"
        logger.error(error_msg)
        print(error_msg)
        return False