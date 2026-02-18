# HTTP Server Guide

## Overview

The **Image Generator MCP** platform can also run as a standalone HTTP API server, exposing the capabilities of its installed apps (like `cell_cover`) over REST.

## Architecture

The HTTP server wraps the core `image_gen_mcp` library. It is designed for scenarios where you need a standard web API rather than an MCP connection (e.g., connecting from a non-LLM client).

**Note**: The HTTP server currently focuses on exposing the **Cell Cover** app functionality. Future updates will make it a generic gateway for all plugins.

## Quick Start

### 1. Start the Server

```bash
# Using uv (Recommended)
uv run python -m server.main
```

Or using the legacy script:
```bash
./scripts/start_server.sh
```

### 2. Access the API

- **Swagger UI**: `http://localhost:8888/docs`
- **Health Check**: `http://localhost:8888/health`

## API Endpoints (Cell Cover)

The server exposes the following endpoints mapping to the Cell Cover plugin capabilities:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/concepts` | List available design concepts |
| POST | `/api/v1/create` | Create a new image generation task |
| GET | `/api/v1/tasks` | List recent tasks |
| GET | `/api/v1/tasks/{id}` | Get task details |
| POST | `/api/v1/tasks/{id}/action` | Perform action (Upscale/Variation) |

## Configuration

The HTTP server uses the same configuration as the MCP server:
- `~/.crc/prompts_config.json` for concepts.
- `TTAPI_API_KEY` environment variable for authentication.
- `SERVER_HOST` / `SERVER_PORT` env vars to control binding.
