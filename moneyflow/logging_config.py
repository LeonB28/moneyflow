"""
Centralized logging configuration for moneyflow.

Sets up file logging that won't be intercepted by Textual's console capture.
All errors and important events are logged to ~/.moneyflow/moneyflow.log
"""

import logging
from pathlib import Path


def setup_logging():
    """
    Configure logging to write to file.

    Logs are written to ~/.moneyflow/moneyflow.log so they're not
    swallowed by Textual's UI.

    Returns:
        Logger instance
    """
    log_dir = Path.home() / ".moneyflow"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "moneyflow.log"

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also to console for --dev mode
        ]
    )

    logger = logging.getLogger('moneyflow')
    logger.info(f"Logging initialized - writing to {log_file}")

    return logger


def get_logger(name: str = 'moneyflow'):
    """Get a logger instance."""
    return logging.getLogger(name)
