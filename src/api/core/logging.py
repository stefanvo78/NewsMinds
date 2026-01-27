"""
Structured logging configuration with Azure Monitor integration.

This module sets up logging that:
- Outputs structured logs to stdout (for container environments)
- Integrates with Azure Monitor when APPLICATIONINSIGHTS_CONNECTION_STRING is set
- Reduces noise from third-party libraries
"""

import logging
import sys

from src.api.core.config import settings


def setup_logging() -> logging.Logger:
    """
    Configure structured logging for the application.

    Returns:
        Configured logger instance for the application.
    """
    # Set log level based on environment
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Configure root logger with structured format
    # Format: timestamp | level | logger_name | message
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Override any existing configuration
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Create application logger
    logger = logging.getLogger("newsminds")
    logger.setLevel(log_level)

    return logger


# Initialize logger on module import
logger = setup_logging()
