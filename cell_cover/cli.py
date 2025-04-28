#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import typer

import logging
try:
    from dotenv import load_dotenv
    # 显式指定 .env 文件路径，确保从项目根目录加载
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv_path = os.path.join(project_root, '.env')
    if os.path.exists(dotenv_path):
        loaded = load_dotenv(dotenv_path=dotenv_path)
        if loaded:
            # print(f"DEBUG [cli.py]: Successfully loaded .env from: {dotenv_path}")
            openai_key_cli = os.getenv("OPENAI_API_KEY")
            ttapi_key_cli = os.getenv("TTAPI_API_KEY")
            # print(f"DEBUG [cli.py]: OPENAI_API_KEY after load: {'SET' if openai_key_cli else 'NOT SET'}")
            # print(f"DEBUG [cli.py]: TTAPI_API_KEY after load: {'SET' if ttapi_key_cli else 'NOT SET'}")
        else:
             print(f"DEBUG [cli.py]: load_dotenv called but reported failure for: {dotenv_path}")
    else:
        print(f"DEBUG [cli.py]: .env file not found at: {dotenv_path}")
        pass # 如果没有 .env 文件，继续执行，依赖于已设置的环境变量
except ImportError:
    logging.warning("dotenv 模块未安装，请运行 pip install python-dotenv")

from typing import Optional, List

from .utils.config import load_config, get_api_key
from .utils.log import setup_logging
from .utils.filesystem_utils import check_and_create_directories, read_last_job_id, write_last_job_id, read_last_succeed_job_id

from .commands.create import handle_create
from .commands.generate import handle_generate
from .commands.blend import handle_blend
from .commands.describe import handle_describe
from .commands.list_cmd import handle_list_concepts, handle_list_variations
from .commands.recreate import handle_recreate
from .commands.select import handle_select
from .commands.view import handle_view
from .commands.action import handle_action
from .commands.list_tasks import handle_list_tasks

app = typer.Typer(
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)
CELL_COVER_DIR = os.path.dirname(os.path.abspath(__file__))

ACTION_CHOICES = ["variation1", "variation2", "variation3", "variation4", "upscale2", "upscale4", "reroll"]

def common_setup(verbose: bool):
    logger = setup_logging(CELL_COVER_DIR, verbose)
    config_path = os.path.join(CELL_COVER_DIR, 'prompts_config.json')
    config = load_config(logger, config_path)
    if not config:
        logger.critical("无法加载配置文件")
        raise typer.Exit(code=1)
    if not check_and_create_directories(logger):
        logger.critical("无法创建必要目录")
        raise typer.Exit(code=1)
    return logger, config

@app.command()
def list_concepts(verbose: bool = False):
    logger, config = common_setup(verbose)
    handle_list_concepts(config)

@app.command()
def variations(concept_key: str, verbose: bool = False):
    logger, config = common_setup(verbose)
    class Args: pass
    args = Args()
    args.concept_key = concept_key
    args.verbose = verbose
    handle_list_variations(config, args)

