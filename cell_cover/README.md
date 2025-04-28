# Cell 杂志封面生成器

这个工具集用于生成 Cell Reports Medicine 杂志封面的 Midjourney 提示词，并通过 TTAPI 获取生成的图像。

## 目录

- [功能概述](#功能概述)
- [安装与设置](#安装与设置)
- [使用指南](#使用指南)
  - [基本命令](#基本命令)
  - [创意概念](#创意概念)
  - [生成提示词](#生成提示词)
  - [生成图像](#生成图像)
  - [查询任务状态](#查询任务状态)
  - [异步模式](#异步模式)
- [配置文件](#配置文件)
- [图像元数据](#图像元数据)
- [图像后处理](#图像后处理)
- [提交流程](#提交流程)
- [常见问题](#常见问题)

## 功能概述

本工具集提供以下功能：

1. **提示词生成**：基于预设的创意概念生成 Midjourney 提示词，或使用OpenAI优化用户输入
2. **多样化变体**：每个创意概念有多个变体可供选择
3. **灵活配置**：可自定义宽高比、质量和 Midjourney 版本
4. **API 集成**：通过 TTAPI 直接生成图像并下载到本地
5. **多种操作支持**：支持 Upscale, Variation, Reroll 等后续操作。
6. **Seed 管理**：支持获取图像 Seed，并基于 Prompt 和 Seed 重新生成。
7. **异步生成**：支持通过 Webhook 异步接收生成结果
8. **概念持久化**：将AI优化的提示词保存为命名概念，方便重复使用
9. **元数据管理**：自动保存图像元数据，便于后续查询和管理
10. **日志记录**：详细的日志记录，便于排查问题
11. **统一命令入口**：通过 `crc` 命令访问所有功能。

## 安装与设置

### 前提条件

- Python 3.6+
- uv 包管理器（推荐）或 pip
- TTAPI 账户和 API 密钥
- OpenAI API 密钥（用于提示词优化）

### 安装步骤

1. 克隆或下载本项目到本地
2. 运行安装脚本安装依赖：

```bash
cd /path/to/your/project/cell_cover # 进入项目目录
chmod +x setup.sh
./setup.sh
```

该脚本会：
- 检查 Python 和 uv 环境。
- 使用 uv 安装 `requirements.txt` 中的依赖。
- 在 `$HOME/.local/bin` 目录下创建一个名为 `crc` 的全局命令。
- 检查 `$HOME/.local/bin` 是否在您的 PATH 环境变量中，如果不在则提示您添加。

3. 设置 API 密钥：

```bash
# 方法一：设置环境变量
export TTAPI_API_KEY="your_ttapi_key_here"
export OPENAI_API_KEY="your_openai_key_here"

# 方法二：创建 .env 文件 (在项目根目录下)
echo "TTAPI_API_KEY=your_ttapi_key_here" > .env
echo "OPENAI_API_KEY=your_openai_key_here" >> .env
```

4. (可选) 确保 Python 脚本有执行权限（通常 `setup.sh` 创建的 `crc` 命令会处理这个）：

```bash
# 如果直接运行 Python 脚本会用到，但推荐使用 crc
# chmod +x cell_cover/generate_cover.py
# chmod +x cell_cover/fetch_job_status.py
```

## 使用指南

### 基本命令

所有命令都通过 `crc` 命令执行。您可以在任何目录下运行 `crc` (前提是安装目录在 PATH 中)。

查看可用命令和帮助：
```bash
crc help
# 或者
crc <子命令> --help
```

### 创意概念

查看所有可用的创意概念：

```bash
crc list
```

查看特定概念的变体：

```bash
crc variations ca # 注意：这里概念名是 ca 而不是 concept_a
```

### 生成提示词

#### 使用AI优化提示词（新功能）

使用OpenAI API优化提示词：

```bash
# 基本用法：提供简单描述，由AI优化为详细提示词
crc generate --prompt "一个科幻城市景观"

# 附加风格和宽高比等参数
crc generate --prompt "宇宙中的深海生物" --style vibrant_colors dark_bg --aspect portrait

# 保存到剪贴板
crc generate --prompt "微观世界的分子舞蹈" --clipboard

# 持久化为新概念：将生成的提示词保存到prompts_config.json
crc generate --prompt "古代文明的神秘符号" --concept ancient_symbols

# 更新现有概念：用新生成的提示词更新已有概念
crc generate --prompt "改进版本的免疫细胞网络" --concept ca3
```

使用参数自定义生成：

```bash
# 指定质量和版本
crc generate --prompt "分子结构与DNA双螺旋" --quality high --version v6

# 使用参考图像
crc generate --prompt "科学视觉化的病毒结构" --cref https://example.com/reference.jpg
```

#### 使用现有提示词（传统方式）

基于预设概念生成提示词：

```bash
crc create -c ca

# 指定变体
crc create -c ca -var scientific

# 添加全局风格
crc create -c ca -var dramatic --style focus cinematic

# 使用其他参数
crc create -c ca -var vibrant --aspect portrait --quality high --version v6 --save-prompt
```

### 生成图像

使用 `create` 命令基于概念和变体生成图像：

```bash
# 基本用法 (使用 ca 概念的默认变体)
crc create -c ca

# 指定变体
crc create -c ca -var scientific

# 添加全局风格
crc create -c ca -var dramatic --style focus cinematic

# 使用其他参数
crc create -c ca -var vibrant --aspect portrait --quality high --version v6 --save-prompt
```

使用 `generate` 命令基于自由格式提示词生成图像：
```bash
crc generate -p "A photorealistic electron microscope view of a virus attacking a cell, detailed, cinematic lighting" --aspect landscape
```

使用 `recreate` 命令基于之前的任务 (使用其 Prompt 和 Seed) 重新生成图像：
```bash
# 使用文件名、Job ID 前缀或完整 Job ID 作为标识符
crc recreate <job_id_or_filename>

# 示例
crc recreate ca-abc123-scientific-focus-20240101_120000.png
crc recreate abc123 # 使用 Job ID 前缀
```
注意：`recreate` 命令需要原始任务的元数据中包含 `seed` 值。

### 管理和查询任务

列出历史任务：
```bash
# 默认显示本地元数据中的任务列表 (最近 50 条)
crc list

# 使用 --limit 限制本地列表数量
crc list --limit 10

# 使用 --remote 从 TTAPI 获取远程任务列表
crc list --remote

# 获取远程任务列表并指定页码和数量
crc list --remote --page 2 --limit 20
```

查看特定任务详情：
```bash
crc view <job_id>
```

获取任务的 Seed 值：
```bash
# 使用文件名、Job ID 前缀或完整 Job ID 作为标识符
crc seed <job_id_or_filename>

# 示例
crc seed ca-abc123-scientific-focus-20240101_120000.png
```
此命令会先检查本地元数据，如果未找到 Seed，会尝试从 API 获取并更新本地元数据。

恢复本地缺失的元数据：
```bash
crc restore --limit 50
```

### 执行后续操作 (Upscale, Variation, Reroll)

基于原始任务执行操作：
```bash
# 使用文件名、Job ID 前缀或完整 Job ID 作为标识符

# Upscale (放大第 N 张图)
crc upscale <job_id_or_filename> 2

# Variation (基于第 N 张图生成变体)
crc variation <job_id_or_filename> 3

# Reroll (重新执行原始 Prompt)
crc reroll <job_id_or_filename>
```

### 异步模式

当生成时间较长时，建议使用异步模式：

```bash
crc create -c ca --hook-url https://your-webhook.com/callback --notify-id your-custom-id

# 也可用于 recreate, upscale, variation, reroll 等命令
crc upscale <job_id> 1 --hook-url https://your-webhook.com/callback
```

当任务完成时，TTAPI 将发送回调请求到指定的 Webhook URL。

如果您没有 Webhook 服务，可以使用第三方服务如 webhook.site 或 requestbin.com 进行测试。

## 配置文件

所有提示词模板和设置都存储在 `prompts_config.json` 文件中。您可以：

- 通过手动编辑此文件来添加新的创意概念或修改现有的提示词
- 使用 `crc generate --prompt "..." --concept new_concept_key` 自动创建新概念
- 使用 `crc generate --prompt "..." --concept existing_key` 更新现有概念

配置文件中包含以下主要部分：

- **concepts**: 创意概念及其变体
- **global_styles**: 全局样式设置
- **aspect_ratios**: 支持的宽高比
- **quality_settings**: 图像质量设置
- **style_versions**: Midjourney版本设置

### 依赖项

为使用新版的`generate`命令优化提示词，需要安装以下额外依赖：

```bash
pip install openai python-dotenv
```

## 图像元数据

生成的图像元数据存储在 `metadata/images_metadata.json` 文件中。每个图像的元数据包含以下信息：

- **id**: 唯一标识符
- **job_id**: TTAPI 任务 ID
- **filename**: 图像文件名
- **filepath**: 图像文件路径
- **url**: 原始图像 URL
- **prompt**: 生成图像的提示词
- **concept**: 使用的创意概念
- **variation**: 使用的变体列表（如果有）
- **global_styles**: 使用的全局风格列表（如果有）
- **components**: 可用的操作组件（如 upsample1、variation1 等）
- **seed**: 生成图像的种子值（如果有）
- **created_at**: 创建时间
- **metadata_updated_at**: 元数据最后更新时间（例如通过 `crc seed` 更新时）

这些元数据可以用于后续的图像管理和操作。

后续操作（Upscale, Variation, Reroll）的结果元数据存储在 `metadata/actions_metadata.json` 中，包含新旧 Job ID、操作类型等信息。

### 创意概念

目前有以下创意概念可用：

#### IFN盾牌系列

1. **concept_a**: IFN盾牌（聚焦防御与治疗）
   - 展示细胞通过干扰素防御猴痘病毒的过程
   - 变体：scientific, minimalist, dramatic, vibrant

2. **concept_a2**: IFN盾牌 - 微观战场视角
   - 从微观视角展示免疫细胞与病毒的战斗
   - 变体：detailed, dramatic, educational, futuristic

3. **concept_a3**: IFN盾牌 - 细胞网络防御
   - 展示多个细胞协同工作形成防御网络
   - 变体：network, swarm, reinforcement, depth

#### 抽象冲突系列

1. **concept_c**: 抽象冲突与解决（聚焦艺术印象）
   - 高度风格化的抽象表现
   - 变体：abstract, dynamic, vibrant, balanced, scientific

2. **concept_c2**: 抽象冲突 - 流体力学与光波
   - 使用流体力学和光波美学表现免疫反应
   - 变体：fluid, wave, transformation, physics

3. **concept_c3**: 抽象冲突 - 数字化免疫学
   - 将免疫反应表现为数字化、算法化的视觉元素
   - 变体：data, code, fractal, futuristic

### 其他设置

- **全局风格 (Global Styles)**: 可通过 `--style` 参数在 `create` 和 `generate` 命令中使用，例如 `focus`, `cinematic`, `illustration`, `photorealistic`, `dark_bg`, `vibrant_colors`, `electron_microscope`。可在 `prompts_config.json` 中查看或添加。
- **宽高比**：portrait (3:4), square (1:1), landscape (4:3), cell_cover (0.75)
- **质量设置**：standard, high
- **Midjourney版本**：v5, v6

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

编辑 `prompts_config.json` 文件，按照现有格式添加新的概念和变体。

### 提示词生成后在哪里查看？

生成的提示词会直接用于 API 调用。如果需要查看或保存提示词文本，可以在 `create` 或 `generate` 命令中使用 `--save-prompt` 选项，提示词将保存在 `outputs` 目录中。

### 如何获取最佳效果？

1. 尝试不同的创意概念和变体
2. 调整宽高比以匹配 Cell 杂志封面要求
3. 使用高质量设置生成图像
4. 使用 `crc seed <identifier>` 获取成功的 Seed，然后使用 `crc recreate <identifier>` 尝试微调参数重新生成。
5. 进行专业的后期处理

### API 调用失败怎么办？

1. 检查 API 密钥是否正确
2. 确认 API 配额是否充足
3. 检查网络连接
4. 查看 API 响应中的错误信息

### 如何使用OpenAI优化我的提示词？

1. 确保已设置`OPENAI_API_KEY`环境变量或在`.env`文件中添加
2. 使用`crc generate --prompt "简单描述"`命令，提供您的基本想法
3. OpenAI将优化您的描述，生成详细、富有视觉描述性的Midjourney提示词
4. 如需保存为重复使用的概念，添加`--concept my_concept_name`参数

### 为什么我的OpenAI API调用失败？

1. 检查`OPENAI_API_KEY`是否正确设置
2. 确认API密钥有效且有足够的配额
3. 检查网络连接
4. 如果问题持续，可以添加`--debug`参数查看详细错误信息

---

如有任何问题或建议，请联系项目维护者。