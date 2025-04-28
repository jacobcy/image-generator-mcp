# PRD: crc generate 命令 (v4)

**命令名称**: `crc generate`

**目标**: 利用 OpenAI API 优化用户提供的核心文本，生成高质量的 Midjourney 提示词主干，然后附加指定的 Midjourney 参数。提供将最终生成的完整提示词持久化为命名概念的选项。

**使用场景**:
*   用户有一个初步的想法或关键词 (`--prompt`)，希望 AI 帮助优化成更丰富、更具描述性的 Midjourney 提示词核心部分。
*   用户希望在生成提示词后，自动附加常用的 Midjourney 参数（如宽高比、版本、风格等）。
*   用户希望将最终生成并带有参数的完整提示词保存为命名概念 (`--concept`)，方便后续复用或分享。
*   用户希望用新生成的完整提示词更新已有的概念。

**用法**:

```bash
crc generate --prompt <TEXT> [OPTIONS]
```

**参数 (OPTIONS)**:

| 参数              | 类型              | 是否必须 | 默认值        | 描述                                                                                                                                                                                                                            |
| :---------------- | :---------------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--prompt TEXT`   | `string`          | **必需** | `None`         | 提供基础文本或想法。这部分内容将作为唯一输入，交由 OpenAI API 进行优化和扩展，生成最终 Midjourney 提示词的**核心文本部分**。                                                                                                           |
| `--concept TEXT`  | `string`          | 可选     | `None`         | **（用于持久化）** 指定一个概念键 (key)。如果提供此参数，命令执行成功后，会将最终生成的**完整提示词**（核心文本 + 附加参数）保存或更新到 `prompts_config.json` 文件中与此 `<key>` 关联的条目下的 `midjourney_prompt` 字段。 |
| `--variation TEXT`| `List[string]`    | 可选     | `None`         | **（当前版本不直接送入AI）** 暂不直接影响 AI 输出，保留供未来扩展或用于文件名/元数据。                                                                                                                                              |
| `--style TEXT`    | `List[string]`    | 可选     | `None`         | **（主要用于参数附加）** 指定全局风格。如果是 `prompts_config.json` 中 `global_styles` 的有效键，其对应的 Midjourney 参数（如 `--s xxx` 或仅文本描述）将被查找并附加到最终提示词末尾。自定义文本风格目前不附加。                |
| `--aspect TEXT`   | `string`          | 可选     | `"square"`     | 指定宽高比。使用 `prompts_config.json` 中 `aspect_ratios` 的键。对应的 Midjourney 参数 (`--ar`) 会附加到最终提示词的末尾。                                                                                                        |
| `--quality TEXT`  | `string`          | 可选     | `"high"`       | 指定图像质量。使用 `prompts_config.json` 中 `quality_settings` 的键。对应的 Midjourney 参数 (`--q`) 会附加到最终提示词的末尾。                                                                                                   |
| `--version TEXT`  | `string`          | 可选     | `"v6"`         | 指定 Midjourney 版本。使用 `prompts_config.json` 中 `style_versions` 的键。对应的 Midjourney 参数 (`--v`) 会附加到最终提示词的末尾。                                                                                                 |
| `--cref TEXT`     | `string`          | 可选     | `None`         | **（当前版本不直接送入AI）** 提供一个参考图像的 URL。Midjourney 的 `--cref URL` 参数会附加到最终提示词的末尾。                                                                                                                     |
| `--clipboard`     | `boolean` (flag)  | 可选     | `False`        | 将最终生成的完整提示词复制到系统剪贴板。                                                                                                                                                                                           |
| `--save-prompt`   | `boolean` (flag)  | 可选     | `False`        | **（不推荐，优先使用 --concept）** 将最终生成的完整提示词保存到 `output` 目录下的文本文件中（基于时间戳命名）。                                                                                                                    |

**行为**:

1.  **参数检查**: 检查 `--prompt` 是否已提供。
2.  **构建元提示词**: 创建一个发送给 OpenAI API 的 "元提示词"，内容类似："请将以下文本优化并扩展为一个高质量、富有描述性的 Midjourney 提示词核心内容：`[--prompt 内容]`。请以 JSON 格式返回结果，包含一个键 `optimized_prompt`，其值为优化后的文本。"
3.  **调用 OpenAI**:
    *   加载 `OPENAI_API_KEY`。
    *   调用 OpenAI API。
    *   处理 API 响应，解析 JSON，提取 `optimized_prompt` 的值作为 `core_prompt_text`。
4.  **收集附加参数**:
    *   初始化一个空列表 `params_to_append`。
    *   如果提供了 `--cref URL`，添加 `--cref URL` 到列表。
    *   查找 `--aspect`, `--quality`, `--version` 在 `prompts_config.json` 中对应的参数代码，添加到列表。
    *   遍历 `--style` 列表：
        *   对于每个 style key，检查是否存在于 `prompts_config.json` 的 `global_styles` 中。
        *   如果存在，获取对应的值（可能是描述性文本或包含 `--s` 的参数代码）。将此值添加到 `params_to_append` 列表。
5.  **组合最终提示词**: 将 `core_prompt_text` 和 `params_to_append` 列表中的所有参数字符串用空格连接起来，形成 `final_prompt`。
6.  **输出与保存**:
    *   在控制台打印 `final_prompt`。
    *   处理 `--clipboard`。
    *   **处理持久化 (`--concept`)**: 如果提供了 `--concept <key>`：
        *   读取 `cell_cover/prompts_config.json` 文件。
        *   检查 `<key>` 是否存在于 `concepts`。
        *   如果存在，更新 `concepts[key]['midjourney_prompt'] = final_prompt`。
        *   如果不存在，按照以下结构创建新条目：
            ```json
            "key": {
              "name": f"Generated: {key}",
              "description": f"Generated from prompt: {prompt[:50]}...", // 使用原始输入 prompt
              "midjourney_prompt": final_prompt, // 保存最终完整提示词
              "variations": {}
            }
            ```
        *   将修改后的数据（使用 `json.dump` 并设置 `indent=2` 和 `ensure_ascii=False` 以保持格式和中文）写回 `cell_cover/prompts_config.json` 文件 (确保原子性写入)。
        *   打印持久化状态。
    *   处理 `--save-prompt` (如果需要)。
7.  **错误处理**: 处理 API 错误、文件 I/O 错误、JSON 解析错误等。

**依赖**:
*   `openai`, `python-dotenv`, `pyperclip` (可选)。

**配置文件**:
*   `.env`: 含 `OPENAI_API_KEY`。
*   `cell_cover/prompts_config.json`: 用于读取参数映射和读/写概念。