@app.command()
def generate(
    concept: Optional[str] = typer.Option(None, "--concept", "-c"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p"),
    variation: Optional[List[str]] = typer.Option(None, "--variation", "-var"),
    aspect: str = typer.Option("cell_cover", "--aspect", "-ar"),
    quality: str = typer.Option("high", "--quality", "-q"),
    version: str = typer.Option("v6", "--version", "-ver"),
    cref: Optional[str] = None,
    style: Optional[List[str]] = None,
    clipboard: bool = False,
    save_prompt: bool = False,
    verbose: bool = False
):
    logger, config = common_setup(verbose)
    class Args: pass
    args = Args()
    args.concept = concept
    args.prompt = prompt
    args.variation = variation
    args.aspect = aspect
    args.quality = quality
    args.version = version
    args.cref = cref
    args.style = style
    args.clipboard = clipboard
    args.save_prompt = save_prompt
    args.verbose = verbose
    handle_generate(
        prompt=args.prompt,
        concept=args.concept,
        variation=args.variation,
        style=args.style,
        aspect=args.aspect,
        quality=args.quality,
        version=args.version,
        cref=args.cref,
        clipboard=args.clipboard,
        save_prompt=args.save_prompt,
        config=config,
        logger=logger
    )

@app.command()
def create(
    concept: Optional[str] = typer.Option(None, "--concept", "-c"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p"),
    variation: Optional[str] = typer.Option(None, "--variation", "-var"),
    aspect: str = typer.Option("cell_cover", "--aspect", "-ar"),
    quality: str = typer.Option("high", "--quality", "-q"),
    version: str = typer.Option("v6", "--version", "-ver"),
    mode: str = typer.Option("relax", "--mode", "-m"),
    cref: Optional[str] = None,
    style: Optional[str] = None,
    clipboard: bool = False,
    save_prompt: bool = False,
    hook_url: Optional[str] = None,
    notify_id: Optional[str] = None,
    verbose: bool = False
):
    logger, config = common_setup(verbose)
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("create 命令需要 API 密钥")
        raise typer.Exit(code=1)
    
    # 直接传递参数，不再使用 Args 类
    handle_create(
        config=config,
        logger=logger,
        api_key=api_key,
        concept=concept,
        prompt=prompt,
        variation=variation,
        aspect=aspect,
        quality=quality,
        version=version,
        mode=mode,
        cref=cref,
        style=style,
        clipboard=clipboard,
        save_prompt=save_prompt,
        hook_url=hook_url,
        notify_id=notify_id
    )

@app.command()
def recreate(
    identifier: str,
    hook_url: Optional[str] = None,
    cref: Optional[str] = None,
    verbose: bool = False
):
    logger, config = common_setup(verbose)
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("recreate 命令需要 API 密钥")
        raise typer.Exit(code=1)
    class Args: pass
    args = Args()
    args.identifier = identifier
    args.hook_url = hook_url
    args.cref = cref
    args.verbose = verbose
    handle_recreate(args, config, logger, api_key)

@app.command()
def select(
    image_path: Optional[str] = None,
    last_job: bool = False,
    last_succeed: bool = False,
    select: List[str] = typer.Option(..., "--select", "-s", help="选择要保存的部分", rich_help_panel="Required", show_default=False),
    output_dir: Optional[str] = None,
    verbose: bool = False
):
    logger, _ = common_setup(verbose)
    class Args: pass
    args = Args()
    args.image_path = image_path
    args.last_job = last_job
    args.last_succeed = last_succeed
    args.select = select
    args.output_dir = output_dir
    args.verbose = verbose
    handle_select(args, logger)

@app.command()
def view(
    identifier: Optional[str] = None,
    last_job: bool = False,
    last_succeed: bool = False,
    remote: bool = False,
    local_only: bool = False,
    save: bool = False,
    history: bool = False,
    verbose: bool = False
):
    logger, _ = common_setup(verbose)
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("view 命令需要 API 密钥")
        raise typer.Exit(code=1)
    class Args: pass
    args = Args()
    args.identifier = identifier
    args.last_job = last_job
    args.last_succeed = last_succeed
    args.remote = remote
    args.local_only = local_only
    args.save = save
    args.history = history
    args.verbose = verbose
    handle_view(args, logger, api_key)

@app.command()
def blend(
    identifiers: List[str] = typer.Argument(..., help="要混合的图像文件路径或任务 ID（最多3个）"),
    title: Optional[str] = None,
    weights: Optional[str] = None,
    interactive: bool = False,
    verbose: bool = False
):
    logger, config = common_setup(verbose)
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("blend 命令需要 API 密钥")
        raise typer.Exit(code=1)
    class Args: pass
    args = Args()
    args.identifiers = identifiers
    args.title = title
    args.weights = weights
    args.interactive = interactive
    args.verbose = verbose
    handle_blend(args, config, logger, api_key)

@app.command()
def describe(
    identifier: Optional[str] = None,
    last_job: bool = False,
    last_succeed: bool = False,
    text_only: bool = False,
    components: bool = False,
    save: bool = False,
    language: Optional[str] = None,
    verbose: bool = False
):
    logger, _ = common_setup(verbose)
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("describe 命令需要 API 密钥")
        raise typer.Exit(code=1)
    class Args: pass
    args = Args()
    args.identifier = identifier
    args.last_job = last_job
    args.last_succeed = last_succeed
    args.text_only = text_only
    args.components = components
    args.save = save
    args.language = language
    args.verbose = verbose
    handle_describe(args, logger, api_key)

@app.command("list-tasks")
def list_tasks(
    status: str = typer.Option(None, "--status", "-s", help="Filter tasks by status (e.g., 'completed', 'pending')"),
    concept: str = typer.Option(None, "--concept", "-c", help="Filter tasks by concept ID"),
    limit: int = typer.Option(None, "--limit", "-l", help="Limit the number of tasks displayed"),
    sort_by: str = typer.Option("created_at", "--sort", help="Field to sort by (e.g., 'created_at', 'status')"),
    ascending: bool = typer.Option(False, "--asc", help="Sort in ascending order"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output including full prompts")
):
    """List existing generation tasks."""
    logger = setup_logging(CELL_COVER_DIR, verbose)
    logger.debug("Executing list-tasks command")
    # 直接将 typer 解析的参数传递给处理函数
    # 注意：需要确保 handle_list_tasks 的参数签名与这里一致或能接受一个包含这些属性的对象
    # 为了简单起见，我们创建一个命名空间对象来模拟之前的 args 结构
    # 或者修改 handle_list_tasks 以直接接受这些关键字参数
    from argparse import Namespace
    args = Namespace(
        status=status,
        concept=concept,
        limit=limit,
        sort_by=sort_by,
        ascending=ascending,
        verbose=verbose
    )
    handle_list_tasks(args, logger)

# 为 "list" 创建别名命令
@app.command("list")
def list_alias(
    status: str = typer.Option(None, "--status", "-s", help="Filter tasks by status (e.g., 'completed', 'pending')"),
    concept: str = typer.Option(None, "--concept", "-c", help="Filter tasks by concept ID"),
    limit: int = typer.Option(None, "--limit", "-l", help="Limit the number of tasks displayed"),
    sort_by: str = typer.Option("created_at", "--sort", help="Field to sort by (e.g., 'created_at', 'status')"),
    ascending: bool = typer.Option(False, "--asc", help="Sort in ascending order"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output including full prompts")
):
    """Alias for the 'list-tasks' command."""
    # 直接调用 list_tasks 的逻辑
    list_tasks(status=status, concept=concept, limit=limit, sort_by=sort_by, ascending=ascending, verbose=verbose)

@app.command()
def action(
    action_code: Optional[str] = typer.Argument(None, help='要应用的操作，例如 "variation1"'),
    list_: bool = typer.Option(False, "--list", help="列出所有可用的操作代码并退出。"),
    identifier: Optional[str] = None,
    last_job: bool = False,
    last_succeed: bool = False,
    hook_url: Optional[str] = None,
    wait: bool = False,
    mode: str = typer.Option("fast", "--mode", "-m", help="生成模式"),
    verbose: bool = False
):
    from .cli import ACTION_CHOICES, ACTION_DESCRIPTIONS  # import here to avoid circular import if any
    logger, _ = common_setup(verbose)
    if list_:
        print("可用的操作代码:")
        for code in ACTION_CHOICES:
            desc = ACTION_DESCRIPTIONS.get(code, "无描述")
            print(f"  {code}: {desc}")
        raise typer.Exit(code=0)
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("action 命令需要 API 密钥")
        raise typer.Exit(code=1)
    if not action_code:
        logger.error("必须提供 action_code 或使用 --list 列出操作代码")
        raise typer.Exit(code=1)
    class Args: pass
    args = Args()
    args.action_code = action_code
    args.identifier = identifier
    args.last_job = last_job
    args.last_succeed = last_succeed
    args.hook_url = hook_url
    args.wait = wait
    args.mode = mode
    args.verbose = verbose
    handle_action(args, logger, api_key)

if __name__ == "__main__":
    app()