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
POLL_INTERVAL_SECONDS = 10  # Default poll interval
FETCH_TIMEOUT_SECONDS = 360 # Default fetch timeout

# Note: logger needs to be passed into the functions or initialized differently

def call_imagine_api(logger, prompt_data, api_key, hook_url=None, notify_id=None, max_retries=1):
    """调用TTAPI的 /imagine 接口

    参数:
    - logger: The logging object.
    - prompt_data: 包含提示词和参数的字典
    - api_key: TTAPI API密钥
    - hook_url: 可选的webhook URL，用于接收任务完成通知
    - notify_id: 可选的通知ID，用于识别回调请求
    - max_retries: 最大重试次数（默认为1）
    """
    url = f"{TTAPI_BASE_URL}/imagine"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    # 获取生成模式，默认为 fast
    mode = prompt_data.get("mode", "fast")
    logger.info(f"准备调用 /imagine API，模式: {mode}")

    # 根据模式设置超时时间 (这个逻辑也可以移到调用者处，或者在这里作为默认)
    if mode == "relax":
        timeout = 600  # relax模式默认超时时间更长
    else:
        timeout = 300  # fast和turbo模式默认超时时间

    # 构建请求体 - TODO: Refactor to accept individual parameters per API spec
    payload = {
        "prompt": prompt_data["prompt"], # Keep prompt for now
        "mode": mode,
        "timeout": timeout
        # Add other parameters like aspect, quality, model, etc., here
    }

    # Add parameters expected by the API (aspect, quality, model etc.)
    # These should ideally be passed explicitly, not just in the prompt string
    # Example (needs prompt_data to contain these keys):
    # if "aspect_ratio" in prompt_data and prompt_data["aspect_ratio"]:
    #     payload["aspect"] = prompt_data["aspect_ratio"] # Use the value like "1:1"
    # if "quality" in prompt_data and prompt_data["quality"]:
    #     payload["quality"] = prompt_data["quality"] # Use the value like "1"
    # if "version" in prompt_data and prompt_data["version"]:
    #     payload["model"] = f"v{prompt_data['version']}" # Assuming version is like "6" -> "v6.0" - needs mapping

    # 添加 webhook 相关参数
    if hook_url:
        payload["hookUrl"] = hook_url
        logger.info(f"使用 webhook URL: {hook_url}")
        if notify_id:
            payload["notifyId"] = notify_id
            logger.debug(f"使用通知ID: {notify_id}")

    logger.info(f"正在调用 /imagine API...")
    logger.debug(f"请求头: {headers}") # Log headers too
    logger.debug(f"请求参数 (Payload): {json.dumps(payload, indent=2)}") # Pretty print payload
    print(f"正在调用 /imagine API...")
    # print(f"请求参数: {payload}") # Avoid printing potentially large prompts twice

    # 重试逻辑
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"第 {attempt} 次重试调用 /imagine API...")
                print(f"第 {attempt} 次重试调用 /imagine API...")
                time.sleep(2)  # 重试前等待 2 秒

            response = requests.post(url, headers=headers, json=payload, timeout=30) # 增加请求超时

            logger.debug(f"API 响应状态码: {response.status_code}")
            # print(f"API 响应状态码: {response.status_code}") # Reduce console noise

            try:
                response_json = response.json()
                logger.debug(f"API 响应内容: {json.dumps(response_json, indent=2)}") # Pretty print
                # print(f"API 响应内容: {response_json}") # Reduce console noise
            except json.JSONDecodeError:
                # Log the raw text if JSON parsing fails
                logger.warning(f"API 响应不是有效的 JSON: {response.text[:500]}...") # Log truncated response
                print(f"API 响应文本: {response.text}")
                response_json = None # Set to None if not valid JSON

            response.raise_for_status() # 对 >= 400 的状态码抛出异常

            # Check response content even if status is 2xx
            if response_json:
                result = response_json
                if result.get("status") == "SUCCESS" and result.get("data", {}).get("jobId"):
                    job_id = result["data"]["jobId"]
                    success_msg = f"任务成功提交，Job ID: {job_id}"
                    logger.info(success_msg)
                    print(success_msg)
                    return job_id
                else:
                    error_msg = f"API 提交失败: {result.get('message', '未知错误')}"
                    logger.error(error_msg)
                    logger.error(f"完整响应: {result}")
                    print(error_msg)
                    # print(f"完整响应: {result}") # Already logged
            else:
                # Handle cases where response is 2xx but not valid JSON or expected structure
                error_msg = f"API 调用成功 (状态码 {response.status_code}) 但响应格式不正确或未包含 Job ID。"
                logger.error(error_msg)
                print(error_msg)


            # If we reach here, it means the API call was successful (2xx) but logical failure or bad response
            # Only retry on RequestExceptions or specific API errors if desired
            # For now, break the loop if API call was successful but didn't return jobId
            if attempt < max_retries:
                 logger.warning("API 调用成功但未获取 Job ID，不再重试。")
                 # Decide if this case should retry - currently it won't.
            return None # Return None as job submission failed logically

        except requests.exceptions.RequestException as e:
            error_msg = f"调用 /imagine API 时出错: {e}"
            logger.error(error_msg)
            print(error_msg)
            # Only retry on request exceptions
            if attempt < max_retries:
                continue
            # After all retries, return None
            logger.error("所有 /imagine API 调用重试尝试均失败 (RequestException)")
            return None

    # If loop finishes without returning (e.g., all retries failed for RequestException)
    logger.error("所有 /imagine API 调用重试尝试均失败")
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