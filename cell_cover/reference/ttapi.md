---
title: "Midjourney API | TTAPI 中文文档"
author: "Your Name/Team (if applicable)"
date: "2025-04-18" # Keep or update as needed
description: "TTAPI 提供的 Midjourney API 服务文档，支持最新的 Midjourney 版本，提供稳定且具成本效益的图像生成方案。"
tags:
  - "API"
  - "Midjourney"
  - "TTAPI"
  - "Documentation"
---

# TTAPI Midjourney API 文档

本文档详细介绍了 TTAPI 提供的 Midjourney API 服务，包括认证方式、可用模式、API 端点、参数说明、请求响应示例以及最佳实践。

## 认证

所有 API 请求都需要通过 HTTP Header 进行身份验证。

| Header         | 描述                          |
|----------------|-------------------------------|
| `TT-API-KEY`   | 您的 TTAPI 密钥 (API Key)。    |
| `Content-Type` | 请求体格式，应为 `application/json`。 |

## 速度模式

TTAPI 的 Midjourney 服务提供三种速度模式，对应 Midjourney 的不同生成速度：

- **`fast` 模式:** 响应时间通常在 **60 秒内**。
- **`relax` 模式:** 响应时间通常在 **120 秒内**。
- **`turbo` 模式:** 响应时间通常在 **30 秒内**。

默认情况下，API 使用 `fast` 模式。

**注意:**
- v7 模型当前仅支持 `turbo` 和 `relax` 模式。
- 最多支持 **10 个并发生成任务**。如需更多并发，请联系客服。

## 使用模式

TTAPI 提供两种账户使用模式：

- **PPU (Pay Per Use) 模式:** 按量付费，使用 TTAPI 维护的账户池执行任务，无需管理 Midjourney 账户。
- **账户托管模式:** 将您自己的 Midjourney 账户托管在 TTAPI 平台执行任务。

**注意:** 账户托管模式使用的 API Host 与 PPU 模式不同。

## API 端点

### 1. 生成图像 (`/imagine`)

此接口用于根据文本提示生成 4 张初始图像。

`POST https://api.ttapi.io/midjourney/v1/imagine`

**重要提示:**
- `--cref` 参数必须配合 `--v 6.0` 模型使用。

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**Body 参数**

| 参数          | 类型    | 必填 | 描述                                                                                                                                |
|---------------|---------|------|-------------------------------------------------------------------------------------------------------------------------------------|
| `prompt`      | string  | 是   | 用于生成图像的提示词。示例: `"a cute cat --ar 1:1"`                                                                                      |
| `mode`        | string  | 否   | 生成模式，可选值为 `relax`, `fast`, `turbo`。默认为 `fast`。                                                                          |
| `model`       | string  | 否   | 模型版本，例如 `v6.0`, `v7.0`。请参考 Midjourney 最新支持版本。                                                                             |
| `cref`        | string  | 否   | 图像参考 URL，仅 `v6.0` 支持。                                                                                                           |
| `aspect`      | string  | 否   | 图像宽高比，例如 `1:1`, `16:9` 等。请参考 Midjourney 支持的比例。                                                                         |
| `style`       | string  | 否   | 风格化参数，例如 `raw`。请参考 Midjourney 支持的风格。                                                                                   |
| `quality`     | string  | 否   | 质量参数，例如 `.5`, `1`。请参考 Midjourney 支持的质量。                                                                                |
| `chaos`       | number  | 否   | 混沌度，影响生成结果的多样性。范围 0-100。                                                                                              |
| `seed`        | number  | 否   | 种子值，用于复现相似结果。范围 0-4294967295。                                                                                          |
| `tile`        | boolean | 否   | 是否生成可平铺的图像 (Seamless Tiling)。                                                                                               |
| `stop`        | boolean | 否   | 提前中止生成过程的百分比。                                                                                                             |
| `hookUrl`     | string  | 否   | Webhook 回调地址。任务完成或失败时，将向此 URL 发送 POST 请求通知。如果未设置，需调用 `/fetch` 接口查询状态。                                            |
| `notify_id` | string  | 否 | 自定义通知 ID，会在 Webhook 回调时原样返回，方便关联请求。 |
| `timeout`     | integer | 否   | 任务执行超时时间 (秒)，范围 300 - 1200。`fast` 和 `turbo` 模式默认/最小为 300 秒，`relax` 模式默认/最小为 600 秒。                                  |
| `getUImages`  | boolean | 否   | 是否在初始响应中包含四张小图的 CDN 地址（对应回调结果中的 `images` 字段）。默认为 `false`。注意：这不等同于执行 Upscale 操作。                        |
| `translation` | boolean | 否   | 是否自动翻译非英文提示词。`true` - 翻译，`false` - 不翻译。默认为 `true`。                                                                |


