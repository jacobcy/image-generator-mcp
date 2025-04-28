#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TTAPI Client
------------
Low-level client for interacting with TTAPI Midjourney endpoints.
"""

import json
import time
import logging
import os
import mimetypes
import base64
from typing import Optional, Dict, Any, List, Tuple

import requests

# --- API Constants ---
TTAPI_BASE_URL = "https://api.ttapi.io/midjourney/v1"
POLL_INTERVAL_SECONDS = 5   # Interval between polling attempts
FETCH_TIMEOUT_SECONDS = 300 # Timeout for the OVERALL polling loop (in seconds)
MAX_POLL_ATTEMPTS = 60      # Max attempts (not currently used for overall timeout)

def _handle_api_error(logger: logging.Logger, response: requests.Response, context: str = "API 请求") -> None:
    """统一处理 API 请求错误"""
    error_message = f"{context}失败 - {response.status_code} {response.reason}"
    try:
        error_details = response.json()
        error_message += f" - {json.dumps(error_details)}"
        logger.error(f"Response body: {json.dumps(error_details)}")
    except json.JSONDecodeError:
        error_message += f" - 响应体无法解析为 JSON: {response.text}"
        logger.error(f"Response body (non-JSON): {response.text}")
    logger.error(error_message)

def call_imagine_api(
    logger: logging.Logger,
    prompt_data: dict,
    api_key: str,
    hook_url: Optional[str] = None,
    notify_id: Optional[str] = None,
    cref_url: Optional[str] = None
) -> Optional[str]:
    """调用 TTAPI 的 /imagine 接口提交任务

    Args:
        logger: The logging object.
        prompt_data: Dictionary containing the 'prompt' and potentially 'mode'.
        api_key: Your TTAPI API Key.
        hook_url: Optional webhook URL for async callback.
        notify_id: Optional custom ID for webhook callback.
        cref_url: Optional image reference URL for --cref parameter.

    Returns:
        The Job ID string if successful, None otherwise.
    """
    endpoint = f"{TTAPI_BASE_URL}/imagine"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    # Base payload from prompt_data
    payload = prompt_data.copy()

    # Add optional parameters
    if hook_url:
        payload['hookUrl'] = hook_url
    if notify_id:
        payload['notify_id'] = notify_id
    if cref_url:
        payload['cref'] = cref_url

    logger.info(f"向 {endpoint} 发送请求")
    logger.debug(f"请求 Payload: {json.dumps(payload)}")

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=FETCH_TIMEOUT_SECONDS)
        response.raise_for_status()

        response_data = response.json()
        logger.debug(f"API 响应: {response_data}")

        if response_data.get("status") == "SUCCESS":
            job_id = response_data.get("data", {}).get("jobId")
            if job_id:
                logger.info(f"任务提交成功，Job ID: {job_id}")
                return job_id
            else:
                logger.error("API 报告成功，但响应中缺少 Job ID")
                return None
        else:
            error_message = response_data.get("message", "未知错误")
            logger.error(f"API 报告失败: {error_message}")
            print(f"错误：API 任务提交失败 - {error_message}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"调用 /imagine API 超时 ({FETCH_TIMEOUT_SECONDS} 秒)")
        print(f"错误：调用 API 超时。")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"调用 /imagine API 时发生网络错误: {e}")
        print(f"错误：API 请求失败 - {e}")
        return None
    except json.JSONDecodeError:
        logger.error("无法解析 API 响应 (非 JSON 格式)")
        print("错误：API 响应格式无效。")
        return None
    except Exception as e:
        logger.error(f"调用 /imagine API 时发生意外错误: {e}", exc_info=True)
        print(f"错误：处理 API 请求时发生意外错误。")
        return None

def poll_for_result(
    logger: logging.Logger,
    job_id: str,
    api_key: str,
    poll_interval: int = POLL_INTERVAL_SECONDS,
    timeout: int = FETCH_TIMEOUT_SECONDS,
    max_retries_per_poll: int = 1
) -> Optional[Tuple[str, Any]]:
    """轮询 /fetch 接口获取任务结果

    Args:
        logger: The logging object.
        job_id: 任务ID
        api_key: TTAPI API密钥
        poll_interval: 轮询间隔（秒）
        timeout: 总超时时间（秒）
        max_retries_per_poll: 每次轮询的最大重试次数

    Returns:
        Optional[Tuple[str, Any]]: 成功时返回包含状态和任务数据的元组 (status, data_dict or full_response),
                                      轮询超时或完全失败时返回 None。
    """
    url = f"{TTAPI_BASE_URL}/fetch"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"jobId": job_id}
    start_time = time.time()

    logger.info(f"开始轮询任务结果，Job ID: {job_id}")
    logger.debug(f"轮询间隔: {poll_interval}s, 超时: {timeout}s")
    print(f"正在轮询任务结果 (Job ID: {job_id})... (间隔: {poll_interval}s, 超时: {timeout}s)")

    poll_count = 0
    while time.time() - start_time < timeout:
        poll_count += 1
        logger.debug(f"轮询次数: {poll_count}")

        current_result = None
        poll_successful = False

        for attempt in range(max_retries_per_poll + 1):
            try:
                if attempt > 0:
                    logger.info(f"第 {attempt} 次重试轮询请求...")
                    print(f"  第 {attempt} 次重试轮询请求...")
                    time.sleep(1)

                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                poll_successful = True
                current_result = result
                logger.debug(f"  成功获取轮询结果 (第 {poll_count} 次尝试): {result!r}")
                break

            except requests.exceptions.Timeout:
                logger.warning("  轮询请求超时。")
                print("  轮询请求超时，将在下次尝试。")
                if attempt < max_retries_per_poll:
                    continue
                else:
                    logger.error(f"轮询 Job ID {job_id} 在第 {poll_count} 次尝试时，所有重试均超时。")
            except requests.exceptions.RequestException as e:
                logger.error(f"  轮询 /fetch API 时出错: {e}")
                print(f"  轮询 /fetch API 时出错: {e}")
                if attempt < max_retries_per_poll:
                    continue
                else:
                    logger.error(f"轮询 Job ID {job_id} 在第 {poll_count} 次尝试时，所有重试均失败 (RequestException)。")
            except json.JSONDecodeError as e:
                logger.error(f"错误：无法解析来自 /fetch API 的响应。")
                logger.error(f"解析错误: {e}")
                print(f"错误：无法解析来自 /fetch API 的响应。")
                if attempt < max_retries_per_poll:
                    continue
                else:
                    logger.error(f"轮询 Job ID {job_id} 在第 {poll_count} 次尝试时，所有重试均失败 (JSONDecodeError)。")

        if poll_successful and current_result:
            status = current_result.get("status")
            data = current_result.get("data", {})
            progress = data.get("progress", "N/A") if isinstance(data, dict) else "N/A"

            logger.debug(f"当前状态: {status}, 进度: {progress}%")
            print(f"  当前状态: {status}, 进度: {progress}%")

            if status == "SUCCESS":
                if isinstance(data, dict) and data.get("cdnImage"):
                    logger.info("任务完成，获取到图像 URL")
                    logger.debug(f"  poll_for_result 准备返回成功元组: ('SUCCESS', {data!r})")
                    return ("SUCCESS", data)
                else:
                    logger.error("任务成功但未找到图像 URL 或 data 格式不正确")
                    logger.debug(f"  poll_for_result 准备返回 None (SUCCESS but no cdnImage/data)")
                    return None
            elif status == "FAILED":
                error_message = current_result.get("message", "未知错误")
                logger.warning(f"任务失败: {error_message}")
                print(f"  任务状态: 失败 - {error_message}")
                logger.debug(f"  poll_for_result 准备返回失败元组: ('FAILED', {current_result!r})")
                return ("FAILED", current_result)

        elif not poll_successful:
             logger.error(f"在第 {poll_count} 次轮询中，所有重试均失败。")

        time.sleep(poll_interval)

    logger.error(f"轮询超时 ({timeout} 秒)")
    print(f"错误：轮询超时 ({timeout} 秒)")
    logger.debug(f"  poll_for_result 准备返回 None (Timeout)")
    return None

def fetch_job_list_from_ttapi(
    api_key: str,
    logger: logging.Logger,
    page: int = 1,
    limit: int = 10
) -> Optional[List[Dict[str, Any]]]:
    """从 TTAPI 获取任务列表

    Args:
        api_key: TTAPI API密钥
        logger: 日志记录器
        page: 页码 (默认: 1)
        limit: 每页数量 (默认: 10)

    Returns:
        Optional[List[Dict[str, Any]]]: 成功时返回任务列表，失败时返回 None
    """
    endpoint = f"{TTAPI_BASE_URL}/list"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "page": page,
        "limit": limit
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "SUCCESS":
            jobs = result.get("data", {}).get("jobs", [])
            logger.info(f"成功获取任务列表，共 {len(jobs)} 个任务")
            return jobs
        else:
            error_message = result.get("message", "未知错误")
            logger.error(f"获取任务列表失败: {error_message}")
            return None

    except Exception as e:
        logger.error(f"获取任务列表时发生错误: {e}")
        return None

def call_action_api(
    logger: logging.Logger,
    api_key: str,
    original_job_id: str,
    action: str,
    hook_url: Optional[str] = None,
    mode: Optional[str] = None
) -> Optional[str]:
    """调用 TTAPI 的 /action 接口执行操作（放大、变体等）

    Args:
        logger: 日志记录器
        api_key: TTAPI API密钥
        original_job_id: 原始任务ID
        action: 操作类型 (U1-U4, V1-V4)
        hook_url: 可选的回调 URL
        mode: 可选的操作模式

    Returns:
        Optional[str]: 成功时返回新任务ID，失败时返回 None
    """
    endpoint = f"{TTAPI_BASE_URL}/action"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "jobId": original_job_id,
        "action": action
    }
    if hook_url:
        payload["hookUrl"] = hook_url
    if mode:
        payload["mode"] = mode

    # Log the final payload before sending
    logger.debug(f"发送到 /action 的 Payload: {json.dumps(payload)}")

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        # Check for HTTP errors
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "SUCCESS":
            new_job_id = result.get("data", {}).get("jobId")
            if new_job_id:
                logger.info(f"操作 {action} 提交成功，新任务 ID: {new_job_id}")
                return new_job_id
            else:
                logger.error("API 报告成功但未返回新任务 ID")
                return None
        else:
            # Handle application-level failure reported by API
            error_message = result.get("message", "未知错误")
            logger.error(f"操作 {action} 失败 (API Status != SUCCESS): {error_message}")
            logger.debug(f"Full API failure response: {result}") # Log full response on failure
            print(f"错误：操作 {action} 失败 - {error_message}")
            return None

    except requests.exceptions.Timeout as e:
        logger.error(f"调用 /action API 超时: {e}")
        print(f"错误：调用 /action API 超时。")
        return None
    except requests.exceptions.RequestException as e:
        # Log detailed HTTP error if response is available
        error_msg = f"调用 /action API 时发生网络错误: {e}"
        if e.response is not None:
            error_msg += f" | Status Code: {e.response.status_code}"
            try:
                # Try to get JSON error details
                response_json = e.response.json()
                error_msg += f" | Response: {json.dumps(response_json)}"
            except json.JSONDecodeError:
                # Fallback to raw text if not JSON
                error_msg += f" | Response: {e.response.text}"
        logger.error(error_msg)
        print(f"错误：API 请求失败，请检查日志获取详细信息。 ({e})") # User-friendly message
        return None
    except json.JSONDecodeError as e:
        logger.error(f"无法解析 /action API 响应 (非 JSON): {e}")
        if 'response' in locals() and response:
             logger.error(f"原始响应文本: {response.text}")
        print("错误：API 响应格式无效。")
        return None
    except Exception as e:
        logger.error(f"调用 /action API 时发生意外错误: {e}", exc_info=True)
        print(f"错误：处理 /action API 请求时发生意外错误。")
        return None

def fetch_seed_from_ttapi(
    logger: logging.Logger,
    api_key: str,
    job_id: str
) -> Optional[int]:
    """从 TTAPI 获取任务的 seed 值

    Args:
        logger: 日志记录器
        api_key: TTAPI API密钥
        job_id: 任务ID

    Returns:
        Optional[int]: 成功时返回 seed 值，失败时返回 None
    """
    endpoint = f"{TTAPI_BASE_URL}/fetch"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"jobId": job_id}

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "SUCCESS":
            seed = result.get("data", {}).get("seed")
            if seed is not None:
                logger.info(f"成功获取 seed 值: {seed}")
                return seed
            else:
                logger.warning(f"任务 {job_id} 未找到 seed 值")
                return None
        else:
            error_message = result.get("message", "未知错误")
            logger.error(f"获取 seed 值失败: {error_message}")
            return None

    except Exception as e:
        logger.error(f"获取 seed 值时发生错误: {e}")
        return None

def check_prompt(
    logger: logging.Logger,
    prompt: str,
    api_key: str
) -> bool:
    """检查提示词是否违规

    Args:
        logger: 日志记录器
        prompt: 要检查的提示词
        api_key: TTAPI API密钥

    Returns:
        bool: True 表示通过检查，False 表示违规或检查失败
    """
    endpoint = f"{TTAPI_BASE_URL}/promptCheck"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt}

    logger.info("开始检查提示词是否违规...")
    logger.debug(f"提示词: {prompt}")

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "SUCCESS":
            logger.info("提示词检查通过")
            return True
        else:
            error_message = result.get("message", "未知错误")
            logger.error(f"提示词检查未通过: {error_message}")
            print(f"错误：提示词检查未通过 - {error_message}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"提示词检查请求失败: {e}")
        print(f"错误：提示词检查请求失败 - {e}")
        return False
    except Exception as e:
        logger.error(f"提示词检查过程中发生错误: {e}")
        print(f"错误：提示词检查过程中发生错误 - {e}")
        return False

def call_blend_api(
    logger: logging.Logger,
    api_key: str,
    img_base64_array: List[str],
    dimensions: Optional[str] = None,
    mode: Optional[str] = None,
    hook_url: Optional[str] = None,
    get_u_images: Optional[bool] = None
) -> Optional[str]:
    """调用 TTAPI 的 /blend 接口提交图像合成任务

    Args:
        logger: 日志记录器
        api_key: TTAPI API密钥
        img_base64_array: 包含 2-5 个 Base64 编码图像字符串的列表 (带 data URI 前缀)
        dimensions: 图像比例 ('PORTRAIT', 'SQUARE', 'LANDSCAPE')
        mode: 生成模式 ('relax', 'fast', 'turbo')
        hook_url: 可选的回调 URL
        get_u_images: 是否获取四张小图 (可选, 默认 False)

    Returns:
        Optional[str]: 成功时返回新任务ID，失败时返回 None
    """
    endpoint = f"{TTAPI_BASE_URL}/blend"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "imgBase64Array": img_base64_array
    }
    if dimensions:
        payload["dimensions"] = dimensions
    if mode:
        payload["mode"] = mode
    if hook_url:
        payload["hookUrl"] = hook_url
    if get_u_images is not None:
        payload["getUImages"] = get_u_images

    logger.info(f"向 {endpoint} 发送 Blend 请求 ({len(img_base64_array)} 张图片)")
    # Avoid logging the full base64 array for brevity and security
    logger.debug(f"Blend Payload (excluding base64): {{dimensions: {dimensions}, mode: {mode}, hookUrl: {hook_url}, getUImages: {get_u_images}}}")

    try:
        # Increase timeout slightly for potential larger uploads
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "SUCCESS":
            job_id = result.get("data", {}).get("jobId")
            if job_id:
                logger.info(f"Blend 任务提交成功，新任务 ID: {job_id}")
                return job_id
            else:
                logger.error("Blend API 报告成功但未返回任务 ID")
                return None
        else:
            error_message = result.get("message", "未知错误")
            logger.error(f"Blend 任务提交失败: {error_message}")
            print(f"错误：Blend 任务提交失败 - {error_message}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"调用 /blend API 超时")
        print(f"错误：调用 /blend API 超时。")
        return None
    except requests.exceptions.RequestException as e:
        # Log detailed error if possible
        error_context = str(e)
        try:
            error_context += f" - Response: {response.text}"
        except:
             pass # Ignore if response doesn't exist
        logger.error(f"调用 /blend API 时发生网络错误: {error_context}")
        print(f"错误：Blend API 请求失败 - {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"无法解析 /blend API 响应 (非 JSON 格式): {response.text if 'response' in locals() else 'N/A'}")
        print("错误：Blend API 响应格式无效。")
        return None
    except Exception as e:
        logger.error(f"处理 /blend 响应时发生意外错误: {e}", exc_info=True)
        print(f"错误：处理 Blend 请求时发生意外错误。")
        return None

def call_describe_api(
    logger: logging.Logger,
    api_key: str,
    image_path_or_url: str,
    hook_url: Optional[str] = None,
    timeout: int = 300
) -> Optional[str]:
    """调用 TTAPI 的 /describe 接口提交图像描述任务

    Args:
        logger: 日志记录器
        api_key: TTAPI API密钥
        image_path_or_url: 本地图像路径或公共可访问的图像 URL
        hook_url: 可选的回调 URL
        timeout: 请求超时时间 (秒)

    Returns:
        Optional[str]: 成功时返回新任务ID，失败时返回 None
    """
    endpoint = f"{TTAPI_BASE_URL}/describe"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {}

    if image_path_or_url.startswith(('http://', 'https://')):
        payload['url'] = image_path_or_url
        logger.info(f"使用提供的 URL 进行 Describe: {image_path_or_url}")
    elif os.path.exists(image_path_or_url):
        try:
            mime_type, _ = mimetypes.guess_type(image_path_or_url)
            if not mime_type or not mime_type.startswith('image'):
                logger.warning(f"无法确定图片类型或文件不是图片: {image_path_or_url} (MIME: {mime_type}) - 尝试使用 image/png")
                mime_type = 'image/png' # Default assumption

            with open(image_path_or_url, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                payload['base64'] = f"data:{mime_type};base64,{encoded_string}"
            logger.info(f"已编码本地图片用于 Describe: {image_path_or_url}")
        except Exception as e:
            logger.error(f"编码本地图片时出错 {image_path_or_url}: {e}")
            print(f"错误：编码本地图片时出错 {image_path_or_url}: {e}")
            return None
    else:
        logger.error(f"提供的路径既不是有效 URL 也不是存在的本地文件: {image_path_or_url}")
        print(f"错误：无效的图像路径或 URL: {image_path_or_url}")
        return None

    if hook_url:
        payload["hookUrl"] = hook_url
    payload["timeout"] = timeout # Add timeout to payload

    logger.info(f"向 {endpoint} 发送 Describe 请求")
    logger.debug(f"Describe Payload (excluding base64): { {k: v for k, v in payload.items() if k != 'base64'} }")

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout + 10) # Add buffer to request timeout
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "SUCCESS":
            job_id = result.get("data", {}).get("jobId")
            if job_id:
                logger.info(f"Describe 任务提交成功，新任务 ID: {job_id}")
                return job_id
            else:
                logger.error("Describe API 报告成功但未返回任务 ID")
                return None
        else:
            error_message = result.get("message", "未知错误")
            logger.error(f"Describe 任务提交失败: {error_message}")
            print(f"错误：Describe 任务提交失败 - {error_message}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"调用 /describe API 超时 ({timeout} 秒)")
        print(f"错误：调用 /describe API 超时。")
        return None
    except requests.exceptions.RequestException as e:
        error_context = str(e)
        try: error_context += f" - Response: {response.text}"
        except: pass
        logger.error(f"调用 /describe API 时发生网络错误: {error_context}")
        print(f"错误：Describe API 请求失败 - {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"无法解析 /describe API 响应: {response.text if 'response' in locals() else 'N/A'}")
        print("错误：Describe API 响应格式无效。")
        return None
    except Exception as e:
        logger.error(f"处理 /describe 响应时发生意外错误: {e}", exc_info=True)
        print(f"错误：处理 Describe 请求时发生意外错误。")
        return None