
好的，我理解你的担忧。当前的代码结构确实有些混乱，主要是因为我们将不同类型的命令分散在两个主要的脚本（`generate_cover.py` 和 `fetch_job_status.py`）中处理，并且 `utils` 目录下的某些文件（如 `file_handler.py`）承担了过多的职责。

这是一个逐步优化的方案，旨在让代码结构更清晰、更易于维护，并减小单个文件的体积：

**核心目标：**

1.  **统一入口点：** 使用单一脚本处理所有 `crc` 命令的解析和分发。
2.  **命令模块化：** 将不同命令的实现逻辑拆分到独立的模块或处理函数中。
3.  **工具类细化：** 将功能庞杂的工具类（如 `file_handler.py`）拆分成更专注、单一职责的模块。
4.  **遵循规范：** 更好地遵循文件行数限制（<200行）、单一职责原则。

**优化方案步骤：**

**第一阶段：统一命令入口和分发**

1.  **创建新的主入口脚本：**
    *   新建文件 `cell_cover/cli.py` (或者叫 `main.py`)。
    *   将 `generate_cover.py` 和 `fetch_job_status.py` 中的所有 `argparse` 设置（包括子命令定义）**全部移动**到 `cli.py`。
    *   在 `cli.py` 中，`main` 函数负责解析参数 `args`。
2.  **创建命令分发逻辑：**
    *   在 `cli.py` 中，根据 `args.command` (或 `args.subcommand`)，调用相应的处理函数。
    *   **初期：** 这些处理函数可以暂时直接调用原来 `generate_cover.py` 和 `fetch_job_status.py` 中对应的函数逻辑（需要将这些逻辑封装成可调用的函数，并确保它们能接收必要的参数，如 `args`, `logger`, `api_key` 等）。
3.  **修改 `setup.sh`：**
    *   更新 `scripts/setup.sh` 中的 `crc` 命令脚本。
    *   移除 `case` 语句，让 `crc` 命令始终执行 `python3 -m cell_cover.cli "$@"`。
4.  **目标：**
    *   `cli.py` 成为所有命令的唯一入口。
    *   `generate_cover.py` 和 `fetch_job_status.py` 暂时变成包含可调用函数的库文件，不再直接处理命令行参数。
    *   `crc` 命令现在总是调用 `cli.py`。

**第二阶段：拆分命令处理逻辑**

1.  **创建命令处理模块目录：**
    *   在 `cell_cover/` 下创建新目录 `commands/`。
    *   在 `cell_cover/commands/` 下创建 `__init__.py` 文件。
2.  **为不同类型的命令创建模块：**
    *   `cell_cover/commands/generate.py`: 包含 `create` 和 `generate` 命令的实现逻辑。
    *   `cell_cover/commands/info.py`: 包含 `list`, `view`, `variations` 命令的实现逻辑。
    *   `cell_cover/commands/action.py`: 包含 `upscale`, `variation`, `reroll` 命令的实现逻辑。
    *   `cell_cover/commands/metadata.py`: 包含 `restore`, `seed` 命令的实现逻辑。（`seed` 可能也可以放在 `info.py`）
    *   `cell_cover/commands/image.py`: 包含 `select` 命令的实现逻辑。
    *   `cell_cover/commands/recreate.py`: 包含 `recreate` 命令的实现逻辑 (因为它结合了查找和生成)。
3.  **迁移逻辑：**
    *   将原来 `generate_cover.py` 和 `fetch_job_status.py` 中的具体命令实现代码，**迁移**到 `commands/` 下对应的模块中，封装成函数（例如 `handle_create(args, logger, api_key)`）。
    *   在 `cli.py` 中，导入这些新的命令处理模块，并在命令分发逻辑中调用相应的处理函数。
4.  **目标：**
    *   每个命令或一组相关命令的实现逻辑都封装在独立的模块中。
    *   `cli.py` 变得非常简洁，只负责解析参数和调用相应的命令处理函数。
    *   `generate_cover.py` 和 `fetch_job_status.py` 可以被安全地**删除**。

