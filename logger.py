# logger.py
import logging
import sys
from datetime import datetime
import os
from logging.handlers import RotatingFileHandler
from config_loader import config

def setup_logging(log_level=logging.INFO):
    """Configure logging for the application"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set root logger to lowest level
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create logs directory if it doesn't exist
    log_dir = config.get('paths.log_directory', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # File handler (rotating logs)
    log_file_pattern = config.get('paths.log_file_pattern', 'gateway_ops_%Y%m%d_%H%M%S.log')
    log_file = f"{log_dir}/{datetime.now().strftime(log_file_pattern)}"
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=config.get_int('paths.max_log_size', 5242880),
        backupCount=config.get_int('paths.backup_count', 3)
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized at {log_level} level")
    logger.debug(f"Log file: {os.path.abspath(log_file)}")
    
    return logger