

**拆分方案建议：**

将 `file_handler.py` 拆分为以下三个文件，每个文件负责一部分明确的功能：

1.  **`filesystem_utils.py`**: 负责通用的文件系统操作和路径管理。
    *   **职责**: 提供基础的文件/目录操作，如确保目录存在、清理文件名、定义和提供基础路径常量。
    *   **包含内容**:
        *   常量定义：`UTILS_DIR`, `BASE_DIR`, `OUTPUT_DIR`, `IMAGE_DIR`, `META_DIR`, `METADATA_FILENAME`, `ACTIONS_METADATA_FILENAME`, `MAX_FILENAME_LENGTH` （可以考虑将元数据文件名常量放在 `metadata_manager.py` 中，但放在这里统一管理路径也可以）。
        *   函数：`sanitize_filename()`, `ensure_directories()`。

2.  **`image_handler.py`**: 专注于图像文件的处理，主要是下载。
    *   **职责**: 处理从 URL 下载图像并保存到本地文件系统的逻辑。
    *   **包含内容**:
        *   函数：`download_and_save_image()`。
    *   **依赖**: 此模块需要从 `filesystem_utils.py` 导入路径常量 (`IMAGE_DIR`) 和 `ensure_directories`, `sanitize_filename` 函数。它也需要从 `metadata_manager.py` 导入元数据保存函数 (`save_image_metadata`, `save_action_metadata`)，因为它在下载成功后会调用它们。

3.  **`metadata_manager.py`**: 专门负责处理 `images_metadata.json` 和 `actions_metadata.json` 这两个 JSON 文件。
    *   **职责**: 封装所有对元数据文件的读、写、更新、查询和恢复操作。
    *   **包含内容**:
        *   函数：`save_image_metadata()`, `save_action_metadata()`, `restore_metadata_from_job_list()`, `find_initial_job_info()`, `update_job_metadata()`, `upsert_job_metadata()`。
    *   **依赖**: 此模块需要从 `filesystem_utils.py` 导入元数据文件路径常量 (`METADATA_FILENAME`, `ACTIONS_METADATA_FILENAME`) 以及可能的 `ensure_directories` 和 `sanitize_filename` (用于 `restore_metadata_from_job_list`)。

**拆分后的 `utils` 目录结构（示意）：**

```
cell_cover/
└── utils/
    ├── __init__.py
    ├── filesystem_utils.py  # <-- 新增
    ├── image_handler.py     # <-- 新增
    ├── metadata_manager.py  # <-- 新增
    ├── prompt.py
    ├── config.py
    ├── log.py
    ├── api_client.py
    └── image_uploader.py
    # file_handler.py 将被移除
```

**实施步骤：**

1.  在 `cell_cover/utils/` 目录下创建上述三个新文件 (`filesystem_utils.py`, `image_handler.py`, `metadata_manager.py`)。
2.  将 `file_handler.py` 中的常量和函数，按照上面的职责划分，分别移动到对应的新文件中。
3.  仔细更新所有必要的 `import` 语句：
    *   在新文件中，导入它们彼此之间或从 `filesystem_utils.py` 需要的函数或常量。
    *   在项目其他地方（如 `cli.py`, `commands/create.py`, `commands/fetch_job_status.py` 等）原来导入 `file_handler` 的地方，现在需要改为从新的模块导入对应的函数。例如，`from .utils.file_handler import find_initial_job_info` 需要改为 `from .utils.metadata_manager import find_initial_job_info`。
4.  确认所有功能正常后，删除原始的 `cell_cover/utils/file_handler.py` 文件。

**优点：**

*   **职责单一**: 每个模块的功能更清晰、更集中。
*   **可读性提高**: 代码更容易理解和维护。
*   **可测试性增强**: 可以更容易地对元数据管理、图像下载等逻辑进行单元测试。

