# Cell 杂志封面生成器 - 使用示例

本文档提供了一些实际使用示例，帮助您快速上手 Cell 杂志封面生成工具。

## 基础示例

### 示例 1：生成基本 IFN 盾牌概念

```bash
# 查看所有可用概念
./generate_cover.sh list

# 生成基本 IFN 盾牌提示词
./generate_cover.sh generate concept_a

# 将提示词复制到剪贴板
./generate_cover.sh generate concept_a --clipboard
```

### 示例 2：探索不同变体

```bash
# 查看 concept_a 的所有变体
./generate_cover.sh variations concept_a

# 生成科学风格变体
./generate_cover.sh generate concept_a --variation scientific

# 生成戏剧性风格变体
./generate_cover.sh generate concept_a --variation dramatic
```

### 示例 3：尝试不同的创意概念

```bash
# 生成微观战场视角
./generate_cover.sh generate concept_a2 --variation detailed

# 生成细胞网络防御
./generate_cover.sh generate concept_a3 --variation network

# 生成抽象冲突
./generate_cover.sh generate concept_c --variation dynamic

# 生成流体力学风格
./generate_cover.sh generate concept_c2 --variation fluid

# 生成数字化免疫学
./generate_cover.sh generate concept_c3 --variation code
```

## 高级示例

### 示例 4：自定义宽高比和质量

```bash
# 生成方形高质量图像
./generate_cover.sh generate concept_a --aspect square --quality high

# 生成适合 Cell 杂志的比例
./generate_cover.sh generate concept_c --aspect cell_cover --quality high
```

### 示例 5：使用不同的 Midjourney 版本

```bash
# 使用 v5 版本
./generate_cover.sh generate concept_a --version v5

# 使用 v6 版本
./generate_cover.sh generate concept_c --version v6
```

### 示例 6：通过 API 直接生成图像

```bash
# 设置 API 配置（首次使用）
python3 generate_image.py --setup

# 使用预设概念生成图像
python3 generate_image.py --concept concept_a --variation scientific

# 使用自定义提示词生成图像
python3 generate_image.py --prompt "Your custom prompt here"
```

## 创意组合示例

以下是一些推荐的创意组合，可以产生不同风格的封面：

### 科学精确风格

```bash
./generate_cover.sh generate concept_a --variation scientific
./generate_cover.sh generate concept_a2 --variation detailed
```

### 艺术抽象风格

```bash
./generate_cover.sh generate concept_c --variation abstract
./generate_cover.sh generate concept_c2 --variation wave
```

### 未来科技风格

```bash
./generate_cover.sh generate concept_a2 --variation futuristic
./generate_cover.sh generate concept_c3 --variation code
```

### 动态戏剧风格

```bash
./generate_cover.sh generate concept_a --variation dramatic
./generate_cover.sh generate concept_c --variation dynamic
```

### 教育说明风格

```bash
./generate_cover.sh generate concept_a2 --variation educational
./generate_cover.sh generate concept_a3 --variation network
```

## 提示词修改示例

如果您想修改现有提示词，可以编辑 `prompts_config.json` 文件。以下是一些修改示例：

### 添加新变体

在 `concept_a` 的 `variations` 部分添加：

```json
"elegant": "elegant composition, refined color palette, sophisticated scientific aesthetic"
```

### 添加新概念

在 `concepts` 部分添加新概念：

```json
"concept_d": {
  "name": "治疗前后对比",
  "description": "展示IFN治疗前后的对比效果",
  "midjourney_prompt": "Split-screen scientific illustration showing before and after interferon treatment of monkeypox virus infection...",
  "variations": {
    "clinical": "clinical trial visualization, medical evidence presentation",
    "cellular": "cellular level comparison, microscopic detail",
    "patient": "patient outcome visualization, symptom reduction illustration",
    "data": "data-driven comparison, quantitative results visualization"
  }
}
```

## 最佳实践

1. **迭代生成**：先生成基本概念，然后基于结果进行调整
2. **多样化尝试**：尝试不同的概念和变体，不要局限于一种风格
3. **结合科学与艺术**：寻找科学准确性和视觉吸引力之间的平衡
4. **关注核心信息**：确保图像传达研究的核心发现和意义
5. **考虑目标读者**：针对 Cell Reports Medicine 的读者群体调整风格

希望这些示例能帮助您充分利用 Cell 杂志封面生成工具！