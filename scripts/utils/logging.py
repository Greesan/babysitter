"""Logging utilities for consistent logging across scripts."""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(script_name):
    """Configure logging with both file and console handlers."""
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)

    # Console handler (stderr) - INFO and above
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_formatter)

    # File handler (rotating logs) - DEBUG and above
    # Get ticket dir at runtime to allow tests to override
    ticket_dir = os.environ.get("CLAUDE_TICKET_DIR", "./tickets")
    log_dir = os.path.join(ticket_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f"{script_name}.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
