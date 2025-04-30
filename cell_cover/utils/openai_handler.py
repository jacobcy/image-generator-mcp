# -*- coding: utf-8 -*-
import logging
import json
import os
from typing import Optional, Dict, Any
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

def get_log_func(logger_obj, level="info"):
    """统一日志记录函数生成，避免重复的 if-else 检查"""
    if not logger_obj:
        return print
    
    if level == "error":
        return logger_obj.error
    elif level == "warning":
        return logger_obj.warning
    elif level == "debug":
        return logger_obj.debug
    else:
        return logger_obj.info

def _optimize_prompt(prompt_text: str, concept_key: Optional[str] = None, logger_obj=None) -> Dict[str, Any]:
    """
    调用OpenAI API来优化提示词文本，并生成完整的概念结构
    
    Args:
        prompt_text: 用户提供的基础文本
        concept_key: 概念键名（可选）
        logger_obj: 可选的日志记录器
        
    Returns:
        一个字典，包含优化后的概念结构，如果出错则包含 'error' 键。
    """
    log_func_info = get_log_func(logger_obj, "info")
    log_func_warn = get_log_func(logger_obj, "warning")
    log_func_error = get_log_func(logger_obj, "error")

    if not OPENAI_AVAILABLE:
        error_message = "错误：OpenAI API不可用，请安装openai模块并配置OPENAI_API_KEY"
        log_func_error(error_message)
        return {"error": error_message}
    
    try:
        meta_prompt = f"""
你是一位富有创意的艺术家，擅长Midjourney提示词撰写。你的任务是根据以下提示创作高质量的视觉描述，确保提示词聚焦一个清晰的焦点点，并参考艺术性示例，如'energetic KTV party with dramatic lighting and emotional connection'，强调构图、灯光和情感深度。

用户输入提示：
```
{prompt_text}
```

生成一个完整的JSON结构，包括：
1. 一个有意义的名称（可使用中文，仅简要）。
2. 一个简单的中文描述，仅概述概念的视觉内容和情感（保持简短）。
3. 一个高质量的Midjourney提示词，使用英文关键词和短语，构建围绕核心焦点的视觉故事，例如：'vibrant KTV scene, friends circled around singer with neon highlights, capturing joy and dynamic energy'。确保简洁，只包含3-5个关键元素，并融入情感深度如'candid laughter'或'cinematic composition'。
4. 1-2个变体提示，每个变体微调焦点，如增强灯光效果。

JSON格式必须精确：

```json
{{
  "name": "有意义的概念名称（中文，简要）",
  "description": "简单中文概述",
  "midjourney_prompt": "英文关键词，富有创意和焦点，例如 'neon-glow KTV circle, passionate singing at center with vivid highlights'",
  "variations": {{
    "variation1_name": "变体1关键词，例如 'intensified emotional vibe'",
    "variation2_name": "变体2关键词，例如 'dramatic light dynamics'"
  }}
}}

注意：
1. Midjourney提示词必须是英文，专注于连贯的视觉艺术故事，如示例。
2. 不要包括Midjourney参数。
3. 示例：如果输入是'安静的森林'，则prompt应是'mysterious dawn forest, soft light on central trees, serene tranquility with subtle fog'。
4. 确保输出是有效的JSON对象。
        """
        
        log_func_info(f"正在调用 OpenAI API...")
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",  # 或其他合适的模型
            messages=[
                {"role": "system", "content": "你是一个专业的Midjourney提示词优化助手，擅长将简单概念转化为详细的视觉提示词和变体。你精通中英双语。"},
                {"role": "user", "content": meta_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if content is not None:
            result = json.loads(content)
        else:
            log_func_error("错误：OpenAI API 返回了空的响应内容。")
            raise ValueError("API response content is None")
        log_func_info("OpenAI API 响应解析成功。")
        
        # 验证返回的JSON结构
        required_keys = ["name", "description", "midjourney_prompt", "variations"]
        if not all(key in result for key in required_keys):
            missing_keys = [key for key in required_keys if key not in result]
            log_func_warn(f"警告：API返回的JSON缺少必要字段: {missing_keys}")
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
        
        return result
        
    except Exception as e:
        error_message = f"调用OpenAI API时出错: {str(e)}"
        log_func_error(error_message)
        return {"error": error_message}

def _optimize_sd_prompt(prompt_text: str, concept_key: Optional[str] = None, weight: float = 1.2, logger_obj=None) -> Dict[str, Any]:
    """
    调用OpenAI API来生成Stable Diffusion风格的加权提示词，并包括否定提示词
    
    Args:
        prompt_text: 用户提供的基础文本
        concept_key: 概念键名（可选）
        weight: 关键元素的权重值（默认1.2）
        logger_obj: 可选的日志记录器
        
    Returns:
        一个字典，包含优化后的SD概念结构，包括负面提示词，如果出错则包含 'error' 键。
    """
    log_func_info = get_log_func(logger_obj, "info")
    log_func_warn = get_log_func(logger_obj, "warning")
    log_func_error = get_log_func(logger_obj, "error")

    if not OPENAI_AVAILABLE:
        error_message = "错误：OpenAI API不可用，请安装openai模块并配置OPENAI_API_KEY"
        log_func_error(error_message)
        return {"error": error_message}
    
    try:
        weight_str = f"{weight:.1f}"
        meta_prompt = f"""
你是一位Stable Diffusion提示词专家，擅长创建精确的加权提示词。你的任务是为用户输入创建高质量的SD提示词，强调关键元素并使用加权语法(元素:权重)。同时，提供一个简洁的否定提示词，专注于避免不想要的元素，如模糊或畸形。

用户输入提示：
```
{prompt_text}
```

生成一个完整的JSON结构，包括：
1. 一个简洁的中文名称。
2. 一个简短的中文描述，概述视觉内容。
3. 一个Stable Diffusion格式的提示词，必须使用英文，并包含加权语法，如 '(主题元素:{weight_str})'。
4. 一个否定提示词，使用英文，简洁地指定需要避免的元素。
5. 1-2个变体提示词，每个使用不同的加权组合或元素强调。

JSON格式必须精确：

```json
{{
  "name": "加权场景名称（中文，简洁）",
  "description": "简短中文描述",
  "sd_prompt": "加权格式英文提示词，如 '(main element:{weight_str}), secondary elements'",
  "negative_prompt": "英文否定提示词，例如 'blurry, deformed, extra limbs'",
  "variations": {{
    "variation1_name": "变体1加权提示词"
  }}
}}

注意：
1. SD提示词必须使用英文，并正确使用加权语法。
2. 主要元素应使用权重 {weight_str}。
3. 否定提示词应简洁，避免正面描述。
4. 确保输出是有效的JSON对象。
        """
        
        log_func_info(f"正在调用 OpenAI API 生成Stable Diffusion加权提示词...")
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "你是一个专业的Stable Diffusion提示词专家，擅长创建具有加权语法的详细提示词，精通中英双语。"},
                {"role": "user", "content": meta_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if content is None:
            log_func_error("错误：OpenAI API 返回了空的响应内容。")
            raise ValueError("API response content is None")
        
        result = json.loads(content)
        log_func_info("OpenAI API 响应解析成功。")
        
        required_keys = ["name", "description", "sd_prompt", "negative_prompt", "variations"]
        if not all(key in result for key in required_keys):
            missing_keys = [key for key in required_keys if key not in result]
            log_func_warn(f"警告：API返回的JSON缺少必要字段: {missing_keys}")
            for key in missing_keys:
                if key == "name":
                    result["name"] = f"SD Generated: {concept_key}" if concept_key else "SD Generated Concept"
                elif key == "description":
                    result["description"] = f"Generated from prompt: {prompt_text[:50]}..."
                elif key == "sd_prompt":
                    result["sd_prompt"] = f"({prompt_text}:{weight_str})"
                elif key == "negative_prompt":
                    result["negative_prompt"] = "blurry, deformed, extra limbs"  # 默认否定提示词
                elif key == "variations":
                    result["variations"] = {}
        
        return result
    
    except Exception as e:
        error_message = f"调用OpenAI API时出错: {str(e)}"
        log_func_error(error_message)
        return {"error": error_message} 