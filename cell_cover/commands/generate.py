# -*- coding: utf-8 -*-
import logging
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import re

# 导入OpenAI API
try:
    import openai
    OPENAI_AVAILABLE = True
    # 配置OpenAI客户端 (现在依赖于 cli.py 中加载的 .env)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        OPENAI_AVAILABLE = False
        logging.warning("未找到OPENAI_API_KEY环境变量，OpenAI功能将不可用")
    else:
        openai.api_key = openai_api_key
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("openai 模块未安装，OpenAI功能将不可用")

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
from ..utils.file_handler import OUTPUT_DIR

logger = logging.getLogger(__name__)

def call_openai_api(prompt_text: str, concept_key: str = None, logger=None) -> Dict[str, Any]:
    """
    调用OpenAI API来优化提示词文本，并生成完整的概念结构
    
    Args:
        prompt_text: 用户提供的基础文本
        concept_key: 概念键名（可选）
        logger: 可选的日志记录器
        
    Returns:
        一个字典，包含优化后的概念结构（name, description, midjourney_prompt, variations）
    """
    if not OPENAI_AVAILABLE:
        log_func = logger.error if logger else print
        log_func("错误：OpenAI API不可用，请安装openai模块并配置OPENAI_API_KEY")
        # 返回一个基本结构，确保后续处理不会出错
        return {
            "name": f"Generated: {concept_key}" if concept_key else "Generated Concept",
            "description": prompt_text,
            "midjourney_prompt": prompt_text,
            "variations": {}
        }
    
    try:
        # 构建元提示词 (完整版)
        meta_prompt = f"""
Please create a complete concept structure for Midjourney image generation based on the following prompt:

```
{prompt_text}
```

I need you to generate a complete JSON structure that includes:

1. A meaningful name for this concept (can be in Chinese)
2. A detailed description in Chinese that explains the concept
3. A high-quality Midjourney prompt in English (using keywords and phrases, not full sentences)
4. 1-2 variations of the main prompt, each with a distinctive focus or style

The format should be exactly as follows:

```json
{{
  "name": "有意义的概念名称（可以使用中文）",
  "description": "详细的中文描述，解释这个概念的视觉内容和目的",
  "midjourney_prompt": "High-quality English keywords for Midjourney, focusing on visual elements, style, lighting, perspective, etc.",
  "variations": {{
    "variation1_name": "additional keywords or style modifiers to create a variation of the main prompt",
    "variation2_name": "different set of keywords or style modifiers for another variation"
  }}
}}
```

Notes:
1. The "midjourney_prompt" should be in English, using comma-separated keywords and phrases ideal for Midjourney. Focus on visual elements, artistic style, camera view, lighting, mood, and specific details.
2. IMPORTANT: Do NOT include ANY Midjourney parameters (like --ar, --v, --q, etc.) in ANY part of your response. These will be added separately by the system.
3. The "description" must be in Chinese and should be detailed and descriptive.
4. The variations should offer meaningful alternatives with different focuses or styles.
5. The variation names should be descriptive of what they emphasize.

Your result must be a valid JSON object matching this exact structure.
        """
        
        # 调用API
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",  # 或其他合适的模型
            messages=[
                {"role": "system", "content": "你是一个专业的Midjourney提示词优化助手，擅长将简单概念转化为详细的视觉提示词和变体。你精通中英双语。"},
                {"role": "user", "content": meta_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # 解析响应
        result = json.loads(response.choices[0].message.content)
        
        # 验证返回的JSON结构
        required_keys = ["name", "description", "midjourney_prompt", "variations"]
        if not all(key in result for key in required_keys):
            missing_keys = [key for key in required_keys if key not in result]
            log_func = logger.warning if logger else print
            log_func(f"警告：API返回的JSON缺少必要字段: {missing_keys}")
            # 补充缺失的字段
            for key in missing_keys:
                if key == "name":
                    result["name"] = f"Generated: {concept_key}" if concept_key else "Generated Concept"
                elif key == "description":
                    result["description"] = f"Generated from prompt: {prompt_text[:50]}..."
                elif key == "midjourney_prompt":
                    result["midjourney_prompt"] = prompt_text
                elif key == "variations":
                    result["variations"] = {}
            
        return result
        
    except Exception as e:
        log_func = logger.error if logger else print
        log_func(f"调用OpenAI API时出错: {str(e)}")
        # 返回一个基本结构，确保后续处理不会出错
        return {
            "name": f"Generated: {concept_key}" if concept_key else "Generated Concept",
            "description": prompt_text,
            "midjourney_prompt": prompt_text,
            "variations": {}
        }

def update_config_with_concept(config_path: str, concept_key: str, concept_data: Dict[str, Any], logger=None) -> bool:
    """
    更新或创建prompts_config.json中的概念
    
    Args:
        config_path: 配置文件路径
        concept_key: 概念键
        concept_data: 包含name, description, midjourney_prompt和variations的字典
        logger: 可选的日志记录器
        
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
            config_data = {"concepts": {}, "global_styles": {}, "aspect_ratios": {}, "quality_settings": {}, "style_versions": {}}
            
        # 确保concepts存在
        if "concepts" not in config_data:
            config_data["concepts"] = {}
            
        # 检查概念是否已存在
        if concept_key in config_data["concepts"]:
            # 更新现有概念的各个字段
            config_data["concepts"][concept_key]["name"] = concept_data.get("name", config_data["concepts"][concept_key]["name"])
            config_data["concepts"][concept_key]["description"] = concept_data.get("description", config_data["concepts"][concept_key]["description"])
            config_data["concepts"][concept_key]["midjourney_prompt"] = concept_data.get("midjourney_prompt", config_data["concepts"][concept_key]["midjourney_prompt"])
            
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
                "midjourney_prompt": concept_data.get("midjourney_prompt", ""),
                "variations": concept_data.get("variations", {})
            }
            action = "已创建"
            
        # 写回文件（保持格式和中文）
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
            
        log_func = logger.info if logger else print
        log_func(f"概念 '{concept_key}' {action}")
        return True
        
    except Exception as e:
        log_func = logger.error if logger else print
        log_func(f"更新配置文件时出错: {str(e)}")
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
):
    """处理 'generate' 命令，使用OpenAI API优化提示词并附加参数。"""
    # 添加调试日志，确认传入的 config
    if logger:
        logger.debug(f"Entering handle_generate. Config type: {type(config)}, Keys: {list(config.keys()) if isinstance(config, dict) else 'N/A'}")
        logger.debug(f"Received prompt: {prompt}, concept: {concept}")

    # 参数检查 (确保 config 和 logger 不是 None)
    if config is None:
        print("FATAL ERROR: Config object is None in handle_generate.")
        # 尝试使用全局 logger 或 print 记录错误
        if logger:
            logger.critical("Config object is None!")
        return 1 # 返回错误码

    if logger is None:
        print("WARNING: Logger object is None in handle_generate.")
        # 可以选择创建一个默认 logger 或继续，但日志会丢失

    log_func = logger.info if logger else print # 确保 log_func 安全

    if not prompt:
        error_log_func = logger.error if logger else print
        error_log_func("错误：使用 'generate' 命令时，必须提供 --prompt 参数。")
        return 1  # 返回错误码
    
    # 1. 通过OpenAI API优化提示词文本和生成完整概念结构
    concept_data = call_openai_api(prompt, concept, logger)
    
    # 去除 midjourney_prompt 中可能已存在的参数
    core_prompt_text = concept_data.get("midjourney_prompt", prompt)
    # 检测并移除 midjourney_prompt 中可能包含的参数
    if core_prompt_text:
        # 移除所有以 "--" 开头的参数及其值
        core_prompt_text = re.sub(r'--\w+\s+[^\s]+', '', core_prompt_text).strip()
        # 确保没有多余的空格
        core_prompt_text = re.sub(r'\s+', ' ', core_prompt_text).strip()
        # 更新回 concept_data
        concept_data["midjourney_prompt"] = core_prompt_text
    
    # 2. 收集并附加参数
    params_to_append = []
    
    # 附加cref（如果提供）
    if cref:
        params_to_append.append(f"--cref {cref}")
    
    # 附加aspect_ratio, quality, version参数 (现在 config 应该有值了)
    aspect_ratios = config.get("aspect_ratios", {})
    quality_settings = config.get("quality_settings", {})
    style_versions = config.get("style_versions", {})
    
    aspect_ratio = aspect_ratios.get(aspect)
    quality_setting = quality_settings.get(quality)
    version_setting = style_versions.get(version)
    
    if aspect_ratio: params_to_append.append(aspect_ratio)
    if quality_setting: params_to_append.append(quality_setting)
    if version_setting: params_to_append.append(version_setting)
    
    # 附加style参数（从global_styles中查找）
    if style:
        global_styles = config.get("global_styles", {})
        # 处理 style: 如果在 global_styles 中找不到，则直接使用 style key 本身
        style_params = [global_styles.get(s, s) for s in style]
        params_to_append.extend(style_params)
    
    # 3. 组合最终提示词（仅用于显示和剪贴板）
    final_prompt = core_prompt_text
    if params_to_append:
        final_prompt += " " + " ".join(params_to_append)
    
    # 处理 variations 中可能存在的参数
    if "variations" in concept_data and isinstance(concept_data["variations"], dict):
        cleaned_variations = {}
        for var_name, var_prompt in concept_data["variations"].items():
            # 清理变体提示词中的参数
            cleaned_var_prompt = re.sub(r'--\w+\s+[^\s]+', '', var_prompt).strip()
            cleaned_var_prompt = re.sub(r'\s+', ' ', cleaned_var_prompt).strip()
            cleaned_variations[var_name] = cleaned_var_prompt
        concept_data["variations"] = cleaned_variations
    
    # 注意：此处不更新 concept_data["midjourney_prompt"]，保持其仅包含核心提示词
    # concept_data 中保存的是不带参数的核心提示词
    # final_prompt 变量用于显示和剪贴板，包含完整提示词（核心+参数）
    
    # 4. 输出最终提示词和概念结构信息
    print(f'''Generated Concept:
Name: {concept_data.get("name", "N/A")}
Description: {concept_data.get("description", "N/A")}

Core Midjourney Prompt (without parameters):
---
{core_prompt_text}
---

Full Midjourney Prompt (with parameters):
---
{final_prompt}
---

Variations: {len(concept_data.get("variations", {}))} variation(s)''')
    
    # 5. 处理剪贴板复制 (复制带参数的完整提示词)
    if clipboard:
        if PYPERCLIP_AVAILABLE:
            copy_to_clipboard(logger, final_prompt)
            log_func("提示词已复制到剪贴板。")
        else:
            warn_log_func = logger.warning if logger else print
            warn_log_func("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
    
    # 6. 处理概念持久化
    if concept:
        # 确定配置文件路径
        config_dir = Path(__file__).parent.parent  # cell_cover目录
        config_path = config_dir / "prompts_config.json"
        
        success = update_config_with_concept(
            str(config_path),
            concept,
            concept_data,  # 保存不带参数的核心提示词
            logger
        )
        
        if not success:
            error_log_func = logger.error if logger else print
            error_log_func(f"无法将提示词保存到概念: {concept}")
    
    # 7. 处理提示词文件保存 (保存带参数的完整提示词)
    if save_prompt:
        # 使用concept键名或时间戳创建文件名
        filename_base = concept if concept else f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_success = save_text_prompt(logger, OUTPUT_DIR, final_prompt, filename_base)
        
        if save_success:
            log_func(f"提示词已保存到文件: {filename_base}.txt")
        else:
            error_log_func = logger.error if logger else print
            error_log_func(f"无法保存提示词文件: {filename_base}.txt")
            return 1  # 失败时返回错误码
    
    return 0  # 成功返回
