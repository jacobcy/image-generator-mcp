#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import typer
import json

import logging
try:
    from dotenv import load_dotenv
    # 显式指定 .env 文件路径，确保从项目根目录加载
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv_path = os.path.join(project_root, '.env')
    if os.path.exists(dotenv_path):
        loaded = load_dotenv(dotenv_path=dotenv_path)
        # if loaded:  # 评论掉调试打印
        #     print(f"DEBUG [cli.py]: Successfully loaded .env from: {dotenv_path}")
        openai_key_cli = os.getenv("OPENAI_API_KEY")
        ttapi_key_cli = os.getenv("TTAPI_API_KEY")
        # print(f"DEBUG [cli.py]: OPENAI_API_KEY after load: {'SET' if openai_key_cli else 'NOT SET'}")
        # print(f"DEBUG [cli.py]: TTAPI_API_KEY after load: {'SET' if ttapi_key_cli else 'NOT SET'}")
    else:
        # print(f"DEBUG [cli.py]: .env file not found at: {dotenv_path}")  # 评论掉
        pass # 如果没有 .env 文件，继续执行，依赖于已设置的环境变量
except ImportError:
    logging.warning("dotenv 模块未安装，请运行 pip install python-dotenv")

from typing import Optional, List

from .utils.config import load_config, get_api_key
from .utils.log import setup_logging
from .utils.filesystem_utils import check_and_create_directories, read_last_job_id, write_last_job_id, read_last_succeed_job_id
from .constants import ACTION_CHOICES, ACTION_DESCRIPTIONS

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
from .commands.sync import handle_sync # Import handle_sync

app = typer.Typer(
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)
CELL_COVER_DIR = os.path.dirname(os.path.abspath(__file__))

def common_setup(verbose: bool):
    """执行通用的设置步骤，初始化日志、配置和基于用户主目录的目录。

    Returns:
        Tuple[logging.Logger, dict, str, str, str, str]: 
            logger, config, cwd, crc_base_dir, state_dir, output_dir
    """
    try:
        # Get current working directory
        cwd = os.getcwd()

        # 获取用户主目录
        home_dir = os.path.expanduser("~")
        
        # --- Define and ensure home-based directories ---
        crc_base_dir = os.path.join(home_dir, '.crc') # 放在用户主目录下
        log_dir = os.path.join(crc_base_dir, 'logs')
        state_dir = os.path.join(crc_base_dir, 'state')
        metadata_dir = os.path.join(crc_base_dir, 'metadata')
        
        # 检查是否已初始化
        if not os.path.exists(crc_base_dir):
            print(f"错误：未找到 .crc 目录，请先运行 'crc init' 初始化必要的目录。")
            raise typer.Exit(code=1)

        # Create essential directories first (log and state)
        try:
            os.makedirs(log_dir, exist_ok=True)
            os.makedirs(state_dir, exist_ok=True) # Ensure state dir exists for job IDs etc.
            os.makedirs(metadata_dir, exist_ok=True) # Ensure metadata dir exists
        except OSError as e:
             # Use a temporary basic logger or print if full logger setup fails
             print(f"FATAL: Cannot create essential directories {log_dir} or {state_dir}: {e}")
             sys.exit(1) # Exit if we can't create essential dirs

        # --- Setup logging relative to home dir ---
        # Assuming setup_logging accepts log_dir and verbose flag
        logger = setup_logging(log_dir=log_dir, verbose=verbose)
        logger.debug(f"Current working directory (CWD): {cwd}")
        logger.debug(f"CRC base directory: {crc_base_dir}")
        logger.debug(f"Log directory: {log_dir}")
        logger.debug(f"State directory: {state_dir}")
        logger.debug(f"Metadata directory: {metadata_dir}")

        # --- Load config: default from install dir, override/merge with CWD config ---
        default_config_path = os.path.join(CELL_COVER_DIR, 'prompts_config.json')
        local_config_path = os.path.join(cwd, 'prompts_config.json') # Config in CWD
        logger.debug(f"Default config path: {default_config_path}")
        logger.debug(f"Local config path (override): {local_config_path}")

        # Assuming load_config is modified/designed to check local_config_path and merge/override
        config = load_config(logger, default_config_path, local_config_path)
        if config is None: # load_config should return None on critical failure
            logger.critical("无法加载必要的配置文件。请检查默认配置是否存在且格式正确。")
            # Logger might not be fully set up, so print as well
            print("错误：无法加载必要的配置文件。请检查默认配置是否存在且格式正确。")
            raise typer.Exit(code=1)
        logger.info("配置文件加载完成。")

        # 获取用户指定的 output 目录，如果未指定则使用默认目录
        try:
            with open(os.path.join(state_dir, 'config.json'), 'r') as f:
                import json
                user_config = json.load(f)
                output_dir = user_config.get('output_dir', os.path.join(crc_base_dir, 'output'))
        except (FileNotFoundError, json.JSONDecodeError):
            # 如果文件不存在或解析失败，使用默认值
            output_dir = os.path.join(crc_base_dir, 'output')
            
        # 确保 output 目录存在
        os.makedirs(output_dir, exist_ok=True)
        logger.debug(f"Output directory: {output_dir}")

        # Return logger, config, CWD, base dir, state dir, and output dir
        return logger, config, cwd, crc_base_dir, state_dir, output_dir
    except Exception as e:
        print(f"错误：设置失败，原因: {str(e)}")  # 简化错误输出
        sys.exit(1)

