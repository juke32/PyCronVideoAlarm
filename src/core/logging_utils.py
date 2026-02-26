import logging
import os
from datetime import datetime
from pathlib import Path


def get_log_file_path():
    """Get the current log file path based on today's date."""
    from .config import get_config
    
    config = get_config()
    log_dir_name = config.get("logging", "log_directory") or "logs"
    log_format = config.get("logging", "log_file_format") or "video_alarm_{date}.log"
    
    # Format the filename with today's date
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = log_format.replace("{date}", date_str)
    
    from .config import get_app_data_dir
    # Ensure log directory exists
    log_dir = os.path.join(get_app_data_dir(), log_dir_name)
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    return os.path.join(log_dir, filename)


def setup_file_logging():
    """Enable file logging by adding a FileHandler to the root logger."""
    try:
        log_file = get_log_file_path()
        
        # Check if file handler already exists
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                if handler.baseFilename == os.path.abspath(log_file):
                    logging.info("File logging already enabled")
                    return True
        
        # Create and add file handler
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Use the same format as console logging
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        root_logger.addHandler(file_handler)
        logging.info(f"File logging enabled: {log_file}")
        return True
    except Exception as e:
        logging.error(f"Failed to setup file logging: {e}")
        return False


def remove_file_logging():
    """Disable file logging by removing FileHandler from the root logger."""
    try:
        root_logger = logging.getLogger()
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
        
        for handler in file_handlers:
            handler.close()
            root_logger.removeHandler(handler)
            logging.info("File logging disabled")
        
        return True
    except Exception as e:
        logging.error(f"Failed to remove file logging: {e}")
        return False


def is_file_logging_enabled():
    """Check if file logging is currently active."""
    root_logger = logging.getLogger()
    return any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
