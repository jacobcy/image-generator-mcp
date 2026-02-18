# 🎯 智能参数解析功能使用指南

## 概述

新的 `crc create` 命令支持智能参数解析，可以自动识别和处理提示词中的 Midjourney 参数。

## 支持的参数

| 参数 | 格式 | 说明 | 示例 |
|------|------|------|------|
| `--ar` | `--ar 16:9` | 纵横比 | `--ar 16:9`, `--ar 1:1` |
| `--v` | `--v 6` | 版本 | `--v 6`, `--v 7`, `--v niji` |
| `--style` | `--style raw` | 风格 | `--style raw`, `--style cute` |
| `--q` | `--q 2` | 质量 | `--q 1`, `--q 2` |
| `--s` | `--s 500` | 风格化 | `--s 100`, `--s 1000` |
| `--chaos` | `--chaos 50` | 混乱度 | `--chaos 20`, `--chaos 80` |
| `--weird` | `--weird 100` | 怪异度 | `--weird 50`, `--weird 200` |
| `--seed` | `--seed 12345` | 种子 | `--seed 12345` |
| `--no` | `--no blur` | 负面词 | `--no blur`, `--no hands` |
| `--cref` | `--cref url` | 字符参考 | `--cref https://...` |
| `--cw` | `--cw 80` | 参考权重 | `--cw 50`, `--cw 100` |
| `--tile` | `--tile` | 平铺 | `--tile` |
| `--video` | `--video` | 视频 | `--video` |

## 使用方式

### 1. 提示词中包含参数（推荐）

```bash
# 直接在提示词中包含 Midjourney 参数
crc create -p "Modern laboratory backdrop --ar 16:9 --style raw --v 6"

# 复杂提示词示例
crc create -p "DNA helix structure, molecular biology, scientific illustration --ar 16:9 --style raw --s 500 --chaos 30 --v 6"
```

### 2. 纯命令行参数

```bash
# 使用命令行参数
crc create -p "Modern laboratory backdrop" --ar 16:9 --style raw --version v6

# 使用短参数
crc create -p "Cell membrane structure" --ar 1:1 -s 500 -v v6
```

### 3. 混合使用（CLI 参数优先）

```bash
# 提示词中有参数，CLI 参数会覆盖
crc create -p "Laboratory --ar 1:1 --style raw" --ar 16:9 --style cute
# 结果：aspect_ratio=16:9, style=cute
```

### 4. 概念与参数结合

```bash
# 使用预设概念并添加参数
crc create --concept cell_membrane -p "加入蓝色光效" --ar 16:9 --chaos 20
```

## 参数优先级

1. **CLI 显式参数**（最高优先级）
2. **提示词中的参数**
3. **配置文件默认值**（最低优先级）

## 实际应用场景

### 场景1：从其他平台复制提示词

```bash
# 直接粘贴从 Discord 复制的完整提示词
crc create -p "Modern laboratory backdrop with DNA helix and medical instruments, clean professional presentation style, soft blue lighting, subtle Chinese national elements, minimalist design --ar 16:9 --style raw --v 6"
```

### 场景2：快速参数调整

```bash
# 基础提示词
crc create -p "mitochondria energy production --ar 1:1 --style raw" --ar 16:9
# CLI 的 --ar 16:9 会覆盖提示词中的 --ar 1:1
```

### 场景3：批量生成

```bash
# 使用变量批量生成不同版本
PROMPT="cell division process --ar 16:9 --style raw"

crc create -p "$PROMPT" --v 6
crc create -p "$PROMPT" --v 7
crc create -p "$PROMPT" --v niji6
```

## 注意事项

1. **参数验证**：系统会自动验证参数有效性
2. **错误提示**：无效参数会显示详细错误信息
3. **向后兼容**：完全兼容旧版本的使用方式
4. **智能解析**：自动识别和清理提示词中的参数

## 调试和测试

```bash
# 查看详细日志
crc create -p "your prompt --ar 16:9" --verbose

# 只生成提示词不提交（使用 generate 命令）
crc generate -p "your prompt --ar 16:9"
```

这个新功能让您可以：
- ✅ 直接复制粘贴其他平台的提示词
- ✅ 灵活调整参数而无需记忆复杂命令
- ✅ 快速批量生成不同版本的图像
- ✅ 保持工作流程的连贯性 