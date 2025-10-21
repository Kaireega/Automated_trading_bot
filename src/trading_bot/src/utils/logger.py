"""
Logging utilities for the Market Adaptive Trading Bot.
"""

import logging
import sys
import traceback
from pathlib import Path
from typing import Optional


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name
        level: Logging level (defaults to INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level if provided
    if level is not None:
        logger.setLevel(level)
    
    # Don't add handlers if root logger already has handlers (basicConfig was called)
    # This prevents duplicate output when basicConfig is used
    if not logger.handlers and not logging.getLogger().handlers:
        logger.setLevel(level or logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_dir / "trading_bot.log")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"❌ [DEBUG] Could not create log file: {e}")
            print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
    else:
        pass # No debug print for already configured logger
    
    # Ensure propagation is set correctly
    logger.propagate = True
    
    return logger


def setup_logging(level: int = logging.INFO) -> None:
    """
    Set up basic logging configuration.
    
    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/trading_bot.log')
        ]
    ) 