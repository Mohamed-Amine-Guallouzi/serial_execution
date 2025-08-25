import logging
import sys
from datetime import datetime
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_level=logging.INFO):
    """Configure logging for the application"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set root logger to lowest level
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # File handler (rotating logs)
    log_file = f"{log_dir}/gateway_ops_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
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