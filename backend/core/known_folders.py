"""Resolve Windows known folders without assuming they use the C drive."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import re
import uuid


_KNOWN_FOLDER_IDS = {
    "desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "downloads": "374DE290-123F-4565-9164-39C4925E467B",
    "music": "4BD8D571-6D19-48D3-BE97-422220080E43",
    "pictures": "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "videos": "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
}


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_string(cls, value: str):
        raw = uuid.UUID(value).bytes_le
        return cls.from_buffer_copy(raw)


def get_known_folder_path(name: str) -> str:
    """Return the OS-configured absolute path for a supported Windows folder."""
    key = str(name).strip().lower().replace(" ", "")
    aliases = {"document": "documents", "download": "downloads", "picture": "pictures", "video": "videos"}
    key = aliases.get(key, key)
    folder_id = _KNOWN_FOLDER_IDS.get(key)
    if not folder_id:
        supported = ", ".join(sorted(_KNOWN_FOLDER_IDS))
        raise ValueError(f"Unknown folder '{name}'. Supported folders: {supported}")

    path_ptr = ctypes.c_wchar_p()
    guid = _GUID.from_string(folder_id)
    result = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(guid), 0, None, ctypes.byref(path_ptr)
    )
    if result != 0:
        raise OSError(result, f"Windows could not resolve the {key} folder")
    try:
        return os.path.normpath(path_ptr.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)


def resolve_user_path(path: str) -> str:
    """Expand variables and map ~/KnownFolder to its real redirected location."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Path must be a non-empty string")

    raw = os.path.expandvars(path.strip())
    normalized = raw.replace("\\", "/")
    match = re.match(
        r"^(?:~/?|)(desktop|documents?|downloads?|music|pictures?|videos?)(?:/(.*))?$",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        base = get_known_folder_path(match.group(1))
        remainder = match.group(2)
        return os.path.normpath(os.path.join(base, remainder)) if remainder else base

    return os.path.normpath(os.path.expanduser(raw))


def resolve_known_folder(name: str) -> str:
    """Skill wrapper: reveal the real configured location of a user folder."""
    try:
        path = get_known_folder_path(name)
        exists = Path(path).is_dir()
        return f"Known folder '{name}' resolves to: {path} (exists={exists})"
    except Exception as exc:
        return f"Error resolving known folder '{name}': {exc}"
