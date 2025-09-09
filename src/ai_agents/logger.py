"""Logging configuration for AI agents"""

import logging
import sys


def setup_logger(name: str) -> logging.Logger:
    """Setup a logger with consistent formatting"""

    logger = logging.getLogger(name)

    # Only setup if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Console handler with detailed format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Format with timestamp, logger name, level, and message
        formatter = logging.Formatter(
            "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

    return logger


# Create module-level loggers
api_logger = setup_logger("ai_agents.api_handler")
workflow_logger = setup_logger("ai_agents.workflow")
forecast_logger = setup_logger("ai_agents.forecast")
adjustment_logger = setup_logger("ai_agents.adjustment")
supplier_logger = setup_logger("ai_agents.supplier")