@app.command()
def init(
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="指定输出目录路径，默认在用户主目录下的 .crc/output"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新初始化，覆盖现有设置")
):
    """初始化必要的目录结构，设置输出路径。"""
    
    # 获取用户主目录
    home_dir = os.path.expanduser("~")
    
    # 创建 .crc 目录结构
    crc_base_dir = os.path.join(home_dir, '.crc')
    log_dir = os.path.join(crc_base_dir, 'logs')
    state_dir = os.path.join(crc_base_dir, 'state')
    metadata_dir = os.path.join(crc_base_dir, 'metadata')
    
    # 检查是否已初始化且不是强制模式
    if os.path.exists(crc_base_dir) and not force:
        print(f"警告：.crc 目录已存在于 {crc_base_dir}。若要重新初始化，请使用 --force 选项。")
        return 0
    
    # 创建目录结构
    try:
        os.makedirs(crc_base_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(state_dir, exist_ok=True)
        os.makedirs(metadata_dir, exist_ok=True)
        
        # 如果未指定输出目录，使用默认路径
        if not output_dir:
            output_dir = os.path.join(crc_base_dir, 'output')
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建空的 images_metadata.json 文件
        metadata_file = os.path.join(metadata_dir, 'images_metadata.json')
        if not os.path.exists(metadata_file) or force:
            with open(metadata_file, 'w') as f:
                json.dump({"images": [], "version": "1.0"}, f, indent=4, ensure_ascii=False)
            print(f"  已创建元数据文件: {metadata_file}")
        
        # 保存用户配置
        with open(os.path.join(state_dir, 'config.json'), 'w') as f:
            json.dump({'output_dir': output_dir}, f)
            
        print(f"初始化成功！")
        print(f"  基本目录: {crc_base_dir}")
        print(f"  日志目录: {log_dir}")
        print(f"  状态目录: {state_dir}")
        print(f"  元数据目录: {metadata_dir}")
        print(f"  输出目录: {output_dir}")
        return 0
        
    except Exception as e:
        print(f"错误：初始化失败，原因：{str(e)}")
        return 1

@app.command()
def list_concepts(verbose: bool = False):
    """List available creative concepts."""
    # Update call to unpack new return values
    logger, config, _, _, _, _ = common_setup(verbose)
    handle_list_concepts(config)

@app.command()
def variations(concept_key: str, verbose: bool = False):
    """List available variations for a specific concept."""
    # Update call to unpack new return values
    logger, config, _, _, _, _ = common_setup(verbose)
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
    aspect: str = typer.Option("cover", "--aspect", "-ar"),
    quality: str = typer.Option("high", "--quality", "-q"),
    version: str = typer.Option("v6", "--version", "-ver"),
    cref: Optional[str] = None,
    style: Optional[List[str]] = None,
    style_degree: Optional[float] = typer.Option(None, "--sd", help="生成Stable Diffusion风格的加权提示词，并指定权重值"),
    clipboard: bool = False,
    save_prompt: bool = False,
    verbose: bool = False
):
    """Generate only the Midjourney prompt text (does not submit)."""
    # Update call to unpack new return values
    logger, config, cwd, _, _, output_dir = common_setup(verbose) # Get cwd, output_dir
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
    args.style_degree = style_degree
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
        logger=logger,
        cwd=cwd,
        output_dir=output_dir,
        style_degree=args.style_degree
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
    """Create a new Midjourney image generation task."""
    # Update call to unpack new return values
    logger, config, cwd, _, state_dir, _ = common_setup(verbose) # Get cwd, state_dir
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("create 命令需要 TTAPI API 密钥")
        print("错误: create 命令需要 TTAPI API 密钥 (请设置 TTAPI_API_KEY 或在 .env 中配置)")
        raise typer.Exit(code=1)
    
    # Pass cwd and state_dir
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
        notify_id=notify_id,
        cwd=cwd, # Pass cwd
        state_dir=state_dir # Pass state_dir for writing job IDs
    )

