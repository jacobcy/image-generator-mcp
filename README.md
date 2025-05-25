# Cell 杂志封面生成器

这个工具集用于生成 Cell Reports Medicine 杂志封面的 Midjourney 提示词，并通过 TTAPI 获取生成的图像。

## 目录

- [功能概述](#功能概述)
- [安装与设置](#安装与设置)
- [使用指南](#使用指南)
- [命令详解](#命令详解)
- [配置文件](#配置文件)
- [图像元数据](#图像元数据)
- [图像后处理](#图像后处理)
- [提交流程](#提交流程)
- [常见问题](#常见问题)

## 功能概述

本工具集提供以下功能：

1. **提示词生成**：基于预设的创意概念生成 Midjourney 提示词
2. **多样化变体**：每个创意概念有多个变体可供选择
3. **灵活配置**：可自定义宽高比、质量和 Midjourney 版本
4. **API 集成**：通过 TTAPI 直接生成图像并下载到本地
5. **多种操作支持**：支持 Upscale, Variation, Reroll 等后续操作。
6. **Seed 管理**：支持获取图像 Seed，并基于 Prompt 和 Seed 重新生成。
7. **异步生成**：支持通过 Webhook 异步接收生成结果
8. **元数据管理**：自动保存图像元数据，便于后续查询和管理
9. **日志记录**：详细的日志记录，便于排查问题
10. **统一命令入口**：通过 `crc` 命令访问所有功能。
11. **链式操作**: 支持 `--last-job`, `--wait`, `view --save` 等方便连续操作的功能。

## 安装与设置

### 前提条件

- Python 3.x
- uv 包管理器（推荐）或 pip
- TTAPI 账户和 API 密钥

### 安装步骤

1. 克隆或下载本项目到本地
2. 运行安装脚本安装依赖：

```bash
cd /path/to/your/project # 进入项目目录
# 确保 requirements.txt 存在
uv tool install -e . # 安装依赖
```

3. 设置 TTAPI API 密钥(用于生成图像)：

```bash
# 方法一：设置环境变量 (推荐)
export TTAPI_API_KEY="your_api_key_here"

# 方法二：创建 .env 文件 (在项目根目录下)
echo "TTAPI_API_KEY=your_api_key_here" > .env
```

4. 设置 openai 密钥 (用于生成提示词)：

```bash
# 方法一：设置环境变量 (推荐)
export OPENAI_API_KEY="your_api_key_here"

# 方法二：创建 .env 文件 (在项目根目录下)
echo "OPENAI_API_KEY=your_api_key_here" >> .env
```

## 使用指南

### 基本用法

所有命令都通过 `crc` 命令执行。

```bash
crc <command> [options...]
```

查看可用命令和帮助：
```bash
crc --help
crc <command> --help
```

---

## 命令详解

### `list-concepts`

列出 `prompts_config.json` 中定义的所有可用创意概念及其键。

*   **用法:** `crc list-concepts [-v]`
*   **选项:**
    *   `-v, --verbose`: 显示详细日志。

### `variations`

列出指定创意概念的所有可用变体及其键。

*   **用法:** `crc variations <concept_key> [-v]`
*   **参数:**
    *   `concept_key` (必需): 要查询变体的创意概念键。
*   **选项:**
    *   `-v, --verbose`: 显示详细日志。

### `generate`

仅生成 Midjourney 提示词文本，不提交任务（需要使用openai key）。

*   **用法:** `crc generate [-c CONCEPT | -p PROMPT] [options...]`
*   **主要选项:**
    *   `-c, --concept <key>`: 使用的概念键。
    *   `-p, --prompt <text>`: 自定义提示词。
    *   `-var, --variation <key...>`: 使用的变体键 (可多个)。
    *   `--style <key...>`: 使用的全局风格键 (可多个)。
    *   `--cref <url_or_path>`: 图像参考 URL 或本地路径。
    *   `--clipboard`: 将生成的提示词复制到剪贴板。
    *   `--save-prompt`: 将提示词保存到 `outputs/` 目录。
    *   其他用于构建提示词的参数 (`-ar`, `-q`, `-ver`)。

### `create`

生成提示词并提交新的 Midjourney 图像生成任务。

*   **用法:** `crc create [-c CONCEPT | -p PROMPT] [options...]`
*   **主要选项:**
    *   `-c, --concept <key>`: 使用的概念键。
    *   `-p, --prompt <text>`: 自定义提示词。
    *   `-var, --variation <key>`: 使用的变体键 (仅支持一个)。
    *   `--style <key>`: 使用的全局风格键 (仅支持一个)。
    *   `--cref <url_or_path>`: 图像参考 URL 或本地路径 (支持自动上传本地图片)。
    *   `-m, --mode <mode>`: 生成模式 (`relax`, `fast`, `turbo`，默认: `relax`)。
    *   `--hook-url <url>`: Webhook 回调地址。
    *   `--wait`: 提交任务后阻塞等待任务完成并下载结果 (仅在未使用 `--hook-url` 时生效)。
    *   `--clipboard`, `--save-prompt`
*   **注意:** 成功提交后会更新 `last_job.json`。

### `recreate`

使用指定任务的原始 Prompt 和 Seed 重新生成图像。

*   **用法:** `crc recreate <identifier> [options...]`
*   **参数:**
    *   `identifier` (必需): 要重新生成的原始任务标识符 (Job ID, 前缀或文件名)。
*   **主要选项:**
    *   `--cref <url_or_path>`: 提供**新的**图像参考 URL 或本地路径 (可选)。
    *   `--hook-url <url>`: Webhook 回调地址。
    *   `--wait`: 提交任务后阻塞等待任务完成并下载结果 (仅在未使用 `--hook-url` 时生效)。
*   **注意:** 成功提交后会更新 `last_job.json`。

### `action`

对现有任务执行操作 (如 Upscale, Variation, Zoom, Pan 等)。

*   **用法:** `crc action [action_code] [identifier] [options...]`
*   **参数:**
    *   `action_code`: 要执行的操作代码 (例如 `upsample1`, `variation2`)。使用 `crc action --list` 查看所有可用代码。
    *   `identifier` (可选): 要操作的任务标识符 (Job ID 或本地文件名)。如果省略，默认使用 `last_job.json` 中记录的上一个任务 ID。
*   **主要选项:**
    *   `--list`: 列出所有可用的 `action_code` 及其说明并退出。
    *   `--wait`: 提交操作后阻塞等待任务完成并下载结果 (仅在未使用 `--hook-url` 时生效)。
    *   `-m, --mode <mode>`: 操作使用的生成模式 (`relax`, `fast`, `turbo`，默认: `fast`)。
    *   `--hook-url <url>`: Webhook 回调地址。
*   **注意:** 成功提交后会更新 `last_job.json`。
*   **示例:**
    ```bash
    # 对上一个任务执行 V1 操作并等待完成
    crc action variation1 --wait

    # 对指定 Job ID 执行 U1 操作，使用 relax 模式
    crc action upsample1 abc-123-def-456 --mode relax
    ```

### `select`

切割由 Upscale 操作生成的四格图，并选择保存指定部分。

*   **用法:** `crc select [image_path] -s <u1|u2|u3|u4...> [options...]`
*   **参数:**
    *   `image_path` (可选): 要切割的本地图片文件路径。如果省略，默认使用 `last_job.json` 记录的上一个任务 ID 查找对应的文件路径。
*   **主要选项:**
    *   `-s, --select <u1|u2|u3|u4...>` (必需): 指定要保留的部分 (例如 `-s u1 u3`)。
    *   `-o, --output-dir <dir>`: 指定输出目录 (默认与原图相同)。

### `view`

查看指定任务的详细信息（本地元数据和 API 最新状态）。

*   **用法:** `crc view [identifier] [options...]`
*   **参数:**
    *   `identifier` (可选): 要查看的任务标识符 (Job ID, 前缀或文件名)。如果省略，默认使用 `last_job.json` 记录的上一个任务 ID。
*   **主要选项:**
    *   `--remote`: 强制仅从 API 获取信息，忽略本地元数据。
    *   `--save`: 如果从 API 获取的任务状态为成功且包含图片 URL，则下载图片并更新本地元数据。

### `blend`

将 2 到 5 张本地图片混合生成一张新图。

*   **用法:** `crc blend <image_path1> <image_path2> [<path3>...] [options...]`
*   **参数:**
    *   `image_paths` (必需): 2 到 5 个本地图片文件路径。
*   **主要选项:**
    *   `--dimensions <dim>`: 输出图像比例 (`PORTRAIT`, `SQUARE`, `LANDSCAPE`，默认: `SQUARE`)。
    *   `-m, --mode <mode>`: 生成模式 (`relax`, `fast`, `turbo`，默认: `fast`)。
    *   `--hook-url <url>`: Webhook 回调地址。

### `describe`

根据上传的图片生成相关提示词。

*   **用法:** `crc describe <image_path_or_url> [options...]`
*   **参数:**
    *   `image_path_or_url` (必需): 本地图片路径或可公开访问的图片 URL。
*   **主要选项:**
    *   `--hook-url <url>`: Webhook 回调地址。

### `list-tasks`

列出本地 `images_metadata.json` 文件中记录的任务/作业。

*   **用法:** `crc list-tasks [options...]`
*   **主要选项:**
    *   `-l, --limit <num>`: 显示最近的任务数量 (默认 20)。
    *   `--status <status>`: 按状态过滤 (需要元数据中有此字段)。
    *   `-c, --concept <key>`: 按概念过滤。
    *   `--sort-by <field>`: 排序字段 (`timestamp`, `status`, `concept`，默认 `timestamp`)。
    *   `--asc`: 升序排序 (默认降序)。
    *   `-r, --remote`: 从远程API获取任务列表而非本地元数据。当本地保存失败时，可用此选项查看远程任务状态。
    *   `-v, --verbose`: 显示详细信息，包括完整提示词和额外元数据。

---

## 目录结构和配置

### 系统目录结构

系统使用以下目录结构来管理不同类型的数据：

#### 全局配置目录 (`~/.crc/`)
```
~/.crc/
├── prompts_config.json     # 用户自定义的概念配置
├── logs/                   # 系统日志文件
├── state/                  # 系统状态文件
│   └── config.json        # 用户配置（如输出目录设置）
└── metadata/              # 全局任务元数据
    └── images_metadata.json
```

#### 项目工作目录（当前目录）
```
./your-project/
├── images/                # 生成的图片文件
│   ├── concept1/         # 按概念分类的图片
│   ├── concept2/
│   └── general/          # 未指定概念的图片
├── prompts/              # 保存的提示词文件
│   ├── concept1.txt
│   └── concept2.txt
└── .env                  # 项目级API密钥配置（可选）
```

### 配置文件说明

#### 全局配置
*   **`~/.crc/prompts_config.json`**: 存储所有预设的创意概念、变体、全局风格、宽高比、质量和版本设置。通过 `crc generate` 命令生成的新概念会自动保存到此文件。
*   **`~/.crc/state/config.json`**: 存储用户偏好设置，如自定义输出目录等。

#### 项目级文件
*   **`./images/`**: 当前项目的图片文件，按概念自动分类到子目录中。
*   **`./prompts/`**: 使用 `--save-prompt` 选项保存的提示词文件。
*   **`./.env`**: 项目级API密钥配置文件（可选，会覆盖全局环境变量）。

### 数据分离原则

| 数据类型 | 保存位置 | 作用域 | 说明 |
|---------|---------|--------|------|
| **配置文件** | `~/.crc/prompts_config.json` | 全局 | 跨项目共享的概念和设置 |
| **元数据** | `~/.crc/metadata/` | 全局 | 所有任务的历史记录和状态 |
| **图片文件** | `./images/{concept}/` | 项目 | 每个项目独立管理图片 |
| **提示词文件** | `./prompts/` | 项目 | 与项目代码一起版本控制 |

## 图像元数据

生成的图像元数据存储在 `~/.crc/metadata/images_metadata.json` 文件中。每个图像的元数据包含以下信息：

- **id**: 唯一标识符 (内部生成)
- **job_id**: TTAPI 任务 ID
- **filename**: 图像文件名
- **filepath**: 图像文件路径
- **url**: 原始图像 URL
- **prompt**: 生成图像的提示词
- **concept**: 使用的创意概念 (如果适用)
- **variations**: 使用的变体列表 (如果适用)
- **global_styles**: 使用的全局风格列表 (如果适用)
- **components**: 可用的操作组件（从 API 获取，如 upsample1、variation1 等）
- **seed**: 生成图像的种子值（如果有）
- **created_at**: 元数据记录创建时间
- **metadata_updated_at**: 元数据最后更新时间
- **original_job_id**: 如果是由 `recreate` 或 `action` 生成，记录其来源的任务 ID
- **action_code**: 如果是由 `action` 生成，记录执行的操作代码

## 图像后处理

生成的图像需要进行后处理以符合 Cell Reports Medicine 的要求：

1. 使用图像编辑软件（如 Photoshop、GIMP 或 Affinity Photo）打开图片
2. 调整图片尺寸为 8 1/8 x 10 7/8 英寸，分辨率至少 300 dpi
3. 确保关键视觉元素在安全区域内
4. 保存为高分辨率 TIF 或 PSD 文件

## 提交流程

1. 准备高分辨率 TIF/PSD 文件
2. 创建低分辨率 JPG/PDF 副本（文件大小小于 1 MB）
3. 准备包含作者列表、文章标题和封面图例的 Word 文档
4. 通过 FTP 上传文件
5. 通知制作编辑

## 常见问题

### 如何添加新的创意概念？

有两种方式添加新的创意概念：

1. **自动生成**：使用 `crc generate --concept <概念名> --prompt "<描述>"` 命令，系统会自动生成概念并保存到 `~/.crc/prompts_config.json`。
2. **手动编辑**：直接编辑 `~/.crc/prompts_config.json` 文件，按照现有格式添加新的概念和变体。

### 生成的文件保存在哪里？

- **图片文件**：保存在当前工作目录的 `./images/{concept}/` 子目录中
- **提示词文件**：使用 `--save-prompt` 选项时，保存在当前工作目录的 `./prompts/` 目录中
- **元数据**：保存在 `~/.crc/metadata/images_metadata.json` 中，用于全局任务管理

### 如何在不同项目中使用？

1. 切换到项目目录：`cd /path/to/your-project`
2. 运行命令：`crc create --concept <概念> --prompt "<提示>"`
3. 图片会保存到该项目目录下的 `images/` 文件夹中
4. 配置和概念在所有项目间共享

**使用示例**：
```bash
# 项目A
cd /Users/username/projectA
crc create --concept ca --prompt "细胞防御病毒"
# 图片保存到: /Users/username/projectA/images/ca/

# 项目B
cd /Users/username/projectB
crc create --concept ca --prompt "细胞防御病毒"
# 图片保存到: /Users/username/projectB/images/ca/

# 两个项目使用相同的概念配置，但图片分别保存在各自的目录中
```

### 如何获取最佳效果？

1. 尝试不同的创意概念和变体
2. 调整宽高比以匹配 Cell 杂志封面要求
3. 使用高质量设置生成图像
4. 使用 `view` 命令查看已完成任务的 Seed，然后使用 `crc recreate <identifier>` 尝试微调参数重新生成。
5. 进行专业的后期处理

### API 调用失败怎么办？

1. 检查 API 密钥是否正确设置 (环境变量 `TTAPI_API_KEY` 或 `.env` 文件)。
2. 确认 API 配额是否充足。
3. 检查网络连接。
4. 查看 `~/.crc/logs/` 目录中的日志文件获取详细错误信息。
5. 使用 `crc action --list` 确认操作代码是否正确。
6. 尝试不同的 `--mode` (例如从 `relax` 切换到 `fast`)。

### 如何初始化系统？

首次使用前需要运行初始化命令：

```bash
crc init
```

这会在 `~/.crc/` 目录下创建必要的目录结构和配置文件。可以使用 `--output-dir` 选项指定自定义的默认输出目录。

---

如有任何问题或建议，请联系项目维护者。