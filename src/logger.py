"""
Centralized logging configuration for the Mises Data Curator.

This module provides a consistent logging interface across all components
(CLI, Web, Ingestion, etc.) with proper formatting and configurable handlers.

Usage:
    from src.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Starting data ingestion...")
    logger.error("Failed to fetch data", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get or create a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Optional log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        # Set level
        log_level = level or logging.INFO
        if isinstance(log_level, str):
            log_level = getattr(logging, log_level.upper())
        logger.setLevel(log_level)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
        
        # Prevent propagation to root logger (avoid duplicate logs)
        logger.propagate = False
    
    return logger


def configure_file_logging(log_dir: Path, app_name: str = "data_curator") -> None:
    """
    Add file logging to all loggers.
    
    Args:
        log_dir: Directory to store log files
        app_name: Application name for log file naming
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{app_name}.log"
    
    # Create file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(name)s.%(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add to root logger (affects all loggers)
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)


# Convenience function for quick setup
def setup_logging(level: str = "INFO", enable_file: bool = False, log_dir: Optional[Path] = None) -> None:
    """
    Quick setup for application-wide logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file: Whether to enable file logging
        log_dir: Directory for log files (required if enable_file=True)
    """
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    if enable_file:
        if not log_dir:
            log_dir = Path.cwd() / "logs"
        configure_file_logging(log_dir)
