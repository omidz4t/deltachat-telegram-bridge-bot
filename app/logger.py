import logging
import sys
from pathlib import Path

def get_logger(name="deltabot-telegram-bridge", level=logging.INFO, log_file=None):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            try:
                # Ensure directory exists
                Path(log_file).parent.mkdir(exist_ok=True, parents=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"Failed to setup file logging: {e}")
                
    return logger

def setup_logging(config: dict):
    log_cfg = config.get("logging", {})
    level_str = log_cfg.get("level", "DEBUG" if config.get("debug") else "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)
    log_file = log_cfg.get("file")
    
    logger.setLevel(level)
    if log_file:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        try:
            Path(log_file).parent.mkdir(exist_ok=True, parents=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to setup file logging: {e}")

logger = get_logger()
