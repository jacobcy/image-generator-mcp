# -*- coding: utf-8 -*-
import logging
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import re

# 尝试导入 pyperclip
try:
    import importlib.util
    PYPERCLIP_AVAILABLE = importlib.util.find_spec("pyperclip") is not None
    if PYPERCLIP_AVAILABLE:
        import pyperclip
except ImportError:
    PYPERCLIP_AVAILABLE = False

# 从 utils 导入必要的函数
from ..utils.prompt import save_text_prompt, copy_to_clipboard
# 导入 OpenAI 处理函数
from ..utils.openai_handler import _optimize_prompt, _optimize_sd_prompt, get_log_func
# 导入参数处理工具
from ..utils.param_parser import build_midjourney_params_string

logger = logging.getLogger(__name__)

def _clean_midjourney_params(text: str) -> str:
    """清理文本中可能包含的Midjourney参数"""
    if not text:
        return ""
    # 移除所有以 "--" 开头的参数及其值
    cleaned = re.sub(r'--\w+\s+[^\s]+', '', text).strip()
    # 确保没有多余的空格
    return re.sub(r'\s+', ' ', cleaned).strip()

def _build_final_prompt(core_prompt: str, params: List[str]) -> str:
    """构建最终提示词，包含核心提示词和参数"""
    if not params:
        return core_prompt
    return f"{core_prompt} {' '.join(params)}"

def _get_params_from_parser(aspect: str, quality: str, version: str, 
                           style: Optional[List[str]], cref: Optional[str]) -> str:
    """使用 param_parser 构建参数字符串"""
    params = {}
    
    # 设置基础参数
    if aspect:
        # 将aspect别名转换为实际的纵横比值
        aspect_mapping = {
            'square': '1:1',
            'portrait': '3:4', 
            'landscape': '4:3',
            'cover': '16:9'
        }
        params['aspect_ratio'] = aspect_mapping.get(aspect, aspect)
    
    if quality:
        # 将quality别名转换为实际的质量值
        quality_mapping = {
            'standard': '1',
            'high': '2'
        }
        params['quality'] = quality_mapping.get(quality, quality)
    
    if version:
        # 处理版本参数
        version_mapping = {
            'v5': '5',
            'v6': '6.1', 
            'v7': '7'
        }
        params['version'] = version_mapping.get(version, version)
    
    # 处理cref参数
    if cref:
        params['cref'] = cref
    
    # 注意：style参数在这里不作为Midjourney参数处理，
    # 而是作为global_styles文本追加到提示词中
    
    return build_midjourney_params_string(params)

def _clean_variations(variations: Dict[str, str]) -> Dict[str, str]:
    """清理变体提示词中的参数"""
    if not variations or not isinstance(variations, dict):
        return {}

    cleaned_variations = {}
    for var_name, var_prompt in variations.items():
        cleaned_variations[var_name] = _clean_midjourney_params(var_prompt)
    return cleaned_variations

