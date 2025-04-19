# -*- coding: utf-8 -*-
import logging
from datetime import datetime

# 尝试导入 pyperclip
try:
    import importlib.util
    PYPERCLIP_AVAILABLE = importlib.util.find_spec("pyperclip") is not None
    if PYPERCLIP_AVAILABLE:
        import pyperclip
except ImportError:
    PYPERCLIP_AVAILABLE = False

# 从 utils 导入必要的函数
from ..utils.prompt import generate_prompt_text, save_text_prompt, copy_to_clipboard

logger = logging.getLogger(__name__)

def handle_generate(args, config, logger):
    """处理 'generate' 命令，仅生成提示词。"""
    prompt_text = None
    concept_key_for_save = None

    if args.concept:
        # 假设 generate_prompt_text 返回文本或 None
        prompt_text = generate_prompt_text(
            logger,          # Correct arg 1
            config,          # Correct arg 2
            args.concept,    # Correct arg 3
            args.variation,  # Correct arg 4: variation_keys
            args.style,      # Correct arg 5: global_style_keys
            args.aspect,     # Correct arg 6: aspect_ratio
            args.quality,    # Correct arg 7: quality
            args.version     # Correct arg 8: version
            # cref is not used in generate command
        )
        concept_key_for_save = args.concept # Store concept key for saving filename
    elif args.prompt:
        # Directly use the provided prompt
        prompt_text = args.prompt
        # Basic parameter appending (could be moved to a util function)
        params_to_append = []
        aspect_ratio = config.get("aspect_ratios", {}).get(args.aspect)
        quality = config.get("quality_settings", {}).get(args.quality)
        version = config.get("midjourney_versions", {}).get(args.version)
        if aspect_ratio: params_to_append.append(aspect_ratio)
        if quality: params_to_append.append(quality)
        if version: params_to_append.append(version)
        if args.style:
            # Ensure config lookup for styles happens correctly
            style_params = [config.get("global_styles", {}).get(s, s) for s in args.style]
            params_to_append.extend(style_params)

        if params_to_append:
             prompt_text += " " + " ".join(params_to_append)
    else:
        # Use logger if available, otherwise print
        log_func = logger.error if logger else print
        log_func("错误：使用 'generate' 命令时，必须提供 --concept 或 --prompt 参数。")
        return 1 # Return exit code 1

    if not prompt_text:
        # Use logger if available, otherwise print
        log_func = logger.error if logger else print
        log_func("错误：无法生成提示词文本。")
        return 1 # Return exit code 1

    # logger.info(f"生成的提示词:\\n---\\n{prompt_text}\\n---")
    print(f'''Generated Prompt:
---
{prompt_text}
---''')

    if args.clipboard:
        if PYPERCLIP_AVAILABLE:
            copy_to_clipboard(prompt_text)
            logger.info("提示词已复制到剪贴板。")
        else:
            # Use logger if available, otherwise print
            log_func = logger.warning if logger else print
            log_func("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
    if args.save_prompt:
        # Use concept key if available, otherwise generate a filename
        filename_base = concept_key_for_save if concept_key_for_save else f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_success = save_text_prompt(prompt_text, filename_base)
        if save_success:
            logger.info(f"提示词已保存到文件: {filename_base}.txt")
        else:
            logger.error(f"无法保存提示词文件: {filename_base}.txt")
            return 1 # Indicate failure if saving failed

    return 0 # Success
