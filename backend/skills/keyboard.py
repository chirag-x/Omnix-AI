import pyautogui
from utils.logger import log
from core.task_control import wait as cancellable_wait, check_cancelled

pyautogui.FAILSAFE = False

def press_key(key: str) -> str:
    check_cancelled()
    log.info(f"Pressing key: {key}")
    if '+' in key:
        keys = key.split('+')
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(key)
    return f"Pressed {key}"

import pyperclip
import time

def type_text(text: str) -> str:
    log.info(f"Typing text (via clipboard): {text}")
    # Backup original clipboard
    original_clipboard = pyperclip.paste()
    
    # Inject new text
    try:
        check_cancelled()
        pyperclip.copy(text)
        cancellable_wait(0.1)
        pyautogui.hotkey('ctrl', 'v')
        cancellable_wait(0.1)
    finally:
        pyperclip.copy(original_clipboard)
    
    return f"Typed: {text}"

def clear_and_type(x: int, y: int, text: str) -> str:
    log.info(f"Clearing and typing at ({x}, {y}): {text}")
    
    # Triple click to select all text in the field
    check_cancelled()
    pyautogui.click(x, y, clicks=3, interval=0.1)
    cancellable_wait(0.2)
    pyautogui.press('backspace')
    cancellable_wait(0.1)
    
    # Backup and inject via clipboard
    original_clipboard = pyperclip.paste()
    try:
        check_cancelled()
        pyperclip.copy(text)
        cancellable_wait(0.1)
        pyautogui.hotkey('ctrl', 'v')
        cancellable_wait(0.1)
    finally:
        pyperclip.copy(original_clipboard)
    
    return f"Cleared field and typed: {text}"

def wait(seconds: float) -> str:
    log.info(f"Waiting {seconds} seconds...")
    cancellable_wait(seconds)
    return f"Waited {seconds} seconds."
