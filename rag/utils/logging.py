
import logging
import sys
from rag.config.settings import settings

def setup_rag_logger(name: str) -> logging.Logger:
    """
    Configures a logger with the project standard format.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times if this is called repeatedly
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Format: [TIME] [LEVEL] [MODULE] - Message
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Set level from settings (e.g., "INFO", "DEBUG")
        level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logger.setLevel(level)
        
    return logger