def update_config_with_concept(config_path: str, concept_key: str, concept_data: Dict[str, Any], logger_obj=None) -> bool:
    """
    更新或创建prompts_config.json中的概念

    Args:
        config_path: 配置文件路径
        concept_key: 概念键
        concept_data: 包含name, description, midjourney_prompt和variations的字典
        logger_obj: 可选的日志记录器

    Returns:
        是否成功更新/创建
    """
    try:
        # 读取现有配置
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        else:
            # 如果文件不存在，创建基本结构
            config_data = {"concepts": {}, "global_styles": {}}

        # 确保concepts存在
        if "concepts" not in config_data:
            config_data["concepts"] = {}

        # 检查概念是否已存在
        if concept_key in config_data["concepts"]:
            # 更新现有概念的各个字段
            config_data["concepts"][concept_key]["name"] = concept_data.get("name", config_data["concepts"][concept_key]["name"])
            config_data["concepts"][concept_key]["description"] = concept_data.get("description", config_data["concepts"][concept_key]["description"])

            # 检查是否有 midjourney_prompt
            if "midjourney_prompt" in concept_data:
                config_data["concepts"][concept_key]["midjourney_prompt"] = concept_data["midjourney_prompt"]
            # 检查是否有 sd_prompt
            elif "sd_prompt" in concept_data:
                config_data["concepts"][concept_key]["sd_prompt"] = concept_data["sd_prompt"]

            # 合并或更新variations
            if "variations" in concept_data and concept_data["variations"]:
                # 如果原有variations为空或不存在，直接设置
                if "variations" not in config_data["concepts"][concept_key] or not config_data["concepts"][concept_key]["variations"]:
                    config_data["concepts"][concept_key]["variations"] = concept_data["variations"]
                else:
                    # 否则合并原有和新的variations
                    config_data["concepts"][concept_key]["variations"].update(concept_data["variations"])

            action = "已更新"
        else:
            # 创建新概念，使用concept_data中的所有数据
            config_data["concepts"][concept_key] = {
                "name": concept_data.get("name", f"Generated: {concept_key}"),
                "description": concept_data.get("description", ""),
            }

            # 检查是否有 midjourney_prompt 或 sd_prompt
            if "midjourney_prompt" in concept_data:
                config_data["concepts"][concept_key]["midjourney_prompt"] = concept_data["midjourney_prompt"]
            elif "sd_prompt" in concept_data:
                config_data["concepts"][concept_key]["sd_prompt"] = concept_data["sd_prompt"]

            config_data["concepts"][concept_key]["variations"] = concept_data.get("variations", {})
            action = "已创建"

        # 写回文件（保持格式和中文）
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        log_func = get_log_func(logger_obj)
        log_func(f"概念 '{concept_key}' {action}")
        return True

    except Exception as e:
        log_func = get_log_func(logger_obj, "error")
        log_func(f"更新配置文件时出错: {str(e)}")
        return False

def _save_prompt_to_file(logger_obj, output_dir: Optional[str], prompt: str, concept: Optional[str]) -> bool:
    """保存提示词到文件"""
    if not output_dir:
        # 保存到当前工作目录的 prompts 子目录，而不是使用 OUTPUT_DIR
        current_dir = os.getcwd()
        output_dir = os.path.join(current_dir, 'prompts')

    # 使用concept键名或时间戳创建文件名
    filename_base = concept if concept else f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    save_success = save_text_prompt(logger_obj, output_dir, prompt, filename_base)

    log_func = get_log_func(logger_obj)
    if save_success:
        log_func(f"提示词已保存到文件: {filename_base}.txt")
        return True
    else:
        error_log = get_log_func(logger_obj, "error")
        error_log(f"无法保存提示词文件: {filename_base}.txt")
        return False

