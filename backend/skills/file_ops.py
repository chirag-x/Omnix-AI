"""
Phase 8 — Full File Operations
Gives Omnix the ability to copy, move, rename, delete, create folders,
inspect file metadata, and download files from the internet.
All operations expand ~ to the actual user home directory.
"""
import os
import shutil
import stat
from utils.logger import log


def _expand(path: str) -> str:
    return os.path.expanduser(path.replace("\\", "/"))


# ──────────────────────────────────────────────────────────────────────────────
# COPY / MOVE / DELETE / CREATE
# ──────────────────────────────────────────────────────────────────────────────

def copy_file(source: str, destination: str) -> str:
    """
    Copy a file or folder to a new location.
    If destination is a folder, the file is placed inside it.
    If destination is a full path, the file is copied and renamed.

    Args:
        source: Full path of the file or folder to copy.
        destination: Target path or folder to copy into.

    Returns:
        Success message or error.
    """
    src = _expand(source)
    dst = _expand(destination)
    log.info(f"Copying '{src}' → '{dst}'")
    try:
        if not os.path.exists(src):
            return f"Error: Source not found: {src}"

        if os.path.isdir(src):
            # If dst already exists as a dir, copy inside it
            if os.path.isdir(dst):
                dst = os.path.join(dst, os.path.basename(src))
            shutil.copytree(src, dst)
        else:
            # If destination is a directory, copy the file inside it
            if os.path.isdir(dst):
                dst = os.path.join(dst, os.path.basename(src))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

        return f"Copied '{os.path.basename(src)}' to '{dst}'"
    except Exception as e:
        log.error(f"copy_file error: {e}")
        return f"Error copying file: {e}"


def move_file(source: str, destination: str) -> str:
    """
    Move or rename a file or folder.
    Can be used to rename files: move_file("old_name.txt", "new_name.txt")
    Or to move to another folder: move_file("file.txt", "~/Documents/")

    Args:
        source: Full path of the file or folder to move.
        destination: Target path or destination folder.

    Returns:
        Success message or error.
    """
    src = _expand(source)
    dst = _expand(destination)
    log.info(f"Moving '{src}' → '{dst}'")
    try:
        if not os.path.exists(src):
            return f"Error: Source not found: {src}"
        os.makedirs(os.path.dirname(dst) if not os.path.isdir(dst) else dst, exist_ok=True)
        shutil.move(src, dst)
        return f"Moved '{os.path.basename(src)}' to '{dst}'"
    except Exception as e:
        log.error(f"move_file error: {e}")
        return f"Error moving file: {e}"


def delete_file(path: str) -> str:
    """
    Permanently delete a file or empty folder.
    SAFETY: This cannot delete an entire drive root or the Windows system folder.
    Always confirm with the user before calling this for important files.

    Args:
        path: Full path of the file or folder to delete.

    Returns:
        Success message or error.
    """
    target = _expand(path)
    log.warning(f"Deleting: '{target}'")

    # Safety guard: block obviously dangerous paths
    blocked = ["C:\\Windows", "C:\\Program Files", "C:/Windows", os.path.expanduser("~") + "\\AppData"]
    for b in blocked:
        if target.lower().startswith(b.lower()):
            return f"Error: Refusing to delete system path: {target}"

    try:
        if not os.path.exists(target):
            return f"Error: Path not found: {target}"

        if os.path.isdir(target):
            # Only delete empty directories safely
            if os.listdir(target):
                return (f"Error: '{target}' is not empty. Use run_terminal_command('rmdir /s /q \"{target}\"') "
                        f"to delete a folder with contents, but ONLY after user confirmation.")
            os.rmdir(target)
        else:
            # Handle read-only files
            if not os.access(target, os.W_OK):
                os.chmod(target, stat.S_IWRITE)
            os.remove(target)

        return f"Deleted '{target}' successfully."
    except Exception as e:
        log.error(f"delete_file error: {e}")
        return f"Error deleting '{target}': {e}"


def create_folder(path: str) -> str:
    """
    Create a new folder (and any required parent folders).

    Args:
        path: Full path of the folder to create. Supports ~ for home directory.

    Returns:
        Success or error message.
    """
    target = _expand(path)
    log.info(f"Creating folder: '{target}'")
    try:
        if os.path.exists(target):
            return f"Folder already exists: {target}"
        os.makedirs(target, exist_ok=True)
        return f"Created folder: '{target}'"
    except Exception as e:
        log.error(f"create_folder error: {e}")
        return f"Error creating folder: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# FILE METADATA
# ──────────────────────────────────────────────────────────────────────────────

def get_file_info(path: str) -> str:
    """
    Get detailed metadata about a file or folder: size, dates, type, permissions.
    Useful for answering questions like "how big is this file?" or "when was it modified?"

    Args:
        path: Full path to the file or folder.

    Returns:
        A human-readable summary of the file's metadata.
    """
    target = _expand(path)
    log.info(f"Getting file info: '{target}'")
    try:
        if not os.path.exists(target):
            return f"Error: Path not found: {target}"

        import datetime
        stat_result = os.stat(target)
        size_bytes = stat_result.st_size
        modified = datetime.datetime.fromtimestamp(stat_result.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        created = datetime.datetime.fromtimestamp(stat_result.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        is_dir = os.path.isdir(target)

        # Format size
        if size_bytes < 1024:
            size_str = f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 ** 3:
            size_str = f"{size_bytes / (1024**2):.2f} MB"
        else:
            size_str = f"{size_bytes / (1024**3):.2f} GB"

        result = [
            f"Name: {os.path.basename(target)}",
            f"Type: {'Folder' if is_dir else 'File'}",
            f"Path: {target}",
            f"Size: {size_str}",
            f"Modified: {modified}",
            f"Created: {created}",
        ]

        if is_dir:
            try:
                items = os.listdir(target)
                result.append(f"Contents: {len(items)} item(s)")
            except Exception:
                pass

        return "\n".join(result)
    except Exception as e:
        log.error(f"get_file_info error: {e}")
        return f"Error getting file info: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# DOWNLOAD
# ──────────────────────────────────────────────────────────────────────────────

def download_file(url: str, destination: str) -> str:
    """
    Download a file from a URL directly to disk.
    Use this when the user wants to download something from the internet
    without opening a browser.

    Args:
        url: The full URL of the file to download.
        destination: The local path to save the file to (e.g., "~/Downloads/file.pdf").
                     If a folder is given, the filename is inferred from the URL.

    Returns:
        Success message with the saved path, or an error.
    """
    dst = _expand(destination)
    log.info(f"Downloading '{url}' → '{dst}'")
    try:
        import requests
        import urllib.parse

        # If destination is a folder, infer the filename from the URL
        if os.path.isdir(dst) or not os.path.splitext(dst)[1]:
            filename = os.path.basename(urllib.parse.urlparse(url).path) or "downloaded_file"
            dst = os.path.join(dst if os.path.isdir(dst) else os.path.expanduser("~/Downloads"), filename)

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(dst, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        size_mb = downloaded / (1024 * 1024)
        return f"Downloaded {size_mb:.2f} MB to: '{dst}'"

    except Exception as e:
        log.error(f"download_file error: {e}")
        return f"Error downloading file: {e}"