**请求示例**

```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/imagine" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cute cat --ar 1:1",
    "mode": "fast",
    "hookUrl": "https://yourdomain.com/webhook",
    "notify_id": "user_request_123"
  }'
```

```python
import requests

endpoint = "https://api.ttapi.io/midjourney/v1/imagine"
api_key = "your_api_key" # 替换为你的 API Key

headers = {
    "TT-API-KEY": api_key,
    "Content-Type": "application/json"
}

data = {
    "prompt": "a cute cat --ar 1:1",
    "mode": "fast",
    "hookUrl": "https://yourdomain.com/webhook",
    "notify_id": "user_request_123"
    # 添加其他需要的参数
}

response = requests.post(endpoint, headers=headers, json=data)

print(f"Status Code: {response.status_code}")
try:
    print(f"Response JSON: {response.json()}")
except requests.exceptions.JSONDecodeError:
    print(f"Response Text: {response.text}")
```

**响应示例 (成功提交)**

```json
{
  "status": "SUCCESS",
  "message": "",
  "data": {
    "jobId": "afa774a3-1aee-5aba-4510-14818d6875e4"
  }
}
```

**响应示例 (失败)**

```json
{
  "status": "FAILED",
  "message": "Invalid parameter: prompt cannot be empty.",
  "data": null
}
```

