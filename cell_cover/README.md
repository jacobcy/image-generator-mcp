# Cell 杂志封面生成器

这个工具集用于生成 Cell Reports Medicine 杂志封面的 Midjourney 提示词，并通过 API 获取生成的图像。

## 目录

- [功能概述](#功能概述)
- [安装与设置](#安装与设置)
- [使用指南](#使用指南)
  - [基本命令](#基本命令)
  - [创意概念](#创意概念)
  - [生成提示词](#生成提示词)
  - [生成图像](#生成图像)
- [配置文件](#配置文件)
- [图像后处理](#图像后处理)
- [提交流程](#提交流程)
- [常见问题](#常见问题)

## 功能概述

本工具集提供以下功能：

1. **提示词生成**：基于预设的创意概念生成 Midjourney 提示词
2. **多样化变体**：每个创意概念有多个变体可供选择
3. **灵活配置**：可自定义宽高比、质量和 Midjourney 版本
4. **API 集成**：通过 TTAPI 直接生成图像并下载到本地

## 安装与设置

### 前提条件

- Python 3.6+
- uv 包管理器（推荐）或 pip
- TTAPI 账户和 API 密钥

### 安装步骤

1. 克隆或下载本项目到本地
2. 运行安装脚本安装依赖：

```bash
cd /Users/chenyi/Library/Mobile Documents/com~apple~CloudDocs/paper
chmod +x setup.sh
./setup.sh
```

3. 设置 API 配置（如果需要通过 API 生成图像）：

```bash
cd cell_cover
python3 generate_cover.py --setup
```

## 使用指南

### 基本命令

所有命令都通过 `generate_cover.sh` 脚本执行：

```bash
cd /Users/chenyi/Library/Mobile Documents/com~apple~CloudDocs/paper/cell_cover
chmod +x generate_cover.sh  # 确保脚本有执行权限
```

### 创意概念

查看所有可用的创意概念：

```bash
./generate_cover.sh list
```

查看特定概念的变体：

```bash
./generate_cover.sh variations concept_a
```

### 生成提示词

生成基本提示词：

```bash
./generate_cover.sh generate concept_a
```

生成带变体的提示词：

```bash
./generate_cover.sh generate concept_a --variation scientific
```

生成提示词并复制到剪贴板：

```bash
./generate_cover.sh generate concept_c --variation dynamic --clipboard
```

自定义宽高比、质量和版本：

```bash
./generate_cover.sh generate concept_a2 --aspect portrait --quality standard --version v5
```

### 生成图像

如果您已经设置了 API 配置，可以直接生成图像：

```bash
python3 generate_image.py --concept concept_a --variation scientific
```

使用自定义提示词生成图像：

```bash
python3 generate_image.py --prompt "Your custom prompt here"
```

## 配置文件

所有提示词模板和设置都存储在 `prompts_config.json` 文件中。您可以编辑此文件来添加新的创意概念或修改现有的提示词。

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

生成的提示词将保存在 `outputs` 目录中，并显示在终端上。如果使用 `--clipboard` 选项，提示词也会被复制到剪贴板。

### 如何获取最佳效果？

1. 尝试不同的创意概念和变体
2. 调整宽高比以匹配 Cell 杂志封面要求
3. 使用高质量设置生成图像
4. 生成多个图像并选择最佳效果
5. 进行专业的后期处理

### API 调用失败怎么办？

1. 检查 API 密钥是否正确
2. 确认 API 配额是否充足
3. 检查网络连接
4. 查看 API 响应中的错误信息

---

如有任何问题或建议，请联系项目维护者。