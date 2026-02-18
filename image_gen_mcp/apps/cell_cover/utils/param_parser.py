# -*- coding: utf-8 -*-
import re
import logging
from typing import Dict, Tuple, Optional, Any

logger = logging.getLogger(__name__)

# Midjourney 参数映射表
MIDJOURNEY_PARAM_MAPPING = {
    'ar': 'aspect_ratio',
    'aspect': 'aspect_ratio',
    's': 'stylize',
    'style': 'style',
    'c': 'chaos',
    'chaos': 'chaos',
    'w': 'weird',
    'weird': 'weird',
    'seed': 'seed',
    'v': 'version',
    'version': 'version',
    'q': 'quality',
    'quality': 'quality',
    'no': 'no',
    'tile': 'tile',
    'video': 'video',
    'cref': 'cref',
    'cw': 'cref_weight',
    'sref': 'sref',
    'sw': 'sref_weight',
    'repeat': 'repeat',
    'stop': 'stop'
}

# 基于项目配置文件的有效参数值
VALID_ASPECT_RATIOS = ['1:1', '3:4', '4:3', '16:9', '9:16', '2:3', '3:2', '4:5', '5:4', '1:2', '2:1']
VALID_VERSIONS = ['5', '6', '6.1', '7', 'v5', 'v6', 'v6.1', 'v7', 'niji', 'niji5', 'niji6']
VALID_QUALITIES = ['1', '2', '0.25', '0.5']  # 项目主要使用1和2，但保留其他常用值
VALID_STYLES = ['raw', 'cute', 'expressive', 'original', 'scenic']

def parse_prompt_parameters(prompt: str) -> Tuple[str, Dict[str, Any]]:
    """
    从提示词中解析 Midjourney 参数
    
    Args:
        prompt: 包含可能的 --参数的提示词
        
    Returns:
        Tuple[str, Dict[str, Any]]: (清理后的提示词, 解析出的参数字典)
    """
    if not prompt:
        return "", {}
    
    extracted_params = {}
    cleaned_prompt = prompt
    
    # 匹配所有 --参数的正则表达式
    # 支持格式：--param value 或 --param
    param_pattern = r'--(\w+)(?:\s+([^\s\-][^\s]*?))?(?=\s|$|--)'
    
    matches = re.findall(param_pattern, prompt)
    
    for param_name, param_value in matches:
        # 标准化参数名
        normalized_param = MIDJOURNEY_PARAM_MAPPING.get(param_name.lower())
        
        if normalized_param:
            # 处理布尔值参数（无值参数）
            if not param_value:
                if param_name.lower() in ['tile', 'video']:
                    extracted_params[normalized_param] = True
                continue
            
            # 处理数值参数
            if normalized_param in ['stylize', 'chaos', 'weird', 'seed', 'cref_weight', 'sref_weight', 'repeat', 'stop']:
                try:
                    if normalized_param in ['cref_weight', 'sref_weight']:
                        extracted_params[normalized_param] = float(param_value)
                    else:
                        extracted_params[normalized_param] = int(param_value)
                except ValueError:
                    logger.warning(f"无效的数值参数: --{param_name} {param_value}")
                    continue
            else:
                # 处理字符串参数
                extracted_params[normalized_param] = param_value
    
    # 从原始提示词中移除所有 --参数
    cleaned_prompt = re.sub(r'--\w+(?:\s+[^\s\-][^\s]*?)?(?=\s|$|--)', '', prompt).strip()
    cleaned_prompt = re.sub(r'\s+', ' ', cleaned_prompt).strip()
    
    logger.debug(f"解析的参数: {extracted_params}")
    logger.debug(f"清理后的提示词: {cleaned_prompt}")
    
    return cleaned_prompt, extracted_params

