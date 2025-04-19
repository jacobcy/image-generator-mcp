#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TTAPI API Interaction Utilities
-------------------------------
Functions for calling the TTAPI Midjourney endpoints.
"""

import json
import time
import logging
import requests # Make sure requests is imported

# --- API Constants ---
TTAPI_BASE_URL = "https://api.ttapi.io/midjourney/v1"
POLL_INTERVAL_SECONDS = 5   # Interval between polling attempts
FETCH_TIMEOUT_SECONDS = 300 # Timeout for the OVERALL polling loop (in seconds)
MAX_POLL_ATTEMPTS = 60      # Max attempts (not currently used for overall timeout)

# Note: logger needs to be passed into the functions or initialized differently

# --- Helper Functions ---
def _handle_api_error(logger, response, context="API 请求"):
    """统一处理 API 请求错误"""
    error_message = f"{context}失败 - {response.status_code} {response.reason}"
    try:
        error_details = response.json() #尝试解析 JSON 响应体
        error_message += f" - {json.dumps(error_details)}"
        logger.error(f"Response body: {json.dumps(error_details)}") # Log detailed error
    except json.JSONDecodeError:
        error_message += f" - 响应体无法解析为 JSON: {response.text}"
        logger.error(f"Response body (non-JSON): {response.text}")
    logger.error(error_message)
    # This helper itself doesn't return None, the caller should handle the return
    # return None # Removed return None

def call_imagine_api(logger, prompt_data, api_key, hook_url=None, notify_id=None, cref_url=None):
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
    # Base payload from prompt_data (contains prompt and mode)
    payload = prompt_data.copy()

    # Add optional parameters to the payload
    if hook_url:
        payload['hookUrl'] = hook_url
    if notify_id:
        payload['notify_id'] = notify_id
    if cref_url:
        # Ensure cref is only sent if v6 is explicitly or implicitly used?
        # TTAPI docs say cref is only for v6. We assume the user provides
        # --version v6 when using --cref for now.
        # A check could be added here if prompt_data included the version.
        payload['cref'] = cref_url

    logger.info(f"向 {endpoint} 发送请求")
    logger.debug(f"请求 Payload: {json.dumps(payload)}") # Be careful logging potentially large prompts

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=FETCH_TIMEOUT_SECONDS)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

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

def poll_for_result(logger, job_id, api_key, poll_interval=POLL_INTERVAL_SECONDS, timeout=FETCH_TIMEOUT_SECONDS, max_retries_per_poll=1):
    """轮询 /fetch 接口获取任务结果

    参数:
    - logger: The logging object.
    - job_id: 任务ID
    - api_key: TTAPI API密钥
    - poll_interval: 轮询间隔（秒）
    - timeout: 总超时时间（秒）
    - max_retries_per_poll: 每次轮询的最大重试次数（默认为1）

    返回值:
        成功时返回包含任务数据的字典 (e.g., {'cdnImage': 'url', ...})
        失败或超时时返回 None
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

        # 重试逻辑 for each poll attempt
        current_result = None
        poll_successful = False
        for attempt in range(max_retries_per_poll + 1):
            try:
                if attempt > 0:
                    logger.info(f"第 {attempt} 次重试轮询请求...")
                    print(f"  第 {attempt} 次重试轮询请求...")
                    time.sleep(1)  # 重试前等待 1 秒

                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                poll_successful = True # Mark poll as successful if we get here
                current_result = result # Store the result
                break # Exit retry loop on success

            except requests.exceptions.Timeout:
                logger.warning("  轮询请求超时。")
                print("  轮询请求超时，将在下次尝试。")
                # If still have retries, continue inner loop
                if attempt < max_retries_per_poll:
                    continue
                else: # Exhausted retries for this poll
                     logger.error(f"轮询 Job ID {job_id} 在第 {poll_count} 次尝试时，所有重试均超时。")
                     # Fall through to wait for the next poll interval
            except requests.exceptions.RequestException as e:
                logger.error(f"  轮询 /fetch API 时出错: {e}")
                print(f"  轮询 /fetch API 时出错: {e}")
                # If still have retries, continue inner loop
                if attempt < max_retries_per_poll:
                    continue
                else: # Exhausted retries for this poll
                    logger.error(f"轮询 Job ID {job_id} 在第 {poll_count} 次尝试时，所有重试均失败 (RequestException)。")
                    # Fall through to wait for the next poll interval
            except json.JSONDecodeError as e:
                logger.error(f"错误：无法解析来自 /fetch API 的响应。")
                logger.error(f"解析错误: {e}")
                print(f"错误：无法解析来自 /fetch API 的响应。")
                 # If still have retries, continue inner loop
                if attempt < max_retries_per_poll:
                    continue
                else: # Exhausted retries for this poll
                    logger.error(f"轮询 Job ID {job_id} 在第 {poll_count} 次尝试时，所有重试均失败 (JSONDecodeError)。")
                    # Fall through to wait for the next poll interval

        # --- Process the result of the poll attempt (if successful) ---
        if poll_successful and current_result:
            status = current_result.get("status")
            data = current_result.get("data", {})
            progress = data.get("progress", "N/A") if isinstance(data, dict) else "N/A"

            logger.debug(f"当前状态: {status}, 进度: {progress}%")
            print(f"  当前状态: {status}, 进度: {progress}%")

            if status == "SUCCESS":
                success_msg = "任务成功完成!"
                logger.info(success_msg)
                print(success_msg)
                if isinstance(data, dict) and data.get("cdnImage"):
                    image_url = data["cdnImage"]
                    logger.info(f"获取到图像 URL: {image_url}")
                    # Return the whole data dict on success for more flexibility
                    return data
                else:
                    error_msg = "错误：任务成功但未找到 cdnImage URL 或数据格式错误。"
                    logger.error(error_msg)
                    logger.error(f"完整响应: {current_result}")
                    print(error_msg)
                    # print(f"完整响应: {current_result}") # Already logged
                    return None # Indicate logical failure
            elif status == "FAILED":
                error_msg = f"任务失败: {current_result.get('message', '未知原因')}"
                logger.error(error_msg)
                logger.error(f"完整响应: {current_result}")
                print(error_msg)
                # print(f"完整响应: {current_result}") # Already logged
                return None # Indicate failure
            elif status in ["PENDING_QUEUE", "ON_QUEUE"]:
                # Continue polling
                pass
            else: # Unknown or unexpected status
                warning_msg = f"收到未知或意外的状态: {status}"
                logger.warning(warning_msg)
                logger.warning(f"完整响应: {current_result}")
                print(warning_msg)
                # Decide whether to stop or continue polling on unknown status
                # For now, continue polling.
                pass

        # Wait for the next poll interval, regardless of the outcome of this poll attempt
        # unless SUCCESS or FAILED occurred.
        if status not in ["SUCCESS", "FAILED"]:
             logger.debug(f"等待 {poll_interval} 秒进行下一次轮询...")
             time.sleep(poll_interval)
        else:
             break # Exit while loop if final state reached

    # If the while loop finishes (timeout reached)
    error_msg = f"错误：获取任务结果超时 ({timeout}秒)。"
    logger.error(error_msg)
    print(error_msg)
    return None

