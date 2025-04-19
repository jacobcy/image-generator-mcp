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


def generate_prompt_text(logger, config, concept_key, variation_keys=None, global_style_keys=None, aspect_ratio="cell_cover", quality="high", version="v6"):
    """生成用于API的Midjourney提示词文本和参数字典

    Args:
        logger: The logging object.
        config: The loaded configuration dictionary.
        concept_key: Key of the concept to use.
        variation_keys: List of concept-specific variation keys (optional).
        global_style_keys: List of global style keys (optional).
        aspect_ratio: Key for aspect ratio setting.
        quality: Key for quality setting.
        version: Key for Midjourney version setting.

    Returns:
        成功时返回字典，包含 prompt 字符串以及解析出的参数值 (variations 是列表)
        失败时返回 None
    """
    variation_log_str = '-'.join(variation_keys) if variation_keys else 'None'
    style_log_str = '-'.join(global_style_keys) if global_style_keys else 'None'
    logger.info(f"正在生成提示词，概念: {concept_key}, 变体: {variation_log_str}, 全局风格: {style_log_str}")

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
    current_prompt_parts = [base_prompt]
    logger.debug(f"基础提示词: {base_prompt}")

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
            variation_text = variations[key]
            current_prompt_parts.append(variation_text)
            logger.debug(f"添加概念变体 '{key}': {variation_text}")

    # Add global style modifiers (before technical params like --ar)
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
        if not all_valid:
            print(f"由于一个或多个全局风格键无效，提示词生成失败。")
            return None
        for key in valid_global_styles:
            style_text = global_styles[key]
            current_prompt_parts.append(style_text)
            logger.debug(f"添加全局风格 '{key}': {style_text}")

    # Add technical parameters (aspect ratio, quality, version)
    # Aspect Ratio
    aspect_ratios = config.get("aspect_ratios", {})
    if aspect_ratio in aspect_ratios:
        aspect_value_str = aspect_ratios[aspect_ratio]
        current_prompt_parts.append(aspect_value_str)
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
        current_prompt_parts.append(quality_value_str)
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
        current_prompt_parts.append(version_value_str)
        result["version"] = version_value_str.replace("--v ", "")
        logger.debug(f"添加版本设置 '{version}': {version_value_str}")
    else:
        warning_msg = f"警告：找不到版本设置 '{version}'，将使用默认。"
        logger.warning(warning_msg)
        print(warning_msg)

    # Combine parts and strip whitespace
    result["prompt"] = " ".join(current_prompt_parts).strip()
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