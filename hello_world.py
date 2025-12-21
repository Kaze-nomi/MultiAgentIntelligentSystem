#!/usr/bin/env python3
"""
Simple Hello World application.

This module provides a basic demonstration of Python functionality
by printing a greeting message to the console.

Author: Assistant
Version: 1.0.0
"""

import sys
import logging
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_greeting(name: Optional[str] = None) -> str:
    """
    Generate a greeting message.

    Args:
        name: Optional name to greet. If None, greets "World".

    Returns:
        str: The greeting message
    """
    target = name if name else "World"
    return f"Hello, {target}!"


def main() -> int:
    """
    Main entry point for the application.

    Returns:
        int: Exit code (0 for success)
    """
    try:
        setup_logging()
        logger = logging.getLogger(__name__)

        # Get greeting message
        message = get_greeting()

        # Print the message
        print(message)
        logger.info("Greeting message printed successfully")

        return 0

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
