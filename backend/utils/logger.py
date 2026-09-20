import logging
import sys
import os
from core.settings import SettingsManager

def setup_logger(name="Omnix"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(levelname)s] %(module)s: %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler (always write, UI can open it)
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "omnix.log")
        
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s: %(message)s')
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)
        
    return logger

log = setup_logger()
