"""
Phase 8 — Clipboard Engine
Gives Omnix the ability to read AND write the Windows clipboard.
This allows it to grab text you've copied, process it, and paste results.
"""
import pyperclip
from utils.logger import log


def get_clipboard() -> str:
    """
    Read the current text content of the Windows clipboard and return it.
    Use this when the user says 'summarize what I copied', 'translate my clipboard',
    'fix the spelling of what I copied', or any similar clipboard-based task.

    Returns:
        The text currently in the clipboard, or an error if empty/non-text.
    """
    log.info("Reading clipboard content")
    try:
        text = pyperclip.paste()
        if not text or not text.strip():
            return "Clipboard is empty or contains no readable text."
        log.info(f"Clipboard content ({len(text)} chars): {text[:100]}...")
        return f"Clipboard content:\n{text}"
    except Exception as e:
        log.error(f"get_clipboard error: {e}")
        return f"Error reading clipboard: {e}"


def set_clipboard(text: str) -> str:
    """
    Write text to the Windows clipboard so the user can paste it anywhere.
    Use this when you want to prepare text for the user to paste, e.g.
    'put this translation in my clipboard', 'copy this code to my clipboard'.

    Args:
        text: The text to place in the clipboard.

    Returns:
        Success or error message.
    """
    log.info(f"Writing to clipboard: {text[:80]}...")
    try:
        pyperclip.copy(text)
        return f"Copied to clipboard: '{text[:60]}{'...' if len(text) > 60 else ''}'"
    except Exception as e:
        log.error(f"set_clipboard error: {e}")
        return f"Error writing to clipboard: {e}"
