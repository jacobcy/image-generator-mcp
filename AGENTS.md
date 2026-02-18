# AI Agents & Tools Documentation

This document describes the AI agents and tools available in the **Image Generator MCP** platform. The system is designed as a modular platform where different image generation capabilities are provided as pluggable "Apps".

## Core Platform

The **Image Generator MCP** provides the foundational infrastructure:
- **Server**: A FastMCP-based server that hosts all tools.
- **Plugin System**: Dynamically loads apps from `image_gen_mcp/apps/`.
- **Config & Logging**: Centralized configuration management.

## Available Apps (Agents)

### 1. Cell Cover Generator (`cell_cover`)
A specialized agent for designing scientific journal covers (specifically for Cell Reports Medicine). It understands scientific concepts and translates them into Midjourney prompts.

**Tools Provided:**

- **`create_image`**
  - **Description**: Creates a new image generation task.
  - **Capabilities**: Handles prompts, aspect ratios, styles, and specific scientific concepts.
  - **Usage**: `create_image(prompt="mitochondria", concept="cell_energy", aspect_ratio="16:9")`

- **`list_concepts`**
  - **Description**: Lists available scientific design concepts (e.g., "cell_membrane", "dna_helix").
  - **Usage**: LLMs use this to discover valid concept keys for `create_image`.

- **`list_variations`**
  - **Description**: Lists style variations for a specific concept.
  - **Usage**: `list_variations(concept_key="cell_membrane")`

- **`list_tasks`**
  - **Description**: Lists recent image generation tasks and their status.
  - **Usage**: Monitor progress of generation jobs.

- **`view_task`**
  - **Description**: Retrieves detailed metadata for a specific task (including image URLs).
  - **Usage**: `view_task(task_id="...")`

- **`perform_action`**
  - **Description**: Executes Midjourney actions like Upscale (U1-U4), Variation (V1-V4), or Reroll.
  - **Usage**: `perform_action(task_id="...", action_code="upsample1")`

- **`describe_image`**
  - **Description**: Generates a prompt description from an existing image file or URL.
  - **Usage**: Reverse-engineer prompts from reference images.

**Resources Provided:**

- **`file://concepts.json`**: Raw configuration of all design concepts.
- **`file://tasks.json`**: Read-only view of the recent task history.

## Future Apps

The platform is ready to host additional agents, such as:
- **`poster_gen`**: For academic conference posters.
- **`logo_gen`**: For project branding.
- **`figure_gen`**: For scientific paper figures.

To add a new agent, simply create a new directory in `image_gen_mcp/apps/` and implement a `register(mcp)` function.
