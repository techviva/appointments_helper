import logging
import os


def get_logger() -> logging.Logger:
# 1. Get a logger instance
    

    logger = logging.getLogger("route_orchestrator")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on re-import (tests, notebooks, restarts)
    if not logger.handlers:
    # Console handler
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        sh.setFormatter(fmt)
        logger.addHandler(sh)

        # File handler (logs will be saved to logs/app.log)
        os.makedirs("logs", exist_ok=True)
        fh = logging.FileHandler("logs/app.log")
        fh.setLevel(logging.INFO)
        fh.setFormatter(fmt)
        logger.addHandler(fh)


    return logger

logger = get_logger()