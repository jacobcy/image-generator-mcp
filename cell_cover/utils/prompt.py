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


def generate_prompt_text(logger, config, concept_key, variation_key=None, global_style_key=None, aspect_ratio="cell_cover", quality="high", version="v6", cref_url=None):
    """生成完整的 Midjourney 提示词文本。

    Args:
        logger: 日志记录器。
        config: 配置字典。
        concept_key: 创意概念的键。
        variation_key: 变体的键 (可选, 单个)。
        global_style_key: 全局风格修饰词的键 (可选, 单个)。
        aspect_ratio: 宽高比设置的键 (默认: cell_cover)。
        quality: 质量设置的键 (默认: high)。
        version: Midjourney 版本的键 (默认: v6)。
        cref_url: 图像参考 URL (可选，仅 v6/v7 支持)。

    Returns:
        dict: 包含生成的提示词和其他相关信息的字典，如果生成失败则返回 None。
    """
    variation_log_str = variation_key if variation_key else 'None'
    style_log_str = global_style_key if global_style_key else 'None'
    logger.info(f"正在生成提示词，概念: {concept_key}, 变体: {variation_log_str}, 全局风格: {style_log_str}")
    print(f"正在生成提示词的步骤...")

    # Initialize result dictionary
    result = {
        "prompt": "",
        "aspect_ratio": None,
        "quality": None,
        "version": None,
        "concept": concept_key,
        "variations": [variation_key] if variation_key else [],
        "global_styles": [global_style_key] if global_style_key else []
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
    prompt_parts = base_prompt.split('--')
    main_description = prompt_parts[0].strip()
    technical_params_from_base = [f"--{p.strip()}" for p in prompt_parts[1:] if p.strip()]
    logger.debug(f"基础描述部分: {main_description}")
    logger.debug(f"基础提示词中的技术参数: {technical_params_from_base}")

    current_prompt_modifiers = []

    if variation_key:
        variations = concept.get("variations", {})
        if variation_key not in variations:
            error_msg = f"错误：在概念 '{concept_key}' 中找不到变体 '{variation_key}'。"
            logger.error(error_msg)
            print(error_msg)
            print(f"由于概念 '{concept_key}' 的变体键无效，提示词生成失败。")
            return None
        else:
            variation_text = variations[variation_key].strip()
            if variation_text:
                current_prompt_modifiers.append(variation_text)
                logger.debug(f"添加概念变体描述 '{variation_key}': {variation_text}")

    if global_style_key:
        global_styles = config.get("global_styles", {})
        if global_style_key not in global_styles:
            error_msg = f"错误：找不到全局风格 '{global_style_key}'。请检查 prompts_config.json 中的 global_styles 定义。"
            logger.error(error_msg)
            print(error_msg)
            print(f"由于全局风格键无效，提示词生成失败。")
            return None
        else:
            style_text = global_styles[global_style_key].strip()
            if style_text:
                 current_prompt_modifiers.append(style_text)
                 logger.debug(f"添加全局风格描述 '{global_style_key}': {style_text}")

    # Combine description and modifiers
    full_description = main_description.strip()
    if current_prompt_modifiers:
        modifier_string = ", ".join(filter(None, current_prompt_modifiers))
        if full_description:
            full_description += ", " + modifier_string
        else:
            full_description = modifier_string

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
        version_value_str = f"--v {version.replace('v', '')}"
        final_technical_params.append(version_value_str)
        result["version"] = version.replace('v', '')
        logger.debug(f"使用默认版本设置: {version_value_str}")

    # If cref_url is provided, add it
    if cref_url:
        final_technical_params.append(f"--cref {cref_url}")
        logger.debug(f"添加图像参考 URL: {cref_url}")

    # Combine description, base technical params (if any), and final technical params
    combined_parts = [full_description.strip()] + technical_params_from_base + final_technical_params
    result["prompt"] = " ".join(filter(None, combined_parts)).strip()
    logger.info(f"最终生成的提示词: {result['prompt']}")
    logger.info(f"提示词生成成功，长度: {len(result['prompt'])}")

    return result

def save_text_prompt(logger, output_dir, prompt_text, concept_key, variation_key=None):
    """保存生成的文本提示词到指定目录

    Args:
        logger: The logging object.
        output_dir: The directory to save the prompt file in.
        prompt_text: The prompt string to save.
        concept_key: Key of the concept.
        variation_key: Single variation key (optional).
    """
    variation_log_str = variation_key if variation_key else 'None'
    logger.info(f"正在保存提示词文本，概念: {concept_key}, 变体: {variation_log_str}")

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logger.info(f"创建目录: {output_dir}")
        except OSError as e:
            logger.error(f"错误：无法创建输出目录 {output_dir} - {e}")
            print(f"错误：无法创建输出目录 {output_dir} - {e}")
            return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    variation_str = f"_{variation_key}" if variation_key else ""
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
    """将文本复制到剪贴板"""
    if not PYPERCLIP_AVAILABLE:
        logger.warning("Pyperclip 模块不可用，无法复制到剪贴板。")
        print("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
        return False

    try:
        pyperclip.copy(text)
        logger.info("文本已复制到剪贴板。")
        print("文本已复制到剪贴板。")
        return True
    except Exception as e:
        logger.error(f"复制到剪贴板时发生错误: {e}", exc_info=True)
        print(f"错误：无法复制到剪贴板 - {e}")
        return False