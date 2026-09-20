import os
from utils.logger import log

def verify_file(path: str) -> str:
    log.info(f"Verifying file exists: {path}")
    if os.path.exists(path):
        return f"Success: File verified at {path}"
    else:
        return f"Error: File NOT found at {path}"

def write_to_file(path: str, text: str) -> str:
    log.info(f"Writing text to file: {path}")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return f"Success: Wrote to {path}"
    except Exception as e:
        return f"Error writing to file: {e}"
