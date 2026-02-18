# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-19

### Changed
- **Major Refactoring**: Restructured project to separate core logic (`image_gen_mcp/core`) from application plugins (`image_gen_mcp/apps`).
- **Dependency Management**: Migrated fully to `uv` for package management, replacing `pip` and `requirements.txt`.
- **Documentation**: 
    - Updated `README.md` to reflect new installation and usage instructions using `uv`.
    - Rewrote `ARCHITECTURE.md` to match the actual file structure and unified layer descriptions.
    - Integrated scattered documentation into the root directory.
- **CLI**: Updated `scripts/start_mcp.sh` to use `uv` for environment checks and execution.

### Removed
- **Obsolete Directories**: Removed `.serena` and empty `docs` directories.
- **Legacy Files**: Removed references to missing files like `MCP_README.md`.

### Fixed
- **Testing**: Added `pytest` to development dependencies and verified CLI test suites.

## [0.1.0] - 2026-01-01

### Added
- Initial release of Cell Cover Generator MCP.
- Basic MCP server implementation with FastMCP.
- Integration with Midjourney API (TTAPI).
- CLI commands for creating and viewing tasks.
