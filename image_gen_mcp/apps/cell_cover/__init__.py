#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import types
import json
import logging
from typing import Optional
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

from image_gen_mcp.core.config import load_config, get_api_key
from image_gen_mcp.core.logging import setup_logging
from image_gen_mcp.apps.cell_cover.commands import (
    create as cmd_create,
    list_cmd as cmd_list,
    view as cmd_view,
    action as cmd_action,
    list_tasks as cmd_list_tasks,
    describe as cmd_describe,
)
from image_gen_mcp.apps.cell_cover.constants import ACTION_CHOICES

PLUGIN_NAME = "cell_cover"


def register(mcp):
    # Initialize plugin directories and configuration
    # Get the directory containing this file
    init_file_dir = os.path.dirname(__file__)
    # Go up 3 levels from init file to get project root
    # Structure: .../image_gen_mcp/apps/cell_cover/__init__.py
    # So we need to go up 3 levels to reach project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(init_file_dir)))
    
    _BASE_DIR = os.path.join(project_root, ".crc")
    _STATE_DIR = os.path.join(_BASE_DIR, "state")
    _METADATA_DIR = os.path.join(_BASE_DIR, "metadata")
    _LOG_DIR = os.path.join(_BASE_DIR, "logs")

    os.makedirs(_LOG_DIR, exist_ok=True)
    _logger = setup_logging(log_dir=_LOG_DIR, verbose=False)

    _default_config_path = os.path.join(project_root, "image_gen_mcp", "apps", "cell_cover", "prompts_config.json")
    _user_config_path = os.path.join(os.path.expanduser("~"), ".crc", "prompts_config.json")
    _config = load_config(_logger, _default_config_path, _user_config_path)

    if _config is None:
        _logger.error("cell_cover plugin failed to load config — skipping registration")
        return

    @mcp.tool()
    def list_concepts() -> str:
        """列出所有可用的创意概念及其键。"""
        try:
            output = StringIO()
            with redirect_stdout(output):
                cmd_list.handle_list_concepts(_config)
            return output.getvalue()
        except Exception as e:
            _logger.error(f"列出概念失败: {e}")
            return f"错误: {str(e)}"

    @mcp.tool()
    def list_variations(concept_key: str) -> str:
        """列出指定创意概念的所有可用变体。

        Args:
            concept_key: 要查询变体的创意概念键。
        """
        try:
            output = StringIO()
            with redirect_stdout(output):
                cmd_list.handle_list_variations(_config, concept_key)
            return output.getvalue()
        except Exception as e:
            _logger.error(f"列出变体失败: {e}")
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
        quality: Optional[str] = None,
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
        """
        try:
            api_key = get_api_key(_logger)
            if not api_key:
                return "错误: TTAPI_API_KEY 未配置"
            if not _config:
                return "错误: 配置加载失败"

            output = StringIO()
            err_output = StringIO()
            with redirect_stdout(output), redirect_stderr(err_output):
                cmd_create.handle_create(
                    config=_config, logger=_logger, api_key=api_key,
                    concept=concept, prompt=prompt, variation=None,
                    aspect_ratio=aspect_ratio, style=style, stylize=stylize,
                    chaos=chaos, weird=None, seed=seed, version=version,
                    quality=quality, no=None, tile=False, video=False,
                    cref=None, cref_weight=None, sref=None, sref_weight=None,
                    mode=mode, clipboard=False, save_prompt=False,
                    hook_url=None, notify_id=None, skip_prompt_check=False,
                    cwd=project_root, state_dir=_STATE_DIR, metadata_dir=_METADATA_DIR,
                )

            result = output.getvalue()
            err_result = err_output.getvalue()
            job_id = None
            if "Job ID:" in result:
                try:
                    job_id = result.split("Job ID:")[1].strip().split()[0]
                except Exception:
                    pass

            response = {"success": True, "message": "任务创建成功", "job_id": job_id, "output": result.strip()}
            if err_result:
                response["errors"] = err_result.strip()
            return json.dumps(response, ensure_ascii=False, indent=2)

        except Exception as e:
            _logger.error(f"创建任务失败: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)

    @mcp.tool()
    def list_tasks(
        limit: int = 20,
        status: Optional[str] = None,
        concept: Optional[str] = None,
        sort_by: str = "created_at",
    ) -> str:
        """列出任务列表。

        Args:
            limit: 返回任务数量限制（默认: 20）
            status: 按状态过滤（可选）
            concept: 按概念过滤（可选）
            sort_by: 排序字段（默认: created_at）
        """
        try:
            output = StringIO()
            with redirect_stdout(output):
                cmd_list_tasks.handle_list_tasks(
                    status=status, concept=concept, limit=limit,
                    sort_by=sort_by, ascending=False, verbose=True,
                    logger=_logger, crc_base_dir=_BASE_DIR,
                    remote=False, api_key=None,
                )
            return output.getvalue()
        except Exception as e:
            _logger.error(f"列出任务失败: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)

    @mcp.tool()
    def view_task(task_id: str, remote: bool = False, save: bool = False) -> str:
        """查看任务的详细信息。

        Args:
            task_id: 要查看的任务标识符（Job ID 或文件名）
            remote: 是否从远程 API 获取信息（默认: False）
            save: 如果从远程获取，是否保存到本地（默认: False）
        """
        try:
            output = StringIO()
            with redirect_stdout(output):
                cmd_view.handle_view(
                    identifier=task_id, last_job=False, last_succeed=False,
                    remote=remote, local_only=False, save=save,
                    history=False, verbose=True,
                    metadata_dir=_METADATA_DIR, state_dir=_STATE_DIR,
                )
            return output.getvalue()
        except Exception as e:
            _logger.error(f"查看任务失败: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)

    @mcp.tool()
    def perform_action(task_id: str, action_code: str, mode: str = "fast", wait: bool = False) -> str:
        """对现有任务执行操作（如 Upscale, Variation, Reroll）。

        Args:
            task_id: 要操作的任务标识符
            action_code: 操作代码（upsample1-4, variation1-4, reroll）
            mode: 生成模式（默认: fast）
            wait: 是否等待任务完成（默认: False）
        """
        try:
            api_key = get_api_key(_logger)
            if not api_key:
                return "错误: TTAPI_API_KEY 未配置"

            if action_code not in ACTION_CHOICES:
                return json.dumps(
                    {"success": False, "error": f"无效操作: {action_code}", "available_actions": ACTION_CHOICES},
                    ensure_ascii=False, indent=2,
                )

            args = types.SimpleNamespace(
                action_code=action_code, identifier=task_id,
                last_job=False, last_succeed=False, hook_url=None,
                wait=wait, mode=mode, verbose=False, list_=False,
            )
            output = StringIO()
            with redirect_stdout(output):
                cmd_action.handle_action(
                    args=args, logger=_logger, api_key=api_key,
                    config=_config, cwd=project_root,
                    crc_base_dir=_BASE_DIR, state_dir=_STATE_DIR,
                )
            return output.getvalue()
        except Exception as e:
            _logger.error(f"执行操作失败: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)

    @mcp.tool()
    def describe_image(image_path: str) -> str:
        """根据上传的图片生成相关提示词。

        Args:
            image_path: 本地图片文件路径或可公开访问的图片 URL。
        """
        try:
            api_key = get_api_key(_logger)
            if not api_key:
                return "错误: TTAPI_API_KEY 未配置"
            output = StringIO()
            with redirect_stdout(output):
                cmd_describe.handle_describe(
                    image_path_or_url=image_path, hook_url=None,
                    logger=_logger, api_key=api_key,
                )
            return output.getvalue()
        except Exception as e:
            _logger.error(f"描述图像失败: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)

    @mcp.resource("file://concepts.json")
    def get_concepts_resource() -> str:
        """获取创意概念配置的 JSON 文件。"""
        try:
            path = _user_config_path if os.path.exists(_user_config_path) else _default_config_path
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.resource("file://tasks.json")
    def get_tasks_resource() -> str:
        """获取任务列表的 JSON 文件（最近20条）。"""
        try:
            metadata_file = os.path.join(_METADATA_DIR, "images_metadata.json")
            if not os.path.exists(metadata_file):
                return json.dumps({"images": [], "version": "1.0"}, ensure_ascii=False, indent=2)
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "images" in data:
                data["images"] = data["images"][:20]
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    _logger.info(f"Plugin registered: {PLUGIN_NAME}")
