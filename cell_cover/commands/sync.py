#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from typing import Optional, List, Dict, Any

from ..utils.sync_metadata import sync_tasks

def handle_sync(
    logger: logging.Logger,
    api_key: str,
    metadata_dir: str,
    output_dir: str,
    state_dir: str,
    silent: bool = False # Add silent option if needed
):
    """Handles the sync command by calling the core sync_tasks function.

    Args:
        logger: Logger instance.
        api_key: TTAPI API key.
        metadata_dir: Path to the metadata directory.
        output_dir: Path to the output directory for images.
        state_dir: Path to the state directory.
        silent: Run silently without extra status messages.
    """
    logger.info("Explicitly triggering task synchronization...")

    try:
        sync_count, skipped_count, failed_count = sync_tasks(
            logger=logger,
            api_key=api_key,
            metadata_dir=metadata_dir,
            output_dir=output_dir,
            state_dir=state_dir,
            silent=silent
        )
        
        print(f"\nSync complete.")
        print(f"  - Successfully Synced/Downloaded: {sync_count}")
        print(f"  - Skipped (already synced or non-final state): {skipped_count}")
        print(f"  - Failed (API error, download error, etc.): {failed_count}")
        # Optionally trigger normalization after sync?
        # Or recommend running normalize command separately.

    except Exception as e:
        logger.error(f"An unexpected error occurred during sync: {e}", exc_info=True)
        print(f"错误：同步过程中发生意外错误: {e}") 