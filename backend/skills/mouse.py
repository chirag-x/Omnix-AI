"""
Phase 3 — The Hands: Upgraded mouse skills using pywinauto UIAutomation.
Provides coordinate-free clicking by element name + window focus control.
"""
import time
import pyautogui
import pygetwindow as gw
from pywinauto import Desktop
from utils.logger import log

pyautogui.FAILSAFE = False


def click(x: int, y: int) -> str:
    """Click at absolute screen coordinates. Fast path for when coordinates are known."""
    log.info(f"Clicking at ({x}, {y})")
    pyautogui.click(x=int(x), y=int(y))
    return f"Clicked at ({x}, {y})"


def scroll(clicks: int) -> str:
    """Scroll the mouse wheel by a number of clicks (negative = down, positive = up)."""
    log.info(f"Scrolling by {clicks} clicks")
    pyautogui.scroll(int(clicks))
    return f"Scrolled by {clicks} units"


def click_element(name: str, timeout: float = 5.0) -> str:
    """
    Find a UI element by its accessible name anywhere in the active window
    and click it — no coordinates needed.

    Args:
        name: The text/label/name of the button, link, or control to click.
              Case-insensitive partial match is attempted.
        timeout: How many seconds to wait for the element to appear.

    Returns:
        Success or failure message for the LLM.
    """
    log.info(f"Searching for UI element: '{name}'")
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            win = gw.getActiveWindow()
            if not win:
                return "Error: No active window found."

            app = Desktop(backend="uia").window(handle=win._hWnd)

            # Search across all common interactive control types
            for control_type in ["Button", "MenuItem", "ListItem", "Hyperlink", "CheckBox", "RadioButton", "Edit"]:
                try:
                    controls = app.descendants(control_type=control_type)
                    for ctrl in controls:
                        ctrl_name = (ctrl.element_info.name or "").strip()
                        if name.lower() in ctrl_name.lower() and ctrl_name:
                            rect = ctrl.rectangle()
                            cx = (rect.left + rect.right) // 2
                            cy = (rect.top + rect.bottom) // 2
                            # Ensure element is on screen
                            if rect.width() > 0 and rect.height() > 0:
                                log.info(f"Found '{ctrl_name}' at ({cx}, {cy}). Clicking.")
                                ctrl.click_input()
                                return f"Clicked element '{ctrl_name}' at ({cx}, {cy})."
                except Exception:
                    continue

        except Exception as e:
            log.warning(f"click_element search error: {e}")

        time.sleep(0.3)

    return (
        f"Error: Could not find a UI element named '{name}' in the active window "
        f"after {timeout:.0f}s. Use observe() to see what's actually on screen, "
        f"then try click(x, y) with the exact coordinates instead."
    )


def find_window(app_name: str) -> str:
    """
    Bring a window to the foreground by its title/app name.
    Useful when an app is already open but in the background.

    Args:
        app_name: Partial name of the window title (case-insensitive).

    Returns:
        Success or failure message for the LLM.
    """
    log.info(f"Searching for window: '{app_name}'")
    try:
        windows = gw.getWindowsWithTitle(app_name)
        if not windows:
            # Try partial match
            all_windows = gw.getAllTitles()
            matched = [t for t in all_windows if app_name.lower() in t.lower() and t.strip()]
            if matched:
                windows = gw.getWindowsWithTitle(matched[0])

        if windows:
            win = windows[0]
            win.restore()
            win.activate()
            time.sleep(0.4)
            log.info(f"Activated window: '{win.title}'")
            return f"Window '{win.title}' brought to foreground."
        else:
            return f"No open window found matching '{app_name}'. The app may not be running — try opening it first."

    except Exception as e:
        log.error(f"find_window error: {e}")
        return f"Error focusing window '{app_name}': {e}"