@app.command()
def recreate(
    identifier: str,
    hook_url: Optional[str] = None,
    cref: Optional[str] = None,
    verbose: bool = False
):
    """Recreate an image using a previous job's prompt and seed."""
    # Update call to unpack new return values
    logger, config, cwd, _, state_dir, metadata_dir = common_setup(verbose) # Get cwd, state_dir, metadata_dir
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("recreate 命令需要 TTAPI API 密钥")
        print("错误: recreate 命令需要 TTAPI API 密钥 (请设置 TTAPI_API_KEY 或在 .env 中配置)")
        raise typer.Exit(code=1)
    class Args: pass
    args = Args()
    args.identifier = identifier
    args.hook_url = hook_url
    args.cref = cref
    args.verbose = verbose
    # Pass relevant paths
    handle_recreate(
        args=args,
        config=config,
        logger=logger,
        api_key=api_key,
        cwd=cwd, # Pass cwd
        state_dir=state_dir, # Pass state_dir for writing job IDs
        metadata_dir=metadata_dir # Pass metadata_dir for finding old task info
    )

@app.command()
def select(
    identifier: Optional[str] = typer.Argument(None, help="要处理的任务的 Job ID 或其他标识符 (默认: 最近成功任务)"),
    select_parts: List[str] = typer.Option(..., "--select", "-s", help="选择要保存的部分 (例如 u1 u3)", rich_help_panel="Required", show_default=False, metavar="PARTS"),
    output_dir: Optional[str] = typer.Option(None, help="指定输出目录 (默认: 当前目录下的 .crc/output/<job_id>/select)"),
    verbose: bool = False
):
    """Split a 4-grid image (from upscale) and save selected parts."""
    # Update call to unpack new return values
    logger, config, cwd, crc_base_dir, state_dir, default_output_base = common_setup(verbose) # Get cwd, state_dir, default output base
    metadata_dir = os.path.join(crc_base_dir, 'metadata')

    class Args: pass
    args = Args()
    args.identifier = identifier
    args.select_parts = select_parts
    args.output_dir = output_dir # User-provided output dir
    args.verbose = verbose

    # Pass relevant paths to handler
    handle_select(
        args=args,
        logger=logger,
        cwd=cwd,
        state_dir=state_dir,
        default_output_base=default_output_base,
        metadata_dir=metadata_dir
    )

