# -*- coding: utf-8 -*-
import logging
import os
import re
import uuid
import requests
import webbrowser

# 从 utils 导入必要的函数 - 使用统一的元数据管理模块
from ..utils.metadata_manager import (
    find_initial_job_info,
    trace_job_history,
    update_job_metadata,
    save_image_metadata, # Import needed for fallback save
    remove_job_metadata # Import needed for removing failed tasks
)
from ..utils.api import normalize_api_response
from ..utils.api_client import poll_for_result
from ..utils.filesystem_utils import (
    read_last_job_id,
    write_last_succeed_job_id,
    write_last_job_id,
    read_last_succeed_job_id
)
# download_and_save_image now handles saving metadata via metadata_manager
from ..utils.image_handler import download_and_save_image
from ..utils.image_metadata import load_all_metadata, _build_metadata_index # Added load & build
from ..utils.config import get_api_key # Import from config instead
from ..utils.metadata_manager import _generate_expected_filename # Added import

logger = logging.getLogger(__name__)

def resolve_job_identifier(logger, raw_identifier, metadata_dir):
    """
    解析并查找各种可能的标识符格式：完整Job ID、短ID、图片文件名等。

    Args:
        logger: 日志记录器
        raw_identifier: 用户提供的标识符
        metadata_dir: 元数据目录

    Returns:
        dict: 包含 'job_id' 和 'local_job_info' 的字典，如果未能解析则返回 None
    """
    if not raw_identifier:
        logger.error("未提供标识符")
        return None

    # 检查是否是完整的UUID格式（36个字符，包含连字符）
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    # 检查是否是6位短ID（通常用作Job ID的前6位）
    short_id_pattern = re.compile(r'^[0-9a-f]{6}$', re.IGNORECASE)

    # 首先，尝试在本地查找
    local_job_info = find_initial_job_info(logger, raw_identifier, metadata_dir)

    if local_job_info:
        job_id = local_job_info.get("job_id")
        if job_id:
            logger.info(f"通过标识符 '{raw_identifier}' 找到本地任务，Job ID: {job_id}")
            return {"job_id": job_id, "local_job_info": local_job_info}
        else:
            logger.warning(f"在本地找到的任务 '{raw_identifier}' 缺少 Job ID。")
            return None

    # 如果本地没找到但看起来像完整的Job ID
    if uuid_pattern.match(raw_identifier):
        logger.info(f"标识符 '{raw_identifier}' 看起来像一个完整的 Job ID，但在本地未找到记录。")
        return {"job_id": raw_identifier, "local_job_info": None}

    # 如果是6位短ID但本地没找到
    if short_id_pattern.match(raw_identifier):
        logger.warning(f"标识符 '{raw_identifier}' 看起来像一个6位短ID，但在本地未找到唯一匹配记录。")

    # 如果可能是图像文件名（加上.png或不加）
    if raw_identifier.endswith('.png') or len(raw_identifier) > 0:
        # 已经在find_initial_job_info中尝试过按文件名查找，这里只是给出更明确的日志
        logger.warning(f"无法通过文件名 '{raw_identifier}' 在本地找到任务记录。")

    logger.error(f"无法解析标识符 '{raw_identifier}' 为有效的任务ID或文件名。")
    return None

