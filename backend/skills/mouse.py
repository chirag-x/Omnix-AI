import pyautogui
from utils.logger import log

pyautogui.FAILSAFE = False

def click(x: int, y: int) -> str:
    log.info(f"Clicking at ({x}, {y})")
    pyautogui.click(x=int(x), y=int(y))
    return f"Clicked at ({x}, {y})"

def scroll(clicks: int) -> str:
    log.info(f"Scrolling by {clicks} clicks")
    pyautogui.scroll(int(clicks))
    return f"Scrolled by {clicks} units"
