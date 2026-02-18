#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import importlib
import pkgutil
import logging

from fastmcp import FastMCP
import image_gen_mcp.apps as apps_pkg

logger = logging.getLogger(__name__)

mcp = FastMCP("Image Generator MCP Server")


def _load_plugins():
    for _, name, _ in pkgutil.iter_modules(apps_pkg.__path__):
        try:
            module = importlib.import_module(f"image_gen_mcp.apps.{name}")
            if hasattr(module, "register"):
                module.register(mcp)
                logger.info(f"Plugin loaded: {name}")
            else:
                logger.debug(f"Plugin '{name}' has no register() function, skipping.")
        except Exception as e:
            logger.error(f"Failed to load plugin '{name}': {e}")


def create_server() -> FastMCP:
    _load_plugins()
    return mcp
