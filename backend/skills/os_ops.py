import os
from utils.logger import log
from core.known_folders import resolve_user_path

def verify_file(path: str) -> str:
    path = resolve_user_path(path)
    log.info(f"Verifying file exists: {path}")
    if os.path.exists(path):
        return f"Success: File verified at {path}"
    else:
        return f"Error: File NOT found at {path}"

def write_to_file(path: str, text: str) -> str:
    path = resolve_user_path(path)
    log.info(f"Writing text to file: {path}")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        with open(path, "r", encoding="utf-8") as f:
            verified = f.read()
        if verified != text:
            return f"Error: Wrote '{path}', but content verification failed."
        return f"Success: Wrote and verified {len(text)} characters at {path}"
    except Exception as e:
        return f"Error writing to file: {e}"