@app.command()
def view(
    identifier: Optional[str] = typer.Option(None, "--identifier", "-i", help="要查看的任务的 Job ID 或其他标识符 (默认: 最近成功任务)"),
    last_job: bool = typer.Option(False, "--last-job", help="使用上一个任务"),
    last_succeed: bool = typer.Option(False, "--last-succeed", help="使用上一个成功任务"),
    remote: bool = typer.Option(False, "--remote", help="从远程获取信息"),
    local_only: bool = typer.Option(False, "--local-only", help="仅使用本地信息"),
    save: bool = typer.Option(False, "--save", help="保存从远程获取的信息"),
    history: bool = typer.Option(False, "--history", help="查看历史记录"),
    verbose: bool = typer.Option(False, "--verbose", help="显示详细输出")
):
    """View an image or task metadata (local or remote)."""
    logger, config, cwd, crc_base_dir, state_dir, output_dir = common_setup(verbose)
    api_key = get_api_key(logger) if remote or history else None
    
    # 计算元数据目录路径
    metadata_dir = os.path.join(crc_base_dir, 'metadata')
    
    handle_view(
        identifier=identifier,
        last_job=last_job,
        last_succeed=last_succeed,
        remote=remote,
        local_only=local_only,
        save=save,
        history=history,
        verbose=verbose,
        metadata_dir=metadata_dir,
        state_dir=state_dir  # 添加 state_dir 参数
    )

@app.command()
def blend(
    identifiers: List[str] = typer.Argument(..., help="要混合的图像文件路径或任务 ID（最多3个）"),
    title: Optional[str] = None,
    weights: Optional[str] = None,
    interactive: bool = False,
    verbose: bool = False
):
    """Blend up to 3 images (local files or task results)."""
    # Update call to unpack new return values
    logger, config, cwd, crc_base_dir, state_dir, _ = common_setup(verbose)
    api_key = get_api_key(logger) # Blending might involve API call
    if not api_key:
        logger.critical("blend 命令需要 TTAPI API 密钥")
        print("错误: blend 命令需要 TTAPI API 密钥 (请设置 TTAPI_API_KEY 或在 .env 中配置)")
        raise typer.Exit(code=1)

    class Args: pass
    args = Args()
    args.identifiers = identifiers
    args.title = title
    args.weights = weights
    args.interactive = interactive
    args.verbose = verbose

    # Pass necessary paths
    handle_blend(
        args=args,
        logger=logger,
        api_key=api_key,
        cwd=cwd,
        crc_base_dir=crc_base_dir, # For finding task images/metadata
        state_dir=state_dir # For resolving task IDs if needed
    )

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
    """Describe an image using OpenAI CLIP or local task metadata."""
    # Update call to unpack new return values
    logger, config, cwd, crc_base_dir, state_dir, output_dir = common_setup(verbose)
    openai_api_key = get_api_key(logger, service="openai") # Need OpenAI key for describe

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

    # Pass necessary paths and keys
    handle_describe(
        args=args,
        logger=logger,
        openai_api_key=openai_api_key,
        cwd=cwd,
        crc_base_dir=crc_base_dir, # For finding task images/metadata
        state_dir=state_dir, # For resolving task IDs
        output_dir=output_dir # For saving description
    )