*(任务的最终结果将通过 Webhook 或 `/fetch` 接口获取，请参考 [异步回调](#异步回调-webhook))*

---

### 2. 图像变化 (`/action`)

此接口用于执行 Midjourney 图像生成后的各种操作，如 Upscale (U1-U4)、Variation (V1-V4)、Zoom Out、Pan 等。

`POST https://api.ttapi.io/midjourney/v1/action`

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**Body 参数**

| 参数         | 类型    | 必填 | 描述                                                                                           |
|--------------|---------|------|------------------------------------------------------------------------------------------------|
| `jobId`      | string  | 是   | 要执行操作的任务 ID (通常来自 `/imagine` 或上一步 `/action` 的响应)。                                    |
| `action`     | string  | 是   | 要执行的具体操作名称。例如 `upsample1`, `variation1`, `zoom_out_2` 等。请参考 [Action 操作列表](#action-操作列表)。 |
| `timeout`    | integer | 否   | 请求超时时间 (秒)。默认为 300 秒。                                                                 |
| `hookUrl`    | string  | 否   | Webhook 回调地址。                                                                               |
| `getUImages` | boolean | 否   | 是否在响应中包含四张小图的 CDN 地址。默认为 `false`。                                                |

**请求示例**

```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/action" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "afa774a3-1aee-5aba-4510-14818d6875e4",
    "action": "upsample1",
    "hookUrl": "https://yourdomain.com/webhook"
  }'
```

```python
import requests

endpoint = "https://api.ttapi.io/midjourney/v1/action"
api_key = "your_api_key"

headers = {
    "TT-API-KEY": api_key,
    "Content-Type": "application/json"
}

data = {
    "jobId": "afa774a3-1aee-5aba-4510-14818d6875e4", # 替换为实际的 Job ID
    "action": "upsample1", # 或其他 Action
    "hookUrl": "https://yourdomain.com/webhook"
}

response = requests.post(endpoint, headers=headers, json=data)

print(f"Status Code: {response.status_code}")
try:
    print(f"Response JSON: {response.json()}")
except requests.exceptions.JSONDecodeError:
    print(f"Response Text: {response.text}")

```

**响应示例 (成功提交)**

```json
{
  "status": "SUCCESS",
  "message": "",
  "data": {
    "jobId": "afa774a3-1aee-5aba-4510-14818d6875e4" // 注意：返回的 jobId 通常与请求中的 jobId 相同
  }
}
```

*(任务的最终结果将通过 Webhook 或 `/fetch` 接口获取)*

---

### 3. 获取图像种子 (`/seed`)

此接口用于获取已完成的 Midjourney 任务所使用的种子值。

`POST https://api.ttapi.io/midjourney/v1/seed`

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**Body 参数**

| 参数      | 类型    | 必填 | 描述                     |
|-----------|---------|------|--------------------------|
| `jobId`   | string  | 是   | 已完成的任务 ID。           |
| `timeout` | integer | 否   | 请求超时时间 (秒)。默认为 300 秒。 |
| `hookUrl` | string  | 否   | Webhook 回调地址。        |

**请求示例**

```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/seed" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "afa774a3-1aee-5aba-4510-14818d6875e4",
    "hookUrl": "https://yourdomain.com/webhook"
  }'
```

**响应示例 (成功提交)**

```json
{
  "status": "SUCCESS",
  "message": "",
  "data": {
    "jobId": "afa774a3-1aee-5aba-4510-14818d6875e4"
  }
}
```

*(种子的值将在最终的任务结果中通过 Webhook 或 `/fetch` 获取，位于 `data.seed` 字段)*

---

### 4. 图像合成 (`/blend`)

此接口用于将 2 到 5 张图像融合成一张新的图像。

`POST https://api.ttapi.io/midjourney/v1/blend`

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**Body 参数**

| 参数            | 类型        | 必填 | 描述                                                                                                                |
|-----------------|-------------|------|---------------------------------------------------------------------------------------------------------------------|
| `imgBase64Array`| array       | 是   | 包含 2 到 5 个图像 Base64 编码字符串的数组。每个字符串需要包含 `data:image/png;base64,` 前缀。                           |
| `dimensions`    | string      | 否   | 输出图像的比例。可选值: `PORTRAIT` (2:3), `SQUARE` (1:1), `LANDSCAPE` (3:2)。默认为 `SQUARE`。                          |
| `mode`          | string      | 否   | 生成模式 (`relax`, `fast`, `turbo`)。默认为 `fast`。                                                                  |
| `hookUrl`       | string      | 否   | Webhook 回调地址。                                                                                                    |
| `timeout`       | integer     | 否   | 请求超时时间 (秒)。默认为 300 秒。                                                                                    |
| `getUImages`    | boolean     | 否   | 是否在响应中包含四张小图的 CDN 地址。默认为 `false`。                                                                   |

**请求示例**

```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/blend" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "imgBase64Array": ["data:image/png;base64,xxx1...", "data:image/png;base64,xxx2..."],
    "dimensions": "SQUARE",
    "mode": "fast",
    "hookUrl": "https://yourdomain.com/webhook"
  }'
```

**响应示例 (成功提交)**

```json
{
  "status": "SUCCESS",
  "message": "",
  "data": {
    "jobId": "bfb885b4-2bff-6bcb-5621-25929e7986f5" # 新生成的 Job ID
  }
}
```

---

### 5. 图像描述 (`/describe`)

此接口用于上传一张图像，并生成四个相关的文本提示词。

`POST https://api.ttapi.io/midjourney/v1/describe`

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**Body 参数**

| 参数      | 类型    | 必填 | 描述                                                                   |
|-----------|---------|------|------------------------------------------------------------------------|
| `base64`  | string  | 否   | 图像的 Base64 编码字符串，需要包含 `data:image/png;base64,` 前缀。          |
| `url`     | string  | 否   | 图像的 URL 地址。                                                         |
| `hookUrl` | string  | 否   | Webhook 回调地址。                                                      |
| `timeout` | integer | 否   | 请求超时时间 (秒)。默认为 300 秒。                                         |

**注意:** `base64` 和 `url` 至少提供一个，如果都提供，优先使用 `base64`。

**请求示例**

```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/describe" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "base64": "data:image/png;base64,xxx1...",
    "hookUrl": "https://yourdomain.com/webhook"
  }'
```

**响应示例 (成功提交)**

```json
{
  "status": "SUCCESS",
  "message": "",
  "data": {
    "jobId": "cfc996c5-3cgg-7cdc-6732-36030f8097g6" # 新生成的 Job ID
  }
}
```
*(生成的提示词将在最终的任务结果中通过 Webhook 或 `/fetch` 获取，位于 `data.prompt` 字段，通常包含多个以换行符分隔的提示)*

---

### 6. 区域重绘 (`/inpaint`)

此接口用于对图像的指定区域进行重绘，等同于 Midjourney 的 Vary (Region) 功能。

`POST https://api.ttapi.io/midjourney/v1/inpaint`

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**Body 参数**

| 参数      | 类型    | 必填 | 描述                                                                                                                                |
|-----------|---------|------|-------------------------------------------------------------------------------------------------------------------------------------|
| `jobId`   | string  | 是   | 要进行重绘的原始任务 ID (通常是 Upscale 后的任务 ID)。                                                                                   |
| `mask`    | string  | 是   | 蒙版图像的 Base64 编码字符串 (**无需** `data:image/png;base64,` 前缀)。蒙版应与原图尺寸相同，白色区域表示要重绘的部分，黑色区域表示保留的部分。 |
| `prompt`  | string  | 否   | 对重绘区域的描述提示词。如果为空，则基于原图提示词进行重绘。                                                                            |
| `hookUrl` | string  | 否   | Webhook 回调地址。                                                                                                                   |
| `timeout` | integer | 否   | 请求超时时间 (秒)。默认为 300 秒。                                                                                                   |

**请求示例**

```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/inpaint" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "afa774a3-1aee-5aba-4510-14818d6875e4",
    "prompt": "wearing sunglasses",
    "mask": "UklGRrw0AABXRUJQVlA4WAoAAAAgAAAA...",
    "hookUrl": "https://yourdomain.com/webhook"
  }'
```

**响应示例 (成功提交)**

```json
{
  "status": "SUCCESS",
  "message": "",
  "data": {
    "jobId": "dfd007d6-4dhh-8ddd-7843-47141g9108h7" # 新生成的 Job ID
  }
}
```

---

### 7. 获取任务状态 (`/fetch`)

此接口用于查询指定任务的当前状态和结果。**此接口免费，不消耗 Quota。**

`POST https://api.ttapi.io/midjourney/v1/fetch`

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**Body 参数**

| 参数    | 类型   | 必填 | 描述       |
|---------|--------|------|------------|
| `jobId` | string | 是   | 要查询的任务 ID。 |

**请求示例**

```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/fetch" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "afa774a3-1aee-5aba-4510-14818d6875e4"
  }'
```

**响应示例**

响应的数据结构与 [异步回调](#异步回调-webhook) 的 JSON 结构一致。

```json
// 示例：任务成功
{
    "status": "SUCCESS",
    "jobId": "f5850038-90a3-8a97-0476-107ea4b8dac4",
    "message": "success",
    "data": {
        "actions": "imagine", // 或其他 action
        "jobId": "f5850038-90a3-8a97-0476-107ea4b8dac4",
        "progress": "100",
        "prompt": "a cute cat --ar 1:1",
        "discordImage": "https://cdn.discordapp.com/...", // Discord CDN URL (可能过期)
        "cdnImage": "https://cdnb.ttapi.io/...", // TTAPI CDN URL (推荐使用)
        "width": 1024, // 图像宽度 (像素)
        "height": 1024, // 图像高度 (像素)
        "hookUrl": "https://yourdomain.com/webhook",
        "components": ["upsample1", "upsample2", /* ... */], // 可执行的下一步操作
        "seed": "1234567890", // 任务种子
        "images": [ // 仅当 getUImages=true 或为 /imagine 任务时存在
            "https://cdnb.ttapi.io/...",
            "https://cdnb.ttapi.io/...",
            "https://cdnb.ttapi.io/...",
            "https://cdnb.ttapi.io/..."
        ],
        "quota": 1 // 示例消耗额度
        // ... 可能包含 notify_id 等其他字段
    }
}

// 示例：任务执行中
{
    "status": "ON_QUEUE", // 或 PENDING_QUEUE
    "jobId": "f5850038-90a3-8a97-0476-107ea4b8dac4",
    "message": "",
    "data": {
       "progress": "50", // 示例进度
       // ... 其他字段可能不完整
    }
}
```

---

### 8. Prompt 效验 (`/promptCheck`)

此接口用于检查提供的英文提示词是否包含 Midjourney 禁止的内容。**此接口免费，不消耗 Quota。**

`POST https://api.ttapi.io/midjourney/v1/promptCheck`

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**Body 参数**

| 参数     | 类型   | 必填 | 描述                        |
|----------|--------|------|-----------------------------|
| `prompt` | string | 是   | 要检查的英文提示词。             |

**请求示例**

```bash
curl -X POST "https://api.ttapi.io/midjourney/v1/promptCheck" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cute kitten playing"
  }'
```

**响应示例 (成功/通过)**

```json
{
    "status": "SUCCESS",
    "message": "success",
    "data": "Prompt verification successful."
}
```

**响应示例 (失败/包含禁止词)**

```json
{
    "status": "FAILED",
    "message": "banned prompt words: [word]", // [word] 是检测到的禁止词
    "data": null
}
```

---

### 9. Midjourney 服务状态查询 (`/status`)

此接口用于查询 TTAPI Midjourney API 各个速度模式的当前运行状态和平均执行时间。**此接口免费，不消耗 Quota。**

`GET https://api.ttapi.io/midjourney/status`

**Headers**

| Header         | 值                 |
|----------------|--------------------|
| `TT-API-KEY`   | `your_api_key`     |
| `Content-Type` | `application/json` |

**请求示例**

```bash
curl -X GET "https://api.ttapi.io/midjourney/status" \
  -H "TT-API-KEY: your_api_key" \
  -H "Content-Type: application/json"
```

**响应示例**

```json
{
    "status": "SUCCESS",
    "message": "success",
    "data": {
        "fast": {
            "status": 200, // 200 表示正常
            "runningMessage": "Endpoints running",
            "averageExecute": 46.42 // 平均执行时间 (秒)
        },
        "relax": {
            "status": 200,
            "runningMessage": "Endpoints running",
            "averageExecute": 39.37
        },
        "turbo": {
            "status": 200,
            "runningMessage": "Endpoints running",
            "averageExecute": 23.87
        }
    }
}
```

## Action 操作列表

以下是 `/action` 接口支持的操作名称 (`action` 参数值) 及其对应的 Midjourney 功能：

| 操作名称                 | 描述                                       | 对应 Midjourney 按钮/功能 | 备注                         |
|--------------------------|--------------------------------------------|---------------------------|------------------------------|
| `upsample1`              | 放大第 1 张图像                             | `U1`                      |                              |
| `upsample2`              | 放大第 2 张图像                             | `U2`                      |                              |
| `upsample3`              | 放大第 3 张图像                             | `U3`                      |                              |
| `upsample4`              | 放大第 4 张图像                             | `U4`                      |                              |
| `variation1`             | 基于第 1 张图像生成变体                     | `V1`                      |                              |
| `variation2`             | 基于第 2 张图像生成变体                     | `V2`                      |                              |
| `variation3`             | 基于第 3 张图像生成变体                     | `V3`                      |                              |
| `variation4`             | 基于第 4 张图像生成变体                     | `V4`                      |                              |
| `high_variation`         | 对放大后的图像进行大幅度变化                 | `Vary (Strong)`           |                              |
| `low_variation`          | 对放大后的图像进行小幅度变化                 | `Vary (Subtle)`           |                              |
| `upscale2`               | 将放大后的图像再放大 2 倍                   | `Upscale (2x)`            | 通常用于 v5 及更早版本       |
| `upscale4`               | 将放大后的图像再放大 4 倍                   | `Upscale (4x)`            | 通常用于 v5 及更早版本       |
| `zoom_out_2`             | 将放大后的图像缩小 2 倍                     | `Zoom Out 2x`             |                              |
| `zoom_out_1_5`           | 将放大后的图像缩小 1.5 倍                   | `Zoom Out 1.5x`           |                              |
| `pan_left`               | 向左平移扩展图像                           | `⬅️`                       |                              |
| `pan_right`              | 向右平移扩展图像                           | `➡️`                       |                              |
| `pan_up`                 | 向上平移扩展图像                           | `⬆️`                       |                              |
| `pan_down`               | 向下平移扩展图像                           | `⬇️`                       |                              |
| `upscale_creative`       | 使用创意模式放大图像 (保留更多细节/创意)    | `Upscale (Creative)`      | 通常用于 v6 及之后版本       |
| `upscale_subtle`         | 使用微妙模式放大图像 (更接近原图)          | `Upscale (Subtle)`        | 通常用于 v6 及之后版本       |
| `reroll`                 | 基于相同提示词重新生成一组图像               | `🔄` (Reroll)             |                              |
| `redo_upscale2`          | 重新执行 Upscale (2x) 操作                | `Redo Upscale (2x)`       |                              |
| `redo_upscale4`          | 重新执行 Upscale (4x) 操作                | `Redo Upscale (4x)`       |                              |
| `make_square`            | 将非方形图像裁剪/扩展为方形                | `Make Square`             |                              |
| `redo_upscale_subtle`    | 重新执行 Upscale (Subtle) 操作            | `Redo Upscale (Subtle)`   |                              |
| `redo_upscale_creative`  | 重新执行 Upscale (Creative) 操作          | `Redo Upscale (Creative)` |                              |

*请参考 Midjourney 官方文档了解各操作的具体效果。*

## 异步回调 (Webhook)

当您在请求中提供了 `hookUrl` 时，任务状态发生变化（如开始执行、完成、失败）时，TTAPI 会向您指定的 URL 发送 `POST` 请求，请求体为 JSON 格式。

**回调 JSON 结构:**

```json
{
    "status": "SUCCESS", // 或 PENDING_QUEUE, ON_QUEUE, FAILED
    "jobId": "f5850038-90a3-8a97-0476-107ea4b8dac4",
    "message": "success", // 或其他消息
    "data": {
        "actions": "imagine", // 或其他 action
        "jobId": "f5850038-90a3-8a97-0476-107ea4b8dac4",
        "progress": "100", // 进度百分比字符串
        "prompt": "...", // 任务使用的提示词
        "discordImage": "https://cdn.discordapp.com/...", // Discord CDN URL (可能过期)
        "cdnImage": "https://cdnb.ttapi.io/...", // TTAPI CDN URL (推荐使用, 有效期至少1个月)
        "width": 1024, // 图像宽度 (像素)
        "height": 1024, // 图像高度 (像素)
        "hookUrl": "https://yourdomain.com/webhook", // 您设置的回调地址
        "components": ["upsample1", /* ... */], // 任务完成后可执行的下一步操作列表
        "seed": "1234567890", // 任务使用的种子值 (如果适用)
        "images": [ // 仅当 getUImages=true 或为 /imagine 任务时存在，包含4张小图的 TTAPI CDN URL
            "https://cdnb.ttapi.io/...",
            "https://cdnb.ttapi.io/...",
            "https://cdnb.ttapi.io/...",
            "https://cdnb.ttapi.io/..."
        ],
        "quota": 1, // 本次任务消耗的额度
        "notify_id": "user_request_123" // 您在请求时设置的 notify_id
        // ... 可能还有其他字段
    }
}
```

**关键字段说明:**

| 字段           | 类型   | 描述                                                                                              |
|----------------|--------|---------------------------------------------------------------------------------------------------|
| `status`       | string | 任务状态: `PENDING_QUEUE` (排队中), `ON_QUEUE` (执行中), `SUCCESS` (成功), `FAILED` (失败)          |
| `jobId`        | string | 任务 ID。                                                                                         |
| `message`      | string | 状态相关的消息，例如失败原因。                                                                       |
| `data`         | object | 任务详情数据。                                                                                    |
| `data.actions` | string | 执行的操作类型 (`imagine`, `upsample1` 等)。                                                     |
| `data.progress`| string | 任务进度百分比字符串 ("0" 到 "100")。                                                              |
| `data.prompt`  | string | 任务使用的提示词。对于 `/describe` 任务，这里会包含生成的多个提示词。                                   |
| `data.cdnImage`| string | **推荐使用的图像 URL**，TTAPI CDN 地址，有效期至少 1 个月。                                         |
| `data.discordImage`| string | Discord CDN 地址，通常在 24-72 小时内过期。                                                       |
| `data.components`| array  | 任务成功后，可以执行的下一步操作列表 (Action 名称)。                                                |
| `data.seed`    | string | 任务使用的种子值。                                                                                |
| `data.images`  | array  | 仅在 `/imagine` 任务或请求时 `getUImages=true` 时包含，为 4 张小图的 TTAPI CDN URL 列表。              |
| `data.quota`   | number | 本次任务消耗的 API 调用额度。                                                                     |
| `data.notify_id`| string | 您在发起任务时提供的 `notify_id`。                                                              |

**注意:**
- Discord 的 CDN 链接 (`discordImage`) 过期时间不定，建议使用 TTAPI 的 CDN 链接 (`cdnImage` 和 `images`)。
- TTAPI 的 CDN 域名自 2024 年 9 月 13 日起由 `https://mjcdn.ttapi.io` 变更为 `https://cdnb.ttapi.io`。
- 您的 Webhook 服务端应在收到回调请求后尽快返回 `200 OK` 状态码。如果回调失败，TTAPI 会尝试重试几次。

## 错误码说明

| 错误码 | 说明         | 建议解决方案                     |
|--------|--------------|----------------------------------|
| -1     | 系统错误     | 请稍后重试或联系技术支持。         |
| -2     | 参数错误     | 检查请求参数是否符合 API 文档要求。   |
| -3     | 认证失败     | 检查 `TT-API-KEY` 是否正确且有效。 |
| -4     | 余额不足     | 请检查您的账户余额并充值。         |
| -5     | 请求过于频繁 | 请降低 API 请求频率。             |
| -6     | 任务不存在   | 检查提供的 `jobId` 是否正确。     |
| -7     | 模型维护中   | 相关模型暂时不可用，请稍后再试。     |
| -8     | 账号被封禁   | 您的账户可能因违反规定被封禁，请联系客服。 |
| *其他* | (特定消息) | 根据响应中的 `message` 字段判断具体问题。 |

## 常见问题 (FAQ)

#### 1. 如何选择合适的生成模式 (`mode`)？
- **`relax`:** 速度最慢，质量最优，适合对最终效果要求高的场景。
- **`fast`:** 速度和质量均衡，适合大多数常规使用场景 (默认)。
- **`turbo`:** 速度最快，质量可能略有降低，适合需要快速迭代或预览的场景。

#### 2. 为什么我的图片生成失败了？
- **提示词违规:** 检查 `prompt` 是否包含 Midjourney 禁止的内容 (可使用 `/promptCheck` 接口预检查)。
- **服务器负载:** 高峰期可能导致任务处理延迟或失败，建议使用 Webhook 处理异步结果。
- **网络问题:** 确保您的服务器能够稳定访问 TTAPI 服务。
- **余额不足:** 确认您的账户有足够的 Quota。
- **参数错误:** 仔细检查请求参数是否符合文档规范。

#### 3. 如何提高生成图片的质量？
- **详细提示词:** 提供更具体、描述性更强的 `prompt`。
- **选择模型:** 尝试不同的模型版本 (`model`)。
- **调整参数:** 尝试调整 `--quality`, `--style`, `--chaos` 等 Midjourney 参数 (附加在 `prompt` 中)。
- **使用 `relax` 模式:** 通常能获得更好的细节和一致性。
- **迭代优化:** 基于初步结果，使用 Variation 或 Inpaint 功能进行调整。

#### 4. API 调用限制是什么？
- **频率限制:** 通常每个 API Key 每分钟有请求次数限制 (例如 60 次/分钟)，具体请参考您的账户类型。单个 IP 也可能有频率限制。
- **并发限制:** 同时执行的任务数量有限制 (例如 10 个)。
- **任务超时:** 单个任务有最大执行时间限制。
- **图片有效期:** `cdnImage` 和 `images` 中的 URL 至少保证 1 个月有效，`discordImage` 可能在 24-72 小时内失效。

#### 5. 如何正确使用 Webhook？
- **POST 支持:** 确保您的 `hookUrl` 是一个能够接收 `POST` 请求的公网可访问地址。
- **及时响应:** 收到回调后，您的服务器应尽快返回 `200 OK`，避免 TTAPI 超时重试。
- **处理不同状态:** 根据回调中的 `status` 字段处理任务成功、失败或进行中的逻辑。
- **使用 `notify_id`:** 在请求时设置 `notify_id`，并在回调中接收它，方便将回调结果与您的内部请求关联起来。
- **幂等性处理:** 考虑到网络重试等因素，您的 Webhook 处理逻辑最好具备幂等性。

## 最佳实践

1.  **异步处理与 Webhook:**
    - 强烈建议使用 `hookUrl` 进行异步结果通知，而不是依赖轮询 `/fetch` 接口。这更高效且能避免不必要的请求。
    - 在 Webhook 服务端记录接收到的任务状态和结果，以便后续处理。

2.  **错误处理与重试:**
    - 对 API 请求进行 `try-catch` 封装，处理网络错误和 API 返回的错误状态码。
    - 对于可恢复的错误 (如瞬时网络问题、服务器临时错误)，可以考虑加入适当的重试逻辑 (例如指数退避)。
    - 对于明确的失败 (如参数错误、余额不足、提示词违规)，应记录错误并通知用户，而不是无限重试。

3.  **速率限制管理:**
    - 如果您的应用需要高频调用 API，请在客户端或服务端实现请求队列和速率控制逻辑，避免超出频率限制。
    - 监控 API 响应中的错误信息，如果出现频率限制相关的错误，应主动降低请求速率。

4.  **参数校验:**
    - 在调用 API 前，对关键参数 (如 `prompt`) 进行基本的校验，例如非空检查。
    - 对于英文 `prompt`，可以先调用 `/promptCheck` 接口进行预检查，减少因违规内容导致的失败。

5.  **配置管理:**
    - 将 `TT-API-KEY`、`hookUrl` 等敏感信息或可配置项存储在安全的环境变量或配置文件中，而不是硬编码在代码里。

6.  **日志记录:**
    - 记录关键的 API 请求参数、返回的 `jobId` 以及 Webhook 回调接收到的信息，方便问题排查。

**代码示例 (错误处理 - JavaScript/Node.js):**

```javascript
async function submitImagineTask(prompt, webhookUrl, apiKey, notifyId) {
  const endpoint = 'https://api.ttapi.io/midjourney/v1/imagine';
  const headers = {
    'TT-API-KEY': apiKey,
    'Content-Type': 'application/json'
  };
  const body = {
    prompt: prompt,
    hookUrl: webhookUrl,
    notify_id: notifyId
    // Add other parameters as needed
  };

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(body)
    });

    if (!response.ok) {
      // Handle HTTP errors (e.g., 4xx, 5xx)
      const errorText = await response.text();
      console.error(`HTTP Error: ${response.status} - ${errorText}`);
      // Potentially throw a custom error or return an error indicator
      return { success: false, error: `HTTP ${response.status}`, message: errorText };
    }

    const data = await response.json();

    if (data.status !== 'SUCCESS') {
      // Handle API-level errors reported in the JSON body
      console.error(`API Error: ${data.message}`);
      return { success: false, error: 'API Error', message: data.message };
    }

    console.log(`Task submitted successfully. Job ID: ${data.data.jobId}`);
    return { success: true, jobId: data.data.jobId };

  } catch (error) {
    // Handle network errors or other exceptions
    console.error('Request failed:', error);
    return { success: false, error: 'Network Error', message: error.message };
  }
}
```

**代码示例 (Webhook 处理 - Node.js/Express):**

```javascript
const express = require('express');
const app = express();
app.use(express.json()); // Middleware to parse JSON bodies

app.post('/webhook', (req, res) => {
  console.log('Received webhook callback:');
  console.log(JSON.stringify(req.body, null, 2));

  const { status, jobId, data, message } = req.body;
  const notifyId = data?.notify_id; // Safely access notify_id

  try {
    // --- Your Logic to Process the Callback ---
    if (status === 'SUCCESS') {
      console.log(`Task ${jobId} (Notify ID: ${notifyId}) completed successfully.`);
      console.log(`Image URL: ${data?.cdnImage}`);
      // TODO: Update your database, notify the user, etc.
      // Example: updateTaskStatus(jobId, 'completed', data.cdnImage, notifyId);

    } else if (status === 'FAILED') {
      console.error(`Task ${jobId} (Notify ID: ${notifyId}) failed. Reason: ${message}`);
      // TODO: Update your database, notify the user about the failure.
      // Example: updateTaskStatus(jobId, 'failed', null, notifyId, message);

    } else if (status === 'ON_QUEUE' || status === 'PENDING_QUEUE') {
      console.log(`Task ${jobId} (Notify ID: ${notifyId}) is currently ${status}. Progress: ${data?.progress || 'N/A'}%`);
      // Optionally update progress in your system
      // Example: updateTaskProgress(jobId, data?.progress, notifyId);
    } else {
      console.warn(`Received unknown status: ${status} for job ${jobId}`);
    }
    // --- End of Your Logic ---

    // Important: Respond quickly to acknowledge receipt
    res.status(200).send('Webhook received');

  } catch (error) {
    console.error('Error processing webhook:', error);
    // Still try to send a 200 OK if possible, or handle error response
    res.status(500).send('Error processing webhook');
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Webhook listener running on port ${PORT}`);
});
```