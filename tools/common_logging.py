from __future__ import annotations

import logging
import os
from typing import Optional


def setup_logging(name: str = "ESP32OS", level: Optional[str] = None) -> logging.Logger:
    """
    Initialize a shared logger with consistent formatting.
    Level can be overridden via LOG_LEVEL env (defaults to INFO).
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format='[%(levelname)s] %(message)s')
    return logging.getLogger(name)