@app.command("list-tasks")
def list_tasks(
    status: str = typer.Option(None, "--status", "-s", help="Filter tasks by status (e.g., 'completed', 'pending')"),
    concept: str = typer.Option(None, "--concept", "-c", help="Filter tasks by concept ID"),
    limit: int = typer.Option(None, "--limit", "-l", help="Limit the number of tasks displayed"),
    sort_by: str = typer.Option("created_at", "--sort", help="Field to sort by (e.g., 'created_at', 'status')"),
    ascending: bool = typer.Option(False, "--asc", help="Sort in ascending order"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output including full prompts"),
    remote: bool = typer.Option(False, "--remote", "-r", help="Get tasks from remote API instead of local metadata")
):
    """List and filter tasks based on local metadata."""
    # Update call to unpack new return values
    logger, config, cwd, crc_base_dir, state_dir, _ = common_setup(verbose)
    
    # 如果remote为True，需要获取API密钥
    api_key = None
    if remote:
        api_key = get_api_key(logger)
        if not api_key:
            logger.critical("remote模式需要TTAPI API密钥")
            print("错误: 使用--remote选项需要TTAPI API密钥 (请设置TTAPI_API_KEY或在.env中配置)")
            raise typer.Exit(code=1)

    # Pass necessary paths
    handle_list_tasks(
        status=status,
        concept=concept,
        limit=limit,
        sort_by=sort_by,
        ascending=ascending,
        verbose=verbose,
        logger=logger,
        crc_base_dir=crc_base_dir, # Pass base dir for finding metadata
        remote=remote,
        api_key=api_key
    )

@app.command("list") # Alias for list-tasks
def list_alias(
    status: str = typer.Option(None, "--status", "-s", help="Filter tasks by status (e.g., 'completed', 'pending')"),
    concept: str = typer.Option(None, "--concept", "-c", help="Filter tasks by concept ID"),
    limit: int = typer.Option(None, "--limit", "-l", help="Limit the number of tasks displayed"),
    sort_by: str = typer.Option("created_at", "--sort", help="Field to sort by (e.g., 'created_at', 'status')"),
    ascending: bool = typer.Option(False, "--asc", help="Sort in ascending order"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output including full prompts"),
    remote: bool = typer.Option(False, "--remote", "-r", help="Get tasks from remote API instead of local metadata")
):
    """Alias for list-tasks."""
    # Update call to unpack new return values
    logger, config, cwd, crc_base_dir, state_dir, _ = common_setup(verbose)

    # 如果remote为True，需要获取API密钥
    api_key = None
    if remote:
        api_key = get_api_key(logger)
        if not api_key:
            logger.critical("remote模式需要TTAPI API密钥")
            print("错误: 使用--remote选项需要TTAPI API密钥 (请设置TTAPI_API_KEY或在.env中配置)")
            raise typer.Exit(code=1)

    # Pass necessary paths
    handle_list_tasks(
        status=status,
        concept=concept,
        limit=limit,
        sort_by=sort_by,
        ascending=ascending,
        verbose=verbose,
        logger=logger,
        crc_base_dir=crc_base_dir, # Pass base dir for finding metadata
        remote=remote,
        api_key=api_key
    )

@app.command()
def action(
    action_code: Optional[str] = typer.Argument(None, help=f'要应用的操作代码. 可用: {", ".join(ACTION_CHOICES)}'),
    list_: bool = typer.Option(False, "--list", help="列出所有可用的操作代码并退出。"),
    identifier: Optional[str] = None,
    last_job: bool = False,
    last_succeed: bool = False,
    hook_url: Optional[str] = None,
    wait: bool = False,
    mode: str = typer.Option("fast", "--mode", "-m", help="生成模式"),
    verbose: bool = False
):
    """Perform an action (e.g., variation, upscale) on a task."""
    # Update call to unpack new return values
    logger, config, cwd, crc_base_dir, state_dir, _ = common_setup(verbose)
    api_key = get_api_key(logger) # Action requires API key
    if not api_key:
        logger.critical("action 命令需要 TTAPI API 密钥")
        print("错误: action 命令需要 TTAPI API 密钥 (请设置 TTAPI_API_KEY 或在 .env 中配置)")
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
    args.list_ = list_

    # Pass necessary paths
    handle_action(
        args=args,
        logger=logger,
        api_key=api_key,
        config=config,
        cwd=cwd,
        crc_base_dir=crc_base_dir, # For finding metadata
        state_dir=state_dir # For resolving task IDs
    )

# --- Add Sync Command --- #
@app.command()
def sync(verbose: bool = False):
    """Synchronize local task status with the remote API and download completed images."""
    logger, config, cwd, crc_base_dir, state_dir, output_dir = common_setup(verbose)
    api_key = get_api_key(logger)
    if not api_key:
        logger.critical("sync 命令需要 TTAPI API 密钥")
        print("错误: sync 命令需要 TTAPI API 密钥 (请设置 TTAPI_API_KEY 或在 .env 中配置)")
        raise typer.Exit(code=1)
    
    metadata_dir = os.path.join(crc_base_dir, 'metadata')
    
    handle_sync(
        logger=logger,
        api_key=api_key,
        metadata_dir=metadata_dir,
        output_dir=output_dir,
        state_dir=state_dir,
        silent=False # Or add a --silent option to the command
    )
# --- End Sync Command --- #

if __name__ == "__main__":
    app()