def fetch_job_list_from_ttapi(api_key, logger, page=1, limit=10):
    """调用 TTAPI 获取 Midjourney 历史任务列表。

    Args:
        api_key (str): TTAPI 密钥。
        logger (logging.Logger): 日志记录器。
        page (int, optional): 页码。默认为 1。
        limit (int, optional): 每页数量 (最大100)。默认为 10。

    Returns:
        list: 包含任务字典的列表，如果成功。
        None: 如果请求失败或没有数据。
    """
    endpoint = f"{TTAPI_BASE_URL}/fetch-list"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    params = {
        "page": page,
        "limit": min(limit, 100) # 确保不超过最大值
    }

    logger.info(f"开始调用 TTAPI 获取任务列表 (Page: {page}, Limit: {params['limit']})...")
    try:
        response = requests.get(endpoint, headers=headers, params=params, timeout=60) # 增加超时时间
        response.raise_for_status() # 如果状态码不是 2xx，则抛出异常

        result = response.json()
        if result.get("status") == "SUCCESS" and "data" in result:
            job_list = result["data"]
            logger.info(f"成功获取到 {len(job_list)} 条任务记录 (Page: {page}, Limit: {params['limit']})。")
            return job_list
        else:
            error_message = result.get("message", "未知的成功响应格式")
            logger.error(f"调用 TTAPI 获取任务列表响应状态非 SUCCESS: {error_message}")
            return None

    except requests.exceptions.Timeout as e:
        logger.error(f"调用 TTAPI 获取任务列表超时: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"调用 TTAPI 获取任务列表失败: {e}")
        # 可以尝试解析错误响应体，如果存在的话
        try:
            error_data = response.json()
            logger.error(f"TTAPI 错误详情: {error_data}")
        except (AttributeError, ValueError):
            pass # response 可能不存在或不是 JSON
        return None
    except Exception as e:
        logger.exception(f"处理 TTAPI 任务列表响应时发生意外错误: {e}")
        return None

def call_action_api(logger, api_key, original_job_id, action, hook_url=None):
    """调用 TTAPI 的 /action 接口执行 Upscale, Variation 等操作。

    Args:
        logger (logging.Logger): 日志记录器。
        api_key (str): TTAPI 密钥。
        original_job_id (str): 要对其执行操作的原始任务的 Job ID。
        action (str): 要执行的操作标识符 (例如: "upsample1", "variation2", "reroll0")。
        hook_url (str, optional): Webhook URL 用于异步回调。

    Returns:
        str: 新任务的 Job ID (如果成功)。
        None: 如果请求失败。
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

    logger.info(f"向 {endpoint} 发送 Action 请求")
    logger.debug(f"Action Payload: {json.dumps(payload)}")

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60) # Set a reasonable timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        response_data = response.json()
        logger.debug(f"Action API 响应: {response_data}")

        if response_data.get("status") == "SUCCESS":
            # According to example, new job ID is in data.jobId
            new_job_id = response_data.get("data", {}).get("jobId")
            if new_job_id:
                logger.info(f"Action 任务提交成功，新的 Job ID: {new_job_id}")
                return new_job_id
            else:
                # If status is SUCCESS but no new jobId, it might be an older API version or unexpected response
                # Let's also check if the top-level jobId exists, just in case
                legacy_job_id = response_data.get("jobId") # Check top level based on example response structure mismatch
                if legacy_job_id:
                    logger.warning("Action API 响应状态为 SUCCESS，但新 Job ID 在 'data' 字段中未找到，尝试使用顶层 'jobId'。")
                    logger.info(f"Action 任务提交成功（使用顶层 Job ID），新的 Job ID: {legacy_job_id}")
                    return legacy_job_id
                else:
                    logger.error("Action API 报告成功，但响应中缺少新的 Job ID (检查了 'data.jobId' 和 'jobId')")
                    return None
        else:
            error_message = response_data.get("message", "未知错误")
            logger.error(f"Action API 报告失败: {error_message}")
            print(f"错误：API 操作提交失败 - {error_message}") # Also print error
            return None

    except requests.exceptions.Timeout:
        logger.error(f"调用 /action API 超时 (60 秒)")
        print(f"错误：调用 Action API 超时。")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"调用 /action API 时发生网络错误: {e}")
        # Log response body if available
        try: logger.error(f"Response body: {response.text}")
        except: pass
        print(f"错误：API Action 请求失败 - {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"无法解析 /action API 响应 (非 JSON 格式): {response.text}")
        print("错误：Action API 响应格式无效。")
        return None
    except Exception as e:
        logger.error(f"处理 /action 响应时发生意外错误: {e}", exc_info=True)
        return None

def fetch_seed_from_ttapi(logger, api_key, job_id):
    """调用 TTAPI 的 /seed 接口获取任务的 Seed 值"""
    endpoint = f"{TTAPI_BASE_URL}/seed"
    headers = {"TT-API-KEY": api_key}
    payload = {"jobId": job_id}

    logger.info(f"向 {endpoint} 请求 Job ID: {job_id} 的 Seed...")
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Check response structure, assuming 'data' contains 'seed'
        if data.get("status") == "SUCCESS" and "data" in data and "seed" in data["data"]:
            seed_value = data["data"]["seed"]
            logger.info(f"成功获取到 Job ID {job_id} 的 Seed: {seed_value}")
            return data["data"] # Return the whole data part which includes seed
        elif data.get("status") == "SUCCESS":
            logger.warning(f"API 成功响应 Seed 请求，但 data 或 seed 字段缺失: {data}")
            return data # Return response even if seed missing, caller checks
        else:
            logger.error(f"API 返回 Seed 获取失败状态: {data.get('status', 'N/A')}, Message: {data.get('message', 'N/A')}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"调用 /seed API 时发生网络错误 (Job ID: {job_id}): {e}")
        if isinstance(e, requests.exceptions.HTTPError):
             _handle_api_error(logger, e.response, f"Seed API 请求 (Job ID: {job_id})")
        return None
    except Exception as e:
        logger.error(f"处理 /seed 响应时发生意外错误 (Job ID: {job_id}): {e}", exc_info=True)
        return None 