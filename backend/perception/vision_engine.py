import pygetwindow as gw
import time
import base64
import io
import pyautogui
from PIL import Image, ImageGrab, ImageChops
from pywinauto import Desktop
from perception.uia_parser import get_uia_elements
from perception.ocr_parser import get_ocr_elements
from utils.logger import log

def capture_screen_b64() -> str:
    # Keep the model's image aligned with the window described by observe().
    # pyautogui.screenshot() only captures the primary display on many Windows
    # systems, which made secondary-monitor interactions visually misleading.
    win = gw.getActiveWindow()
    if win and win.width > 0 and win.height > 0:
        img = ImageGrab.grab(
            (win.left, win.top, win.right, win.bottom), all_screens=True,
        )
    else:
        img = ImageGrab.grab(all_screens=True)

    # Preserve more text detail than the old 1280x720 JPEG while bounding cost.
    img.thumbnail((1600, 1000), Image.Resampling.LANCZOS)
    
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=84)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def wait_for_screen_stabilization(bbox=None, max_wait=1.5):
    log.info("Pausing 1.5s for screen to stabilize...")
    time.sleep(max_wait)
    log.info("Screen stabilized.")

def observe() -> str:
    log.info("Running vision engine...")
    try:
        # List all meaningful open windows so LLM can use find_window
        all_titles = [t for t in gw.getAllTitles() if t.strip() and len(t.strip()) > 1]
        windows_summary = "Open Windows: " + ", ".join(f"'{t}'" for t in all_titles[:15])

        win = gw.getActiveWindow()
        if not win:
            return windows_summary + "\nNo active window found. You are on the desktop."

        bbox = (win.left, win.top, win.right, win.bottom)
        wait_for_screen_stabilization(bbox)

        context = (
            windows_summary + "\n"
            f"Active Window: '{win.title}' (Position: {win.left},{win.top}, Size: {win.width}x{win.height})\n"
        )
        center_x = win.left + (win.width // 2)

        elements = get_uia_elements(win, center_x)
        elements.extend(get_ocr_elements(win, center_x))

        if not elements:
            context += "[No interactable elements found.]"
        else:
            context += "Visible Clickable Elements on Screen:\n"
            context += "\n".join(elements)

        return context
    except Exception as e:
        log.error(f"Vision Engine Fatal Error: {e}")
        return f"Fatal Error reading screen: {str(e)}"
