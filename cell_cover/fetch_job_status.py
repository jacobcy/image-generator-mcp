#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TTAPI Job Status Fetcher
-----------------------
这个脚本用于根据 Job ID 查询 TTAPI Midjourney 任务的状态和结果。
"""

import json
import os
import argparse
import sys
import time
from datetime import datetime

# 尝试导入必要的库
try:
    import requests
except ImportError:
    print("错误：缺少 'requests' 库。请使用 'uv pip install requests' 安装。")
    sys.exit(1)

# --- 配置常量 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TTAPI_BASE_URL = "https://api.ttapi.io/midjourney/v1"

# --- 辅助函数 ---

def get_api_key():
    """从环境变量或 .env 文件获取TTAPI密钥"""
    api_key = os.environ.get("TTAPI_API_KEY")

    if not api_key:
        env_path = os.path.join(SCRIPT_DIR, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            if line.startswith("TTAPI_API_KEY="):
                                api_key = line.strip().split('=', 1)[1]
                                break
            except Exception as e:
                print(f"警告：无法从 .env 文件加载 API 密钥: {e}")

    if not api_key:
        print("错误：未设置 TTAPI_API_KEY 环境变量，且在 .env 文件中也未找到。")
        print("请设置环境变量 TTAPI_API_KEY=<your_api_key> 或在 .env 文件中添加该变量。")
        sys.exit(1)

    return api_key

def fetch_job_status(job_id, api_key):
    """调用 TTAPI 的 /fetch 接口获取任务状态"""
    url = f"{TTAPI_BASE_URL}/fetch"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"jobId": job_id}

    print(f"正在查询 Job ID: {job_id} 的状态...")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        # 打印详细的响应信息以便调试
        print(f"API 响应状态码: {response.status_code}")
        try:
            response_json = response.json()
            print("API 响应内容:")
            print(json.dumps(response_json, indent=2, ensure_ascii=False)) # 格式化打印 JSON
            response.raise_for_status() # 对 >= 400 的状态码抛出异常
            return response_json
        except json.JSONDecodeError:
            # Use triple quotes for multi-line f-string
            print(f"""错误：无法解析 API 响应。响应文本:
{response.text}""")
            return None
        except requests.exceptions.HTTPError as e:
             print(f"API 请求失败: {e}") # HTTPError 会包含状态码
             return None

    except requests.exceptions.RequestException as e:
        print(f"调用 /fetch API 时出错: {e}")
        return None

def display_job_details(result):
    """格式化并显示任务详情"""
    if not result:
        print("未能获取任务详情。")
        return

    status = result.get("status", "N/A")
    job_id = result.get("jobId", "N/A")
    message = result.get("message", "")
    data = result.get("data", {})

    print("\n--- 任务详情 ---")
    print(f"Job ID: {job_id}")
    print(f"状态: {status}")
    if message and status != "SUCCESS":
        print(f"消息: {message}")

    if isinstance(data, dict):
        progress = data.get("progress", "N/A")
        prompt = data.get("prompt", "N/A")
        cdn_image = data.get("cdnImage", "N/A")
        discord_image = data.get("discordImage", "N/A")
        seed = data.get("seed", "N/A")
        quota = data.get("quota", "N/A")
        images = data.get("images") # 可能是列表

        print(f"进度: {progress}%")
        print(f"提示词: {prompt}")
        print(f"种子 (Seed): {seed}")
        print(f"消耗额度 (Quota): {quota}")
        print(f"Discord 图片 URL: {discord_image}")
        print(f"推荐 CDN 图片 URL: {cdn_image}")

        if images and isinstance(images, list):
            print("小图 CDN URLs (来自 images 字段):")
            for i, img_url in enumerate(images):
                print(f"  - 图 {i+1}: {img_url}")
    elif status == "SUCCESS":
        print("警告：任务状态为 SUCCESS 但 data 字段格式不符合预期。")

    print("----------------")


def main():
    parser = argparse.ArgumentParser(
        description="使用 TTAPI 查询 Midjourney 任务状态",
        epilog="需要设置环境变量 TTAPI_API_KEY 或在同目录下有 .env 文件"
    )
    parser.add_argument("--job-id", type=str, required=True, help="要查询的任务的 Job ID")
    args = parser.parse_args()

    api_key = get_api_key()
    job_result = fetch_job_status(args.job_id, api_key)

    if not job_result:
        print("查询失败。")
        sys.exit(1)

    # 显示任务详情
    display_job_details(job_result)

if __name__ == "__main__":
    main() 