def update_local_job_history(logger, job_id, api_result, metadata_dir: str = None):
    """
    用API返回的结果更新本地任务信息。
    如果任务不存在，则创建新记录。

    Args:
        logger: 日志记录器
        job_id: 任务ID
        api_result: API返回的任务结果数据
        metadata_dir: 元数据目录

    Returns:
        bool: 更新或创建是否成功
    """
    if not api_result or not isinstance(api_result, dict):
        logger.error("无法更新本地历史记录：API结果无效或为空")
        return False

    # 使用标准化函数处理API返回值
    normalized_result = normalize_api_response(logger, api_result)

    if normalized_result:
        # 先尝试查找任务
        local_job_info = find_initial_job_info(logger, job_id, metadata_dir)

        # 处理 UNKNOWN 和 SUCCESS 状态
        status = normalized_result.get('status')
        url = normalized_result.get('url')
        if (status == 'UNKNOWN' or status == 'SUCCESS') and url:
            logger.info(f"任务 {job_id} 状态为 {status} 但有图像 URL，将状态设置为 completed")
            normalized_result['status'] = 'completed'

        if local_job_info:
            # 如果任务存在，则更新
            logger.info(f"使用标准化的API数据更新本地任务 {job_id}")
            logger.debug(f"标准化后的更新数据: {normalized_result}")
            return update_job_metadata(logger, job_id, normalized_result)
        else:
            # 如果任务不存在，则创建新记录
            logger.info(f"任务 {job_id} 在本地不存在，创建新记录")

            # 提取必要的字段
            prompt = normalized_result.get('prompt', '')
            concept = normalized_result.get('concept', 'unknown')
            variations = normalized_result.get('variations', '')
            global_styles = normalized_result.get('global_styles', '')
            seed = normalized_result.get('seed')
            original_job_id = normalized_result.get('original_job_id')
            action_code = normalized_result.get('action_code')
            status = normalized_result.get('status', 'completed')

            # 使用 save_image_metadata 创建新记录
            return save_image_metadata(
                logger, str(uuid.uuid4()), job_id, None, None, url,
                prompt, concept, metadata_dir, variations, global_styles,
                None, seed, original_job_id, action_code,
                status
            )
    else:
        logger.warning(f"API返回数据标准化后没有需要更新的字段")
        return False