def merge_parameters(cli_params: Dict[str, Any], prompt_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并命令行参数和提示词参数，CLI 参数优先
    
    Args:
        cli_params: 命令行显式提供的参数
        prompt_params: 从提示词中解析的参数
        
    Returns:
        Dict[str, Any]: 合并后的参数字典
    """
    merged_params = prompt_params.copy()
    
    # CLI 参数覆盖提示词参数
    for key, value in cli_params.items():
        if value is not None:  # 只覆盖非 None 的值
            merged_params[key] = value
            if key in prompt_params:
                logger.info(f"CLI 参数 --{key} 覆盖了提示词中的参数")
    
    logger.debug(f"合并后的参数: {merged_params}")
    return merged_params

def validate_midjourney_parameters(params: Dict[str, Any]) -> Tuple[bool, list]:
    """
    验证 Midjourney 参数的有效性
    
    Args:
        params: 要验证的参数字典
        
    Returns:
        Tuple[bool, list]: (是否所有参数都有效, 错误信息列表)
    """
    errors = []
    
    # 验证纵横比
    if 'aspect_ratio' in params:
        if params['aspect_ratio'] not in VALID_ASPECT_RATIOS:
            errors.append(f"无效的纵横比: {params['aspect_ratio']}。有效值: {', '.join(VALID_ASPECT_RATIOS)}")
    
    # 验证版本 - 统一处理v前缀
    if 'version' in params:
        version = str(params['version']).lower()
        # 移除v前缀进行比较
        version_clean = version.replace('v', '')
        valid_versions_clean = [v.lower().replace('v', '') for v in VALID_VERSIONS]
        
        if version_clean not in valid_versions_clean and version not in [v.lower() for v in VALID_VERSIONS]:
            errors.append(f"无效的版本: {params['version']}。有效值: {', '.join(VALID_VERSIONS)}")
    
    # 验证质量
    if 'quality' in params:
        if str(params['quality']) not in VALID_QUALITIES:
            errors.append(f"无效的质量: {params['quality']}。有效值: {', '.join(VALID_QUALITIES)}")
    
    # 验证风格
    if 'style' in params:
        style = params['style'].lower() if isinstance(params['style'], str) else str(params['style'])
        if style not in [s.lower() for s in VALID_STYLES]:
            logger.warning(f"未知的风格: {params['style']}，将直接使用")
    
    # 验证数值范围
    if 'stylize' in params:
        stylize = params['stylize']
        if not (0 <= stylize <= 1000):
            errors.append(f"stylize 值超出范围 (0-1000): {stylize}")
    
    if 'chaos' in params:
        chaos = params['chaos']
        if not (0 <= chaos <= 100):
            errors.append(f"chaos 值超出范围 (0-100): {chaos}")
    
    if 'weird' in params:
        weird = params['weird']
        if not (0 <= weird <= 3000):
            errors.append(f"weird 值超出范围 (0-3000): {weird}")
    
    if 'cref_weight' in params:
        cw = params['cref_weight']
        if not (0 <= cw <= 100):
            errors.append(f"cref_weight 值超出范围 (0-100): {cw}")
    
    if 'sref_weight' in params:
        sw = params['sref_weight']
        if not (0 <= sw <= 1000):
            errors.append(f"sref_weight 值超出范围 (0-1000): {sw}")
    
    return len(errors) == 0, errors

def build_midjourney_params_string(params: Dict[str, Any]) -> str:
    """
    将参数字典转换为 Midjourney 参数字符串
    
    Args:
        params: 参数字典
        
    Returns:
        str: Midjourney 参数字符串 (例如 "--ar 16:9 --style raw --v 6")
    """
    param_strings = []
    
    # 参数顺序（按重要性排序）
    param_order = [
        'aspect_ratio', 'version', 'quality', 'style', 'stylize', 
        'chaos', 'weird', 'seed', 'cref', 'cref_weight', 'sref', 'sref_weight',
        'no', 'tile', 'video', 'repeat', 'stop'
    ]
    
    # 反向映射：从内部参数名到 Midjourney 参数名
    reverse_mapping = {v: k for k, v in MIDJOURNEY_PARAM_MAPPING.items()}
    
    for param_name in param_order:
        if param_name in params and params[param_name] is not None:
            value = params[param_name]
            
            # 获取 Midjourney 参数名（优先使用短名称）
            mj_param = reverse_mapping.get(param_name, param_name)
            
            # 特殊处理某些参数
            if param_name == 'aspect_ratio':
                mj_param = 'ar'
            elif param_name == 'stylize':
                mj_param = 's'
            elif param_name == 'cref_weight':
                mj_param = 'cw'
            elif param_name == 'sref_weight':
                mj_param = 'sw'
            elif param_name == 'version':
                # 确保版本参数格式正确
                mj_param = 'v'
                # 如果值不包含v前缀，自动添加（除了纯数字版本）
                if isinstance(value, str) and not value.startswith('v') and not value.replace('.', '').isdigit():
                    value = f"v{value}"
            
            # 构建参数字符串
            if isinstance(value, bool) and value:
                param_strings.append(f"--{mj_param}")
            elif not isinstance(value, bool):
                param_strings.append(f"--{mj_param} {value}")
    
    return " ".join(param_strings)

def extract_cli_parameters(**kwargs) -> Dict[str, Any]:
    """
    从 CLI 参数中提取非 None 的参数
    
    Args:
        **kwargs: CLI 参数
        
    Returns:
        Dict[str, Any]: 非 None 的参数字典
    """
    return {k: v for k, v in kwargs.items() if v is not None} 