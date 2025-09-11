"""Logging configuration for AI agents"""

import sys

from loguru import logger


def configure_logging():
    """Configure loguru with consistent formatting"""

    # Remove default handler
    logger.remove()

    # Add custom handler with consistent formatting
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )


# Configure loguru on import
configure_logging()

# Create module-level loggers with proper context
api_logger = logger.bind(name="api_handler")
workflow_logger = logger.bind(name="workflow")
forecast_logger = logger.bind(name="forecast")
adjustment_logger = logger.bind(name="adjustment")
supplier_logger = logger.bind(name="supplier")
