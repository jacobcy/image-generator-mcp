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

def _optimize_prompt(prompt_text: str, concept_key: str = None, logger_obj=None) -> Dict[str, Any]:
    """
    调用OpenAI API来优化提示词文本，并生成完整的概念结构
    
    Args:
        prompt_text: 用户提供的基础文本
        concept_key: 概念键名（可选）
        logger_obj: 可选的日志记录器
        
    Returns:
        一个字典，包含优化后的概念结构（name, description, midjourney_prompt, variations）
    """
    # 如果OpenAI不可用，直接返回基本结构
    if not OPENAI_AVAILABLE:
        log_func = get_log_func(logger_obj, "error")
        log_func("错误：OpenAI API不可用，请安装openai模块并配置OPENAI_API_KEY")
        return {
            "name": f"Generated: {concept_key}" if concept_key else "Generated Concept",
            "description": prompt_text,
            "midjourney_prompt": prompt_text,
            "variations": {}
        }
    
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
3. 示例：如果输入是'安静的森林'，则midjourney_prompt应是'mysterious dawn forest, soft light on central trees, serene tranquility with subtle fog'。
4. 确保输出是有效的JSON对象。\n        """
        
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
            log_func = get_log_func(logger_obj, "warning")
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
        log_func = get_log_func(logger_obj, "error")
        log_func(f"调用OpenAI API时出错: {str(e)}")
        # 返回一个基本结构，确保后续处理不会出错
        return {
            "name": f"Generated: {concept_key}" if concept_key else "Generated Concept",
            "description": prompt_text,
            "midjourney_prompt": prompt_text,
            "variations": {}
        }

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

def _get_params_from_config(config: Dict[str, Any], aspect: str, quality: str, 
                           version: str, style: Optional[List[str]], cref: Optional[str]) -> List[str]:
    """从配置中收集参数"""
    params = []
    
    # 附加cref（如果提供）
    if cref:
        params.append(f"--cref {cref}")
    
    # 附加aspect_ratio, quality, version参数
    aspect_ratios = config.get("aspect_ratios", {})
    quality_settings = config.get("quality_settings", {})
    style_versions = config.get("style_versions", {})
    
    aspect_ratio = aspect_ratios.get(aspect)
    quality_setting = quality_settings.get(quality)
    version_setting = style_versions.get(version)
    
    if aspect_ratio: params.append(aspect_ratio)
    if quality_setting: params.append(quality_setting)
    if version_setting: params.append(version_setting)
    
    # 附加style参数（从global_styles中查找）
    if style:
        global_styles = config.get("global_styles", {})
        # 处理 style: 如果在 global_styles 中找不到，则直接使用 style key 本身
        style_params = [global_styles.get(s, s) for s in style]
        params.extend(style_params)
    
    return params

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
            
        log_func = get_log_func(logger_obj)
        log_func(f"概念 '{concept_key}' {action}")
        return True
        
    except Exception as e:
        log_func = get_log_func(logger_obj, "error")
        log_func(f"更新配置文件时出错: {str(e)}")
        return False

def _save_prompt_to_file(logger_obj, output_dir: str, prompt: str, concept: Optional[str]) -> bool:
    """保存提示词到文件"""
    if not output_dir:
        output_dir = OUTPUT_DIR
    
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
    output_dir: Optional[str] = None
):
    """处理 'generate' 命令，使用OpenAI API优化提示词并附加参数。"""
    # 简化参数检查
    if config is None:
        print("错误: 配置对象为空")
        return 1
    
    if not prompt:
        error_log = get_log_func(logger, "error")
        error_log("错误：使用 'generate' 命令时，必须提供 --prompt 参数。")
        return 1
    
    # 1. 优化提示词
    concept_data = _optimize_prompt(prompt, concept, logger)
    
    # 2. 清理提示词中的参数
    core_prompt_text = _clean_midjourney_params(concept_data.get("midjourney_prompt", prompt))
    concept_data["midjourney_prompt"] = core_prompt_text
    
    # 3. 收集参数并构建完整提示词
    params = _get_params_from_config(config, aspect, quality, version, style, cref)
    final_prompt = _build_final_prompt(core_prompt_text, params)
    
    # 4. 清理变体提示词
    concept_data["variations"] = _clean_variations(concept_data.get("variations", {}))
    
    # 5. 输出结果
    print(f'''生成的概念:
名称: {concept_data.get("name", "N/A")}
描述: {concept_data.get("description", "N/A")}

核心Midjourney提示词（不含参数）:
---
{core_prompt_text}
---

完整Midjourney提示词（含参数）:
---
{final_prompt}
---

变体数量: {len(concept_data.get("variations", {}))}个''')
    
    # 6. 处理剪贴板复制
    if clipboard and PYPERCLIP_AVAILABLE:
        copy_to_clipboard(logger, final_prompt)
        info_log = get_log_func(logger)
        info_log("提示词已复制到剪贴板。")
    elif clipboard:
        warn_log = get_log_func(logger, "warning")
        warn_log("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
    
    # 7. 持久化概念（如果提供）
    if concept:
        config_dir = Path(__file__).parent.parent  # cell_cover目录
        config_path = config_dir / "prompts_config.json"
        
        if not update_config_with_concept(str(config_path), concept, concept_data, logger):
            error_log = get_log_func(logger, "error")
            error_log(f"无法将提示词保存到概念: {concept}")
    
    # 8. 保存提示词到文件
    if save_prompt:
        if not _save_prompt_to_file(logger, output_dir, final_prompt, concept):
            return 1
    
    return 0  # 成功返回