from typing import Optional
def handle_view(
    identifier: Optional[str] = None,
    last_job: bool = False,
    last_succeed: bool = False,
    remote: bool = False,
    save: bool = False,
    local_only: bool = False,
    verbose: bool = False,
    history: bool = False,
    metadata_dir: str = None,
    state_dir: str = None
):
    """处理 'view' 命令，根据标识符查看任务状态和结果。"""

    # 初始化 logger 和 api_key
    import logging
    logger = logging.getLogger(__name__)
    api_key = get_api_key(logger)

    # --- 步骤 3.1: 统一标识符解析入口 ---
    raw_identifier = None

    if last_job:
        logger.info("使用上次提交的任务ID")
        raw_identifier = read_last_job_id(logger)
        if not raw_identifier:
            logger.error("找不到上次提交的任务ID")
            print("错误：找不到上次提交的任务ID，请确保之前有成功提交的任务。")
            return 1
        logger.info(f"获取到上次任务ID: {raw_identifier}")
    elif last_succeed:
        logger.info("使用上次成功的任务ID")
        raw_identifier = read_last_succeed_job_id(logger)
        if not raw_identifier:
            logger.error("找不到上次成功的任务ID")
            print("错误：找不到上次成功的任务ID，请确保之前有成功完成的任务。")
            return 1
        logger.info(f"获取到上次成功任务ID: {raw_identifier}")
    elif identifier:
        raw_identifier = identifier
        logger.info(f"使用提供的标识符: {raw_identifier}")
    else:
        logger.error("未提供标识符，也未指定使用上次的任务")
        print("错误：必须提供任务标识符、图像文件名，或使用 --last-job / --last-succeed 选项。")
        return 1

    # 解析标识符
    resolved = resolve_job_identifier(logger, raw_identifier, metadata_dir)
    if not resolved:
        logger.error(f"无法解析标识符: {raw_identifier}")
        print(f"错误：无法确定 '{raw_identifier}' 对应的任务ID，请提供完整的任务ID、正确的图像文件名或短ID。")
        return 1

    job_id_to_query = resolved["job_id"]
    initial_local_info = resolved["local_job_info"]

    # --- 显示基本信息 ---
    print("\n--- 任务详情 ---")
    print(f"  标识符:     {raw_identifier}")
    print(f"  Job ID:     {job_id_to_query}")

    # --- 处理 --history 选项 ---
    if history and initial_local_info:
        history_chain = trace_job_history(logger, job_id_to_query)
        if history_chain:
            print(f"\n  --- 任务历史 ({len(history_chain)} 个任务) ---")
            for i, task in enumerate(history_chain):
                task_job_id = task.get("job_id", "未知")
                task_action = task.get("action_code", "")
                task_concept = task.get("concept", "未知")
                chain_indicator = "  └─ " if i == len(history_chain) - 1 else "  ├─ "
                if i == 0:  # 根任务
                    print(f"  [根] {task_job_id} - {task_concept}")
                elif task_action:  # Action 任务
                    print(f"{chain_indicator}[通过 {task_action}] {task_job_id} - {task_concept}")
                else:  # 其他类型的任务
                    print(f"{chain_indicator}{task_job_id} - {task_concept}")

    # --- 步骤 3.2: 区分处理流程 ---
    # 显示本地信息（如果有）
    if initial_local_info:
        print("\n  --- 本地元数据 ---")
        if initial_local_info.get("filename"):
            print(f"  本地文件名: {initial_local_info['filename']}")
        online_url = initial_local_info.get("url") or initial_local_info.get("cdnImage")
        if online_url:
            print(f"  在线图像:   {online_url}")
        action_code = initial_local_info.get("action_code")
        original_job_id = initial_local_info.get("original_job_id")
        concept = initial_local_info.get("concept")
        if concept:
            if action_code and original_job_id:
                print(f"  概念:       {concept} (继承自 {original_job_id[:8]}..)")
            else:
                print(f"  概念:       {concept}")
        if action_code:
            print(f"  触发动作:   {action_code}")
        if original_job_id:
            print(f"  源任务 ID:  {original_job_id} (对此任务执行了 {action_code or '未知操作'})")
        prompt_local = initial_local_info.get("prompt")
        if prompt_local:
            truncated_prompt = prompt_local[:80] + ('...' if len(prompt_local) > 80 else '')
            print(f"  原始提示词: {truncated_prompt}")
        if initial_local_info.get("seed") is not None:
            print(f"  Seed:       {initial_local_info['seed']}")
        if action_code and (initial_local_info.get("variations") or initial_local_info.get("global_styles")):
            if initial_local_info.get("variations"):
                print(f"  变体:       {initial_local_info['variations']}")
            if initial_local_info.get("global_styles"):
                print(f"  风格:       {initial_local_info['global_styles']}")
    elif not remote and not save:
        print(f"\n警告：在本地元数据中找不到任务 '{raw_identifier}' 的详细信息。")

    # --- 步骤 3.3 (Remote + Save): 从API获取并保存 ---
    if remote or save:
        if not api_key:
            logger.error("缺少API密钥，无法执行远程操作")
            print("错误：未提供API密钥。为了访问远程API，请设置TTAPI_API_KEY环境变量。")
            return 1
        print("\n正在从远程服务器获取任务状态...")
        try:
            poll_response = poll_for_result(logger, job_id_to_query, api_key)
            if poll_response:
                final_status, api_data = poll_response
                print(f"  远程状态:   {final_status}")
                if save and final_status == 'FAILED':
                    if remove_job_metadata(logger, job_id_to_query):
                        print(f"已删除失败任务 {job_id_to_query} 的元数据记录。")
                    else:
                        print(f"警告：无法删除失败任务 {job_id_to_query} 的元数据记录。")
                    return 0
                latest_result = normalize_api_response(logger, api_data)
                print("\n  --- API 最新状态 ---")
                progress = latest_result.get('progress')
                image_url = latest_result.get('url')
                seed = latest_result.get('seed')
                prompt_api = latest_result.get('prompt')
                actions = api_data.get('components') if final_status == 'FAILED' and isinstance(api_data, dict) else latest_result.get('actions')
                msg = api_data.get('message') if final_status == 'FAILED' and isinstance(api_data, dict) else latest_result.get('msg')
                print(f"  状态:       {final_status}")
                if progress is not None:
                    print(f"  进度:       {progress}%" if progress != "N/A" else "  进度:       N/A")
                if image_url:
                    print(f"  图像 URL:   {image_url}")
                if seed is not None:
                    print(f"  Seed:       {seed}")
                if prompt_api and prompt_api != "":
                    truncated_prompt_api = prompt_api[:80] + ('... ' if len(prompt_api) > 80 else '')
                    print(f"  提示词:     {truncated_prompt_api}")
                if actions:
                    print(f"  可用动作:   {', '.join(actions) if isinstance(actions, list) else actions}")
                if msg:
                    print(f"  消息:       {msg}")
                if save:
                    logger.info("使用API数据更新本地任务记录")
                    update_local_job_history(logger, job_id_to_query, api_data, metadata_dir)
                    if final_status == "SUCCESS" and image_url:
                        logger.info("--save 条件满足 (SUCCESS 状态和图像 URL)。")
                        print(f"任务已成功完成，尝试下载并保存图像: {image_url}")
                        prompt_text = (initial_local_info.get("prompt") if initial_local_info else None) or latest_result.get("prompt", f"Job: {job_id_to_query}")
                        concept = (initial_local_info.get("concept") if initial_local_info else None) or latest_result.get("concept", "unknown")
                        variations = (initial_local_info.get("variations") if initial_local_info else None) or latest_result.get("variations", "")
                        styles = (initial_local_info.get("global_styles") if initial_local_info else None) or latest_result.get("global_styles", "")
                        original_job_id_link = (initial_local_info.get("original_job_id") if initial_local_info else None) or latest_result.get("original_job_id")
                        action_code_done = (initial_local_info.get("action_code") if initial_local_info else None) or latest_result.get("action_code")
                        normalized_save_data = normalize_api_response(logger, api_data)
                        normalized_save_data['job_id'] = job_id_to_query
                        try:
                            all_tasks = load_all_metadata(logger, metadata_dir)
                            all_tasks_index = _build_metadata_index(all_tasks)
                            expected_filename = _generate_expected_filename(logger, normalized_save_data, all_tasks_index)
                        except Exception as e:
                            logger.error(f"为任务 {job_id_to_query} 生成期望文件名时出错: {e}，将使用 job_id 作为备用名。")
                            expected_filename = f"{job_id_to_query}.png"
                        logger.info("下载图像...")
                        download_success, saved_path, _ = download_and_save_image(
                            logger,
                            image_url,
                            job_id_to_query,
                            prompt_text,
                            expected_filename,
                            concept,
                            variations,
                            styles,
                            original_job_id_link,
                            action_code_done,
                            None,
                            seed
                        )
                        if download_success:
                            logger.info(f"图像已下载到: {saved_path}")
                            print(f"图像已下载到: {saved_path}")
                            write_last_succeed_job_id(logger, job_id_to_query, state_dir)
                            return 0
                        else:
                            logger.error("图像下载或保存失败")
                            print("错误：图像下载或保存失败。")
                            return 1
                    else:
                        if final_status != "SUCCESS":
                            logger.warning(f"无法保存图像：任务状态为 {final_status} (非 SUCCESS)。")
                            print(f"警告：无法保存图像，任务状态为 {final_status}。")
                        elif not image_url:
                            logger.warning("无法保存图像：API响应中没有图像URL。")
                            print("警告：API响应中没有图像URL，无法保存图像。")
                        return 1
            else:
                logger.error(f"轮询任务 {job_id_to_query} 失败或超时。")
                print(f"错误：轮询任务 {job_id_to_query} 失败或超时。")
                if save:
                    print("警告：由于轮询失败，--save 操作无法完成。")
                return 1
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"远程服务器未找到任务 (Job ID: {job_id_to_query})")
                print(f"错误：远程服务器未找到任务 (Job ID: {job_id_to_query})")
            else:
                logger.error(f"API请求失败 ({e.response.status_code}): {str(e)}")
                print(f"错误：API请求失败 ({e.response.status_code}) - {str(e)}")
            if save:
                print("警告：由于API错误，--save 操作无法完成。")
            return 1
        except Exception as e:
            logger.error(f"从API获取任务 {job_id_to_query} 时发生错误: {str(e)}")
            print(f"错误：从API获取任务时发生错误 - {str(e)}")
            if save:
                print("警告：由于异常，--save 操作无法完成。")
            return 1

    # 如果只是查看本地，返回成功
    if not remote and not save and initial_local_info:
        online_url = initial_local_info.get("url") or initial_local_info.get("cdnImage")
        if not online_url and not local_only:
            try:
                print(f"\n正在尝试获取任务 {job_id_to_query} 的在线URL...")
                api_result = poll_for_result(logger, job_id_to_query, api_key)
                if api_result:
                    normalized_result = normalize_api_response(logger, api_result)
                    online_url = normalized_result.get('url')
                    if online_url:
                        print(f"  在线图像:   {online_url}")
                        update_local_job_history(logger, job_id_to_query, api_result, metadata_dir)
            except Exception as e:
                logger.warning(f"获取在线URL时发生错误: {str(e)}")
        elif local_only and not online_url:
            logger.info("根据--local-only参数设置，跳过获取在线URL")
            print("提示：根据--local-only参数设置，仅使用本地数据")
            return 0
        return 0
    return 0

