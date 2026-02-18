#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cell Cover Generator MCP Server
将 Cell Cover Generator 功能封装为 MCP 工具
"""
import os
import sys
from typing import Optional, List
import json

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fastmcp import FastMCP, Context
from fastmcp.server.stdio import stdio_server
import logging
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

# 导入 Cell Cover Generator 模块
try:
    from cell_cover.utils.config import load_config, get_api_key
    from cell_cover.utils.log import setup_logging
    from cell_cover.commands import (
        create as cmd_create,
        generate as cmd_generate,
        list_cmd as cmd_list,
        view as cmd_view,
        action as cmd_action,
        list_tasks as cmd_list_tasks,
        describe as cmd_describe
    )
    from cell_cover.constants import ACTION_CHOICES
except ImportError as e:
    logging.error(f"无法导入 Cell Cover Generator 模块: {e}")
    logging.error("请确保已安装 cell_cover_generator 包")
    sys.exit(1)

# 初始化 FastMCP 服务器
mcp = FastMCP("Cell Cover Generator MCP Server")

# 配置
GLOBAL_CONFIG_DIR = os.path.join(os.path.expanduser("~"), '.crc')
CRC_BASE_DIR = os.path.join(project_root, '.crc')
LOG_DIR = os.path.join(CRC_BASE_DIR, 'logs')
STATE_DIR = os.path.join(CRC_BASE_DIR, 'state')
METADATA_DIR = os.path.join(CRC_BASE_DIR, 'metadata')
OUTPUT_DIR = os.path.join(CRC_BASE_DIR, 'output')

# 初始化日志
os.makedirs(LOG_DIR, exist_ok=True)
logger = setup_logging(log_dir=LOG_DIR, verbose=False)

# 加载配置
default_config_path = os.path.join(project_root, 'cell_cover', 'prompts_config.json')
user_config_path = os.path.join(GLOBAL_CONFIG_DIR, 'prompts_config.json')
config = load_config(logger, default_config_path, user_config_path)

logger.info("Cell Cover Generator MCP Server 初始化完成")


# ============================================================================
# MCP 工具定义
# ============================================================================

@mcp.tool()
def list_concepts() -> str:
    """列出所有可用的创意概念及其键。

    返回可用创意概念的 JSON 格式列表。
    """
    try:
        output = StringIO()
        with redirect_stdout(output):
            cmd_list.handle_list_concepts(config)

        result = output.getvalue()

        # 尝试解析为 JSON 以获取更结构化的输出
        try:
            return result
        except:
            return f"可用概念:\n{result}"

    except Exception as e:
        logger.error(f"列出概念失败: {e}")
        return f"错误: {str(e)}"


@mcp.tool()
def list_variations(concept_key: str) -> str:
    """列出指定创意概念的所有可用变体。

    Args:
        concept_key: 要查询变体的创意概念键。

    Returns:
        包含该概念所有变体的 JSON 格式字符串。
    """
    try:
        output = StringIO()
        with redirect_stdout(output):
            cmd_list.handle_list_variations(config, concept_key)

        result = output.getvalue()
        return result

    except Exception as e:
        logger.error(f"列出变体失败: {e}")
        return f"错误: {str(e)}"


@mcp.tool()
def create_image(
    prompt: str,
    concept: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    style: Optional[str] = None,
    version: Optional[str] = None,
    mode: str = "relax",
    chaos: Optional[int] = None,
    stylize: Optional[int] = None,
    seed: Optional[int] = None,
    quality: Optional[str] = None
) -> str:
    """创建新的 Midjourney 图像生成任务。

    Args:
        prompt: 提示词（必需）
        concept: 使用的已存在概念的键名（可选）
        aspect_ratio: 纵横比（如 16:9, 1:1）（可选）
        style: 风格（如 raw, cute）（可选）
        version: Midjourney 版本（如 v6, v7, niji）（可选）
        mode: 生成模式（relax, fast, turbo）（默认: relax）
        chaos: 混乱度（0-100）（可选）
        stylize: 风格化程度（0-1000）（可选）
        seed: 种子值（可选）
        quality: 质量（0.25, 0.5, 1, 2）（可选）

    Returns:
        任务创建结果，包含 Job ID 的 JSON 格式字符串。
    """
    try:
        api_key = get_api_key(logger)
        if not api_key:
            return "错误: TTAPI API 密钥未配置，请设置 TTAPI_API_KEY 环境变量"

        output = StringIO()
        err_output = StringIO()

        with redirect_stdout(output), redirect_stderr(err_output):
            cmd_create.handle_create(
                config=config,
                logger=logger,
                api_key=api_key,
                concept=concept,
                prompt=prompt,
                variation=None,
                aspect_ratio=aspect_ratio,
                style=style,
                stylize=stylize,
                chaos=chaos,
                weird=None,
                seed=seed,
                version=version,
                quality=quality,
                no=None,
                tile=False,
                video=False,
                cref=None,
                cref_weight=None,
                sref=None,
                sref_weight=None,
                mode=mode,
                clipboard=False,
                save_prompt=False,
                hook_url=None,
                notify_id=None,
                skip_prompt_check=False,
                cwd=project_root,
                state_dir=STATE_DIR,
                metadata_dir=METADATA_DIR
            )

        result = output.getvalue()
        error_result = err_output.getvalue()

        # 解析 Job ID
        job_id = None
        if "Job ID:" in result:
            try:
                job_id = result.split("Job ID:")[1].strip().split()[0]
            except:
                pass

        response = {
            "success": True,
            "message": "任务创建成功",
            "job_id": job_id,
            "output": result.strip()
        }

        if error_result:
            response["errors"] = error_result.strip()

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


@mcp.tool()
def list_tasks(
    limit: int = 20,
    status: Optional[str] = None,
    concept: Optional[str] = None,
    sort_by: str = "created_at"
) -> str:
    """列出任务列表。

    Args:
        limit: 返回任务数量限制（默认: 20）
        status: 按状态过滤（如 completed, pending）（可选）
        concept: 按概念过滤（可选）
        sort_by: 排序字段（默认: created_at）（可选）

    Returns:
        任务列表的 JSON 格式字符串。
    """
    try:
        import types

        args = types.SimpleNamespace()
        args.limit = limit
        args.status = status
        args.concept = concept
        args.sort_by = sort_by
        args.ascending = False
        args.verbose = True

        output = StringIO()
        with redirect_stdout(output):
            cmd_list_tasks.handle_list_tasks(
                status=status,
                concept=concept,
                limit=limit,
                sort_by=sort_by,
                ascending=False,
                verbose=True,
                logger=logger,
                crc_base_dir=CRC_BASE_DIR,
                remote=False,
                api_key=None,
                args=args
            )

        result = output.getvalue()
        return result

    except Exception as e:
        logger.error(f"列出任务失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


@mcp.tool()
def view_task(
    task_id: str,
    remote: bool = False,
    save: bool = False
) -> str:
    """查看任务的详细信息。

    Args:
        task_id: 要查看的任务标识符（Job ID 或文件名）
        remote: 是否从远程 API 获取信息（默认: False）
        save: 如果从远程获取，是否保存到本地（默认: False）

    Returns:
        任务详情的 JSON 格式字符串。
    """
    try:
        output = StringIO()
        with redirect_stdout(output):
            cmd_view.handle_view(
                identifier=task_id,
                last_job=False,
                last_succeed=False,
                remote=remote,
                local_only=False,
                save=save,
                history=False,
                verbose=True,
                metadata_dir=METADATA_DIR,
                state_dir=STATE_DIR
            )

        result = output.getvalue()
        return result

    except Exception as e:
        logger.error(f"查看任务失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


@mcp.tool()
def perform_action(
    task_id: str,
    action_code: str,
    mode: str = "fast",
    wait: bool = False
) -> str:
    """对现有任务执行操作（如 Upscale, Variation, Reroll）。

    Args:
        task_id: 要操作的任务标识符（Job ID 或文件名）
        action_code: 操作代码（如 variation1, upsample1, reroll）
        mode: 操作使用的生成模式（默认: fast）
        wait: 是否等待任务完成（默认: False）

    Returns:
        操作结果的 JSON 格式字符串。

    可用的操作代码: upsample1, upsample2, upsample3, upsample4,
    variation1, variation2, variation3, variation4, reroll
    """
    try:
        api_key = get_api_key(logger)
        if not api_key:
            return "错误: TTAPI API 密钥未配置"

        if action_code not in ACTION_CHOICES:
            available = ", ".join(ACTION_CHOICES)
            return json.dumps({
                "success": False,
                "error": f"无效的操作代码: {action_code}",
                "available_actions": ACTION_CHOICES
            }, ensure_ascii=False, indent=2)

        import types

        args = types.SimpleNamespace()
        args.action_code = action_code
        args.identifier = task_id
        args.last_job = False
        args.last_succeed = False
        args.hook_url = None
        args.wait = wait
        args.mode = mode
        args.verbose = False
        args.list_ = False

        output = StringIO()
        with redirect_stdout(output):
            cmd_action.handle_action(
                args=args,
                logger=logger,
                api_key=api_key,
                config=config,
                cwd=project_root,
                crc_base_dir=CRC_BASE_DIR,
                state_dir=STATE_DIR
            )

        result = output.getvalue()
        return result

    except Exception as e:
        logger.error(f"执行操作失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


@mcp.tool()
def describe_image(image_path: str) -> str:
    """根据上传的图片生成相关提示词。

    Args:
        image_path: 本地图片文件路径或可公开访问的图片 URL。

    Returns:
        图像描述结果的 JSON 格式字符串。
    """
    try:
        api_key = get_api_key(logger)
        if not api_key:
            return "错误: TTAPI API 密钥未配置"

        output = StringIO()
        with redirect_stdout(output):
            cmd_describe.handle_describe(
                image_path_or_url=image_path,
                hook_url=None,
                logger=logger,
                api_key=api_key
            )

        result = output.getvalue()
        return result

    except Exception as e:
        logger.error(f"描述图像失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


# ============================================================================
# MCP 资源定义
# ============================================================================

@mcp.resource("file://concepts.json")
def get_concepts_resource() -> str:
    """获取创意概念配置的 JSON 文件。

    这是一个 MCP 资源，可以被 LLM 直接读取以了解可用的创意概念。
    """
    try:
        with open(user_config_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # 如果用户配置不存在，返回默认配置
        try:
            with open(default_config_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"无法读取概念配置: {e}")
            return json.dumps({"error": f"无法读取概念配置: {str(e)}")
    except Exception as e:
        logger.error(f"读取概念资源失败: {e}")
        return json.dumps({"error": str(e)})


@mcp.resource("file://tasks.json")
def get_tasks_resource(limit: int = 20) -> str:
    """获取任务列表的 JSON 文件。

    这是一个 MCP 资源，可以被 LLM 直接读取以查看任务状态。

    Args:
        limit: 返回任务数量限制（默认: 20）
    """
    try:
        metadata_file = os.path.join(METADATA_DIR, 'images_metadata.json')
        if not os.path.exists(metadata_file):
            return json.dumps({"images": [], "version": "1.0"}, ensure_ascii=False, indent=2)

        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 限制返回的任务数量
        if "images" in data:
            data["images"] = data["images"][:limit]

        return json.dumps(data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"读取任务资源失败: {e}")
        return json.dumps({"error": str(e)})


# ============================================================================
# 服务器入口
# ============================================================================

def main():
    """启动 MCP 服务器"""
    logger.info("启动 Cell Cover Generator MCP Server")
    mcp.run()


if __name__ == "__main__":
    main()
