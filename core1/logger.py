# filename: logger.py

import datetime
import os

LOG_FILE = "bot_log.txt"

# Ensure log file exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        f.write(f"{datetime.datetime.now()} | INFO | Logger initialized\n")


def _write_log(level: str, message: str):
    """Internal helper to write log with timestamp and level."""
    timestamp = datetime.datetime.now()
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} | {level} | {message}\n")


# =====================
# Public log functions
# =====================
def info(message: str):
    _write_log("INFO", message)


def warning(message: str):
    _write_log("WARNING", message)


def error(message: str):
    _write_log("ERROR", message)


def debug(message: str):
    _write_log("DEBUG", message)


# =====================
# Generic log function
# =====================
def log(message: str):
    """Fallback generic logger (equivalent to info)."""
    info(message)