**第三阶段：细化工具类模块**

1.  **拆分 `file_handler.py`：**
    *   创建 `cell_cover/utils/metadata_manager.py`: 将所有与 `images_metadata.json` 和 `actions_metadata.json` 读写、查找、更新、恢复相关的函数（如 `save_image_metadata`, `save_action_metadata`, `find_initial_job_info`, `update_job_metadata`, `upsert_job_metadata`, `restore_metadata_from_job_list`）**移动**到这里。
    *   将 `cell_cover/utils/file_handler.py` 中剩余的函数（`ensure_directories`, `download_and_save_image`, `sanitize_filename`）保留，或者可以重命名为 `file_io.py` 或 `filesystem.py`。
2.  **审视其他工具类：**
    *   检查 `api.py` 是否仍然必要。如果它只是简单地重导出 `api_client.py` 的函数，可以考虑在所有使用的地方直接导入 `api_client.py`，然后删除 `api.py`。
    *   确保其他 `utils/` 模块（`config.py`, `log.py`, `prompt.py`, `image_splitter.py`, `image_uploader.py`）职责单一且清晰。
3.  **更新导入：**
    *   修改项目中所有受影响的 `import` 语句，确保它们指向正确的模块和函数。
4.  **目标：**
    *   工具类模块职责更单一，更易于理解和测试。
    *   代码结构更加扁平或按功能组织。

**第四阶段：清理、测试与文档**

1.  **删除无用文件：** 删除在第二阶段中被清空的 `generate_cover.py` 和 `fetch_job_status.py`。
2.  **代码审查：** 检查所有修改后的代码，确保符合风格规范、行数限制。
3.  **测试：**
    *   添加或更新单元测试，覆盖新的命令处理模块和细化后的工具类模块。
    *   执行集成测试，确保所有 `crc` 命令都能正常工作。
4.  **文档更新：**
    *   更新项目 README.md，反映新的代码结构和命令。
    *   添加必要的代码注释。

**优化后的预期结构 (示例):**

```
cell_cover/
├── cli.py              # 新的主入口，处理参数解析和分发
├── commands/
│   ├── __init__.py
│   ├── generate.py     # 处理 create, generate
│   ├── info.py         # 处理 list, view, variations
│   ├── action.py       # 处理 upscale, variation, reroll
│   ├── metadata.py     # 处理 restore, seed
│   ├── image.py        # 处理 select
│   └── recreate.py     # 处理 recreate
├── utils/
│   ├── __init__.py
│   ├── api_client.py   # 底层 API 调用
│   ├── config.py       # 配置加载
│   ├── log.py          # 日志设置
│   ├── metadata_manager.py # 元数据处理 (原 file_handler 的一部分)
│   ├── file_io.py      # 文件/目录操作、下载 (原 file_handler 的一部分)
│   ├── image_splitter.py
│   ├── image_uploader.py
│   └── prompt.py       # 提示词生成
├── metadata/
│   ├── images_metadata.json
│   └── actions_metadata.json
├── images/
├── outputs/
└── selected/
tests/
    ├── ... (单元测试和集成测试)
scripts/
    └── setup.sh        # 更新后的 crc 包装脚本
requirements.txt
README.md
.env (可选)
```

**实施建议：**

*   **分阶段进行：** 建议按照上面四个阶段逐步进行，每个阶段完成后进行测试，确保功能正常。
*   **版本控制：** 在开始前和每个阶段完成后，使用 Git 进行提交，方便回滚。
*   **小步快跑：** 在每个阶段内，也可以将大的步骤拆分成更小的修改和提交。

这个方案旨在系统性地解决当前结构混乱的问题，提高代码的可读性、可维护性和可测试性。你觉得这个方案怎么样？我们可以从第一阶段开始吗？
