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


def generate_prompt_text(logger, config, concept_key, variation_keys=None, aspect_ratio="cell_cover", quality="high", version="v6"):
    """生成用于API的Midjourney提示词文本和参数字典

    Args:
        logger: The logging object.
        config: The loaded configuration dictionary.
        concept_key: Key of the concept to use.
        variation_keys: List of variation keys to use (optional).
        aspect_ratio: Key for aspect ratio setting.
        quality: Key for quality setting.
        version: Key for Midjourney version setting.

    Returns:
        成功时返回字典，包含 prompt 字符串以及解析出的参数值 (variations 是列表)
        失败时返回 None
    """
    variation_log_str = '-'.join(variation_keys) if variation_keys else 'None'
    logger.info(f"正在生成提示词，概念: {concept_key}, 变体: {variation_log_str}")

    # Initialize result dictionary
    result = {
        "prompt": "",
        "aspect_ratio": None,
        "quality": None,
        "version": None,
        "concept": concept_key,
        "variations": variation_keys or [] # Store the list
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

    current_prompt_parts = [base_prompt]
    logger.debug(f"基础提示词: {base_prompt}")

    # Add variation modifiers
    if variation_keys:
        variations = concept.get("variations", {})
        valid_variations = []
        # First, check if all provided keys are valid
        all_valid = True
        for key in variation_keys:
            if key not in variations:
                error_msg = f"错误：找不到变体 '{key}' 用于概念 '{concept_key}'。"
                logger.error(error_msg)
                print(error_msg)
                all_valid = False
            else:
                 valid_variations.append(key)

        if not all_valid:
            print("由于一个或多个变体键无效，提示词生成失败。")
            return None

        # If all are valid, append their text
        for key in valid_variations:
            variation_text = variations[key]
            current_prompt_parts.append(variation_text)
            logger.debug(f"添加变体 '{key}': {variation_text}")


    # Add aspect ratio (and store the value)
    aspect_ratios = config.get("aspect_ratios", {})
    if aspect_ratio in aspect_ratios:
        aspect_value_str = aspect_ratios[aspect_ratio] # e.g., "--ar 3:4"
        current_prompt_parts.append(aspect_value_str)
        result["aspect_ratio"] = aspect_value_str.replace("--ar ", "") # Store the value "3:4"
        logger.debug(f"添加宽高比 '{aspect_ratio}': {aspect_value_str}")
    else:
        warning_msg = f"警告：找不到宽高比设置 '{aspect_ratio}'，将使用默认。"
        logger.warning(warning_msg)
        print(warning_msg)

    # Add quality setting (and store the value)
    quality_settings = config.get("quality_settings", {})
    if quality in quality_settings:
        quality_value_str = quality_settings[quality] # e.g., "--q 2"
        current_prompt_parts.append(quality_value_str)
        result["quality"] = quality_value_str.replace("--q ", "") # Store the value "2"
        logger.debug(f"添加质量设置 '{quality}': {quality_value_str}")
    else:
        warning_msg = f"警告：找不到质量设置 '{quality}'，将使用默认。"
        logger.warning(warning_msg)
        print(warning_msg)

    # Add version setting (and store the value)
    style_versions = config.get("style_versions", {})
    if version in style_versions:
        version_value_str = style_versions[version] # e.g., "--v 6"
        current_prompt_parts.append(version_value_str)
        result["version"] = version_value_str.replace("--v ", "") # Store the value "6"
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