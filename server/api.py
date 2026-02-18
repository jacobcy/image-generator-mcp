"""
Cell Cover Generator HTTP Server
提供通过 Tailscale 访问的 REST API
"""
import os
import sys
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional
import json
from io import StringIO
from contextlib import redirect_stdout

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入 CLI 命令处理函数
from cell_cover.utils.config import load_config, get_api_key
from cell_cover.utils.log import setup_logging
from cell_cover.constants import ACTION_CHOICES

app = FastAPI(
    title="Cell Cover Generator API",
    description="通过 HTTP API 访问 Cell Cover Generator 功能",
    version="1.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局配置
GLOBAL_CONFIG_DIR = os.path.join(os.path.expanduser("~"), '.crc')
CRC_BASE_DIR = os.path.join(project_root, '.crc')
LOG_DIR = os.path.join(CRC_BASE_DIR, 'logs')
STATE_DIR = os.path.join(CRC_BASE_DIR, 'state')
METADATA_DIR = os.path.join(CRC_BASE_DIR, 'metadata')
OUTPUT_DIR = os.path.join(CRC_BASE_DIR, 'output')

# 初始化日志
os.makedirs(LOG_DIR, exist_ok=True)
logger = setup_logging(log_dir=LOG_DIR, verbose=True)

# 加载配置
default_config_path = os.path.join(project_root, 'cell_cover', 'prompts_config.json')
user_config_path = os.path.join(GLOBAL_CONFIG_DIR, 'prompts_config.json')
config = load_config(logger, default_config_path, user_config_path)

logger.info(f"服务器初始化完成，项目根目录: {project_root}")


def verify_api_key(api_key_header: Optional[str] = None):
    """验证 API 密钥（可选）"""
    server_key = os.getenv("SERVER_API_KEY")
    if server_key and api_key_header != server_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "name": "Cell Cover Generator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "create": "/api/v1/create",
            "list-concepts": "/api/v1/concepts",
            "list-tasks": "/api/v1/tasks",
            "view": "/api/v1/tasks/{task_id}",
            "action": "/api/v1/tasks/{task_id}/action",
            "describe": "/api/v1/describe"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "server": "running"}


@app.get("/api/v1/concepts")
async def list_concepts():
    """列出所有可用的创意概念"""
    try:
        from cell_cover.commands.list_cmd import handle_list_concepts

        output = StringIO()
        with redirect_stdout(output):
            handle_list_concepts(config)

        result = output.getvalue()

        # 尝试解析为 JSON
        try:
            return JSONResponse(content=json.loads(result))
        except:
            return {"success": True, "data": result.strip()}

    except Exception as e:
        logger.error(f"列出概念失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/create")
async def create_image(
    prompt: str = Form(..., description="提示词"),
    concept: Optional[str] = Form(None, description="概念键"),
    aspect_ratio: Optional[str] = Form(None, description="纵横比（如 16:9）"),
    style: Optional[str] = Form(None, description="风格（如 raw）"),
    version: Optional[str] = Form(None, description="版本（如 v6, v7）"),
    mode: str = Form("relax", description="生成模式（relax, fast, turbo）"),
    chaos: Optional[int] = Form(None, description="混乱度（0-100）"),
    stylize: Optional[int] = Form(None, description="风格化（0-1000）"),
    x_api_key: Optional[str] = None
):
    """创建新的图像生成任务"""
    try:
        api_key = get_api_key(logger)
        if not api_key:
            raise HTTPException(status_code=500, detail="TTAPI API 密钥未配置")

        # 导入处理函数
        from cell_cover.commands.create import handle_create
        import types

        args_dict = {
            "config": config,
            "logger": logger,
            "api_key": api_key,
            "concept": concept,
            "prompt": prompt,
            "variation": None,
            "aspect_ratio": aspect_ratio,
            "style": style,
            "stylize": stylize,
            "chaos": chaos,
            "weird": None,
            "seed": None,
            "version": version,
            "quality": None,
            "no": None,
            "tile": False,
            "video": False,
            "cref": None,
            "cref_weight": None,
            "sref": None,
            "sref_weight": None,
            "mode": mode,
            "clipboard": False,
            "save_prompt": False,
            "hook_url": None,
            "notify_id": None,
            "skip_prompt_check": False,
            "cwd": project_root,
            "state_dir": STATE_DIR,
            "metadata_dir": METADATA_DIR
        }

        output = StringIO()
        with redirect_stdout(output):
            handle_create(**args_dict)

        result = output.getvalue()

        # 尝试解析任务 ID
        job_id = None
        if "Job ID:" in result:
            job_id = result.split("Job ID:")[1].strip().split()[0]

        return {
            "success": True,
            "message": "任务创建成功",
            "job_id": job_id,
            "output": result.strip()
        }

    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks")
