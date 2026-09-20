import pyautogui
from utils.logger import log

pyautogui.FAILSAFE = False

def press_key(key: str) -> str:
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
    pyperclip.copy(text)
    time.sleep(0.1) # Small delay to ensure clipboard is updated
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.1)
    
    # Restore clipboard
    pyperclip.copy(original_clipboard)
    
    return f"Typed: {text}"

def clear_and_type(x: int, y: int, text: str) -> str:
    log.info(f"Clearing and typing at ({x}, {y}): {text}")
    
    # Triple click to select all text in the field
    pyautogui.click(x, y, clicks=3, interval=0.1)
    time.sleep(0.2)
    pyautogui.press('backspace')
    time.sleep(0.1)
    
    # Backup and inject via clipboard
    original_clipboard = pyperclip.paste()
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.1)
    pyperclip.copy(original_clipboard)
    
    return f"Cleared field and typed: {text}"