def handle_generate(
    config: Dict[str, Any],
    logger: logging.Logger,
    prompt: Optional[str] = None,
    concept: Optional[str] = None,
    variation: Optional[List[str]] = None,
    style: Optional[List[str]] = None,
    aspect: str = "square",
    quality: str = "high",
    version: str = "v6",
    cref: Optional[str] = None,
    clipboard: bool = False,
    save_prompt: bool = False,
    cwd: Optional[str] = None,
    output_dir: Optional[str] = None,
    sd_flag: bool = False,
    style_degree: Optional[float] = None
):
    """处理 'generate' 命令，使用OpenAI API优化提示词并附加参数。

    Args:
        config: 配置对象
        logger: 日志记录器
        prompt: 用户提供的原始提示词
        concept: 概念的键名（可选）
        variation: 要使用的变体列表（可选）
        style: 要应用的风格列表（可选）
        aspect: 图像比例设置
        quality: 图像质量设置
        version: 风格版本设置
        cref: 参考图像URL（可选）
        clipboard: 是否复制到剪贴板
        save_prompt: 是否保存提示词到文件
        cwd: 当前工作目录
        output_dir: 输出目录
        sd_flag: 是否启用Stable Diffusion模式
        style_degree: 风格强度（可选）
    """
    if config is None:
        print("错误: 配置对象为空")
        return 1

    if not prompt:
        error_log = get_log_func(logger, "error")
        error_log("错误：使用 'generate' 命令时，必须提供 --prompt 参数。")
        return 1

    if variation and not concept:
        error_log = get_log_func(logger, "error")
        error_log("错误：使用 --variation 参数时必须同时指定 --concept 参数。")
        return 1

    if style_degree is not None or sd_flag:
        concept_data = _optimize_sd_prompt(prompt, concept, style_degree or 1.2, logger)

        if 'error' in concept_data:
            print(f"错误: {concept_data['error']}")
            return 1

        # 准备输出，包括容错机制
        core_prompt_text = concept_data.get("sd_prompt", prompt)
        negative_prompt_text = concept_data.get("negative_prompt", "无 (默认值)")
        variations = concept_data.get("variations", {})

        print(
f'''生成的SD加权概念:
名称: {concept_data.get("name", "N/A")}
描述: {concept_data.get("description", "N/A")}

SD提示词:
---
{core_prompt_text}
---

否定提示词:
---
{negative_prompt_text}
---

变体提示词:
---'''
        )
        if variations:
            for var_name, var_prompt in variations.items():
                print(f'{var_name}:\n {var_prompt}\n---')
        else:
            warn_log = get_log_func(logger, "warning")
            warn_log("警告：变体提示词缺失")

        clipboard_text = core_prompt_text  # For SD mode
    else:
        # Midjourney模式
        concept_data = _optimize_prompt(prompt, concept, logger)
        if "error" in concept_data:
            error_log = get_log_func(logger, "error")
            error_log(concept_data["error"])
            return 1

        core_prompt_text = _clean_midjourney_params(concept_data.get("midjourney_prompt", prompt))
        concept_data["midjourney_prompt"] = core_prompt_text
        concept_data["variations"] = _clean_variations(concept_data.get("variations", {}))
        print(
f'''生成的概念:
名称: {concept_data.get("name", "N/A")}
描述: {concept_data.get("description", "N/A")}

核心Midjourney提示词:
---
{core_prompt_text}
---
'''
        )
        if concept_data.get("variations"):
            print("\n变体提示词:")
            for var_name, var_prompt in concept_data.get("variations", {}).items():
                print(f"---\n{var_name}: {var_prompt}\n---")
        
        # 使用 param_parser 构建参数
        param_string = _get_params_from_parser(aspect, quality, version, style, cref)
        
        # 处理 global_styles（如果有）
        style_text = ""
        if style:
            global_styles = config.get("global_styles", {})
            style_parts = [global_styles.get(s, s) for s in style]
            style_text = " " + " ".join(style_parts)
        
        clipboard_text = core_prompt_text + style_text
        if param_string:
            clipboard_text += " " + param_string

    if clipboard and PYPERCLIP_AVAILABLE:
        copy_to_clipboard(logger, clipboard_text)
        info_log = get_log_func(logger)
        info_log("提示词已复制到剪贴板。")
    elif clipboard:
        warn_log = get_log_func(logger, "warning")
        warn_log("警告：Pyperclip 模块不可用，无法复制到剪贴板。")

    if concept and "error" not in concept_data:
        # 保存到用户的 ~/.crc 目录中的配置文件
        # 需要从调用者传入 crc_base_dir 参数
        home_dir = os.path.expanduser("~")
        crc_base_dir = os.path.join(home_dir, '.crc')
        config_path = os.path.join(crc_base_dir, 'prompts_config.json')
        if not update_config_with_concept(config_path, concept, concept_data, logger):
            error_log = get_log_func(logger, "error")
            error_log(f"无法将提示词保存到概念: {concept}")

    if save_prompt and "error" not in locals().get("concept_data", {}):
        save_text = clipboard_text  # Use the prepared text
        if not _save_prompt_to_file(logger, output_dir, save_text, concept):
            return 1

    return 0