async def list_tasks(
    limit: int = 20,
    status: Optional[str] = None,
    concept: Optional[str] = None
):
    """列出任务列表"""
    try:
        from cell_cover.commands.list_tasks import handle_list_tasks
        import types

        args = types.SimpleNamespace()
        args.limit = limit
        args.status = status
        args.concept = concept
        args.sort_by = "created_at"
        args.ascending = False
        args.verbose = False

        output = StringIO()
        with redirect_stdout(output):
            handle_list_tasks(
                status=status,
                concept=concept,
                limit=limit,
                sort_by="created_at",
                ascending=False,
                verbose=False,
                logger=logger,
                crc_base_dir=CRC_BASE_DIR,
                remote=False,
                api_key=None,
                args=args
            )

        result = output.getvalue()

        return {"success": True, "data": result.strip()}

    except Exception as e:
        logger.error(f"列出任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks/{task_id}")
async def view_task(
    task_id: str,
    remote: bool = False,
    save: bool = False
):
    """查看任务详情"""
    try:
        from cell_cover.commands.view import handle_view

        output = StringIO()
        with redirect_stdout(output):
            handle_view(
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

        return {
            "success": True,
            "task_id": task_id,
            "data": result.strip()
        }

    except Exception as e:
        logger.error(f"查看任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks/{task_id}/action")
async def perform_action(
    task_id: str,
    action_code: str = Form(..., description="操作代码（如 variation1, upsample1）"),
    mode: str = Form("fast", description="生成模式"),
    wait: bool = Form(False, description="等待任务完成")
):
    """对任务执行操作"""
    try:
        api_key = get_api_key(logger)
        if not api_key:
            raise HTTPException(status_code=500, detail="TTAPI API 密钥未配置")

        if action_code not in ACTION_CHOICES:
            raise HTTPException(status_code=400, detail=f"无效的操作代码: {action_code}")

        from cell_cover.commands.action import handle_action
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
            handle_action(
                args=args,
                logger=logger,
                api_key=api_key,
                config=config,
                cwd=project_root,
                crc_base_dir=CRC_BASE_DIR,
                state_dir=STATE_DIR
            )

        result = output.getvalue()

        return {
            "success": True,
            "message": f"操作 {action_code} 已执行",
            "task_id": task_id,
            "output": result.strip()
        }

    except Exception as e:
        logger.error(f"执行操作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/describe")
async def describe_image(
    image: UploadFile = File(..., description="图像文件")
):
    """描述上传的图像"""
    try:
        api_key = get_api_key(logger)
        if not api_key:
            raise HTTPException(status_code=500, detail="TTAPI API 密钥未配置")

        from cell_cover.commands.describe import handle_describe

        # 保存上传的文件到临时位置
        temp_dir = os.path.join(OUTPUT_DIR, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, image.filename)

        with open(temp_path, "wb") as buffer:
            buffer.write(await image.read())

        # 调用 describe 命令
        output = StringIO()
        with redirect_stdout(output):
            handle_describe(
                image_path_or_url=temp_path,
                hook_url=None,
                logger=logger,
                api_key=api_key
            )

        result = output.getvalue()

        return {
            "success": True,
            "filename": image.filename,
            "data": result.strip()
        }

    except Exception as e:
        logger.error(f"描述图像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
