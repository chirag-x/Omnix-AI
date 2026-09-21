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


def right_click(x: int, y: int) -> str:
    """
    Right-click at absolute screen coordinates.
    Use this to open context menus (e.g., right-click a WhatsApp message bubble
    to get Delete, Reply, etc.). More stable than left-click hovering.
    """
    log.info(f"Right-clicking at ({x}, {y})")
    pyautogui.rightClick(x=int(x), y=int(y))
    return f"Right-clicked at ({x}, {y})"


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
            exact_match = None
            partial_match = None
            
            for control_type in ["Button", "MenuItem", "ListItem", "Hyperlink", "CheckBox", "RadioButton", "Edit"]:
                try:
                    controls = app.descendants(control_type=control_type)
                    for ctrl in controls:
                        ctrl_name = (ctrl.element_info.name or "").strip()
                        if not ctrl_name:
                            continue
                            
                        # Ensure element has valid coordinates
                        rect = ctrl.rectangle()
                        if rect.width() <= 0 or rect.height() <= 0:
                            continue
                            
                        # Check exact match first
                        if name.lower() == ctrl_name.lower():
                            exact_match = (ctrl, ctrl_name, rect)
                            break
                        # Check partial match as fallback
                        elif name.lower() in ctrl_name.lower():
                            if partial_match is None:
                                partial_match = (ctrl, ctrl_name, rect)
                                
                    if exact_match:
                        break
                except Exception:
                    continue
                    
            target = exact_match or partial_match
            if target:
                ctrl, ctrl_name, rect = target
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                log.info(f"Found '{ctrl_name}' at ({cx}, {cy}) [Exact: {exact_match is not None}]. Clicking.")
                ctrl.click_input()
                return f"Clicked element '{ctrl_name}' at ({cx}, {cy})."

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


def click_text(text: str, timeout: float = 5.0) -> str:
    """
    Find exact text visually on the active window using OCR and click it.
    Attempts to use EasyOCR for hyper-accuracy, falls back to Tesseract.
    """
    import os
    from PIL import ImageGrab
    import numpy as np
    
    log.info(f"Searching visually (OCR) for text: '{text}'")
    deadline = time.time() + timeout
    text_lower = text.lower()

    while time.time() < deadline:
        win = gw.getActiveWindow()
        if not win:
            return "Error: No active window found for OCR."
        
        bbox = (win.left, win.top, win.right, win.bottom)
        img = ImageGrab.grab(bbox)
        
    # Initialize EasyOCR once per function call, outside the loop
    reader = None
    use_gpu = False
    try:
        import easyocr
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="torch")
        from core.settings import SettingsManager
        v_device = SettingsManager.get("vision_device", "auto")
        if v_device == "cuda":
            use_gpu = True
        elif v_device == "auto":
            import torch
            use_gpu = torch.cuda.is_available()
        reader = easyocr.Reader(['en'], gpu=use_gpu, verbose=False)
    except Exception as e:
        log.warning(f"EasyOCR init failed: {e}")

    while time.time() < deadline:
        win = gw.getActiveWindow()
        if not win:
            return "Error: No active window found for OCR."
        
        bbox = (win.left, win.top, win.right, win.bottom)
        img = ImageGrab.grab(bbox)
        
        try:
            if reader:
                img_np = np.array(img)
                results = reader.readtext(img_np)
                
                # First pass: try exact or substring match
                for (bbox_cords, word, prob) in results:
                    word_lower = word.lower()
                    # Check if target is in detected word, OR if a significant chunk of target matches detected word
                    if text_lower in word_lower or (len(text_lower) >= 4 and text_lower[:4] in word_lower and text_lower[-4:] in word_lower):
                        x_center = int((bbox_cords[0][0] + bbox_cords[1][0]) / 2)
                        y_center = int((bbox_cords[0][1] + bbox_cords[2][1]) / 2)
                        
                        x = win.left + x_center
                        y = win.top + y_center
                        
                        log.info(f"[EasyOCR] Found '{word}' at ({x}, {y}). Clicking.")
                        pyautogui.click(x=x, y=y)
                        return f"Clicked visual text '{word}' at ({x}, {y})."
                        
                # Second pass: What if EasyOCR split "Gopal ji yadav" into "Gopal", "ji", "yadav"?
                # Check for partial matches that are very close
                parts = text_lower.split()
                if len(parts) > 1:
                    for (bbox_cords, word, prob) in results:
                        word_lower = word.lower()
                        # If the longest word in the target is in the detected text, click it.
                        longest_part = max(parts, key=len)
                        if len(longest_part) > 4 and longest_part in word_lower:
                            x_center = int((bbox_cords[0][0] + bbox_cords[1][0]) / 2)
                            y_center = int((bbox_cords[0][1] + bbox_cords[2][1]) / 2)
                            
                            x = win.left + x_center
                            y = win.top + y_center
                            
                            log.info(f"[EasyOCR] Found partial match '{word}' for '{text}'. Clicking.")
                            pyautogui.click(x=x, y=y)
                            return f"Clicked visual text '{word}' at ({x}, {y})."

            else:
                # FALLBACK TO TESSERACT
                try:
                    import pytesseract
                    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    if os.path.exists(tesseract_path):
                        pytesseract.pytesseract.tesseract_cmd = tesseract_path

                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    for i in range(len(data['text'])):
                        word = data['text'][i].strip().lower()
                        if text_lower in word and len(word) > 2:
                            x = win.left + data['left'][i] + (data['width'][i] // 2)
                            y = win.top + data['top'][i] + (data['height'][i] // 2)
                            log.info(f"[Tesseract] Found '{word}' at ({x}, {y}). Clicking.")
                            pyautogui.click(x=x, y=y)
                            return f"Clicked visual text '{word}' at ({x}, {y})."
                except Exception as te:
                    log.warning(f"Tesseract fallback error: {te}")
                    
        except Exception as e:
            log.warning(f"click_text OCR error: {e}")
            
        time.sleep(0.5)
        
    return f"Error: Could not find the text '{text}' visually on the screen after {timeout:.0f}s."


def click_visual(description: str) -> str:
    """
    Find and click any UI element, icon, or text using Cloud LLM Vision (e.g. Gemini).
    This bypasses local OCR and sends a screenshot to the LLM to get exact coordinates.
    Use this when local click_text fails, or when clicking non-text icons (e.g., "gear icon").
    """
    import base64
    import io
    import time
    from PIL import ImageGrab
    from brain.llm_provider import get_active_model, _make_gemini_request
    from core.settings import SettingsManager
    
    log.info(f"Visual Click Request: '{description}'")
    
    # 1. Check if Cloud Vision is enabled in settings
    vision_mode = SettingsManager.get("vision_engine_type", "Cloud (LLM Vision)")
    if "Local" in vision_mode:
        log.info("Cloud vision is disabled, falling back to click_text")
        return click_text(description)
        
    win = gw.getActiveWindow()
    if not win:
        return "Error: No active window to look at."
        
    # 2. Take screenshot of active window
    bbox = (win.left, win.top, win.right, win.bottom)
    img = ImageGrab.grab(bbox)
    width, height = img.size
    
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # 3. Ask Gemini for coordinates
    prompt = (
        f"You are a robotic vision system. Locate the following UI element on the screen: '{description}'.\n"
        f"The image size is {width}x{height} pixels.\n"
        "Reply ONLY with the exact X and Y coordinates of the center of that element in this exact format: X,Y\n"
        "If you absolutely cannot find it, reply with: NOT_FOUND"
    )
    
    try:
        from brain.llm_provider import FAST_MODEL, ACTIVE_URL, ACTIVE_KEY
        
        # We can construct the OpenAI compat payload for Gemini
        payload = {
            "model": FAST_MODEL or "gemini-3.5-flash",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }
            ],
            "max_tokens": 15,
            "temperature": 0.0
        }
        
        import requests
        headers = {"Authorization": f"Bearer {ACTIVE_KEY}", "Content-Type": "application/json"}
        # Ensure we have the base chat completion endpoint if ACTIVE_URL doesn't end in chat/completions
        base = ACTIVE_URL.rstrip('/') if ACTIVE_URL else "https://generativelanguage.googleapis.com/v1beta/openai"
        url = f"{base}/chat/completions"
        
        log.info(f"Querying Cloud Vision ({FAST_MODEL}) for coordinates...")
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        
        result_text = resp.json()["choices"][0]["message"]["content"].strip()
        log.info(f"Cloud Vision responded: {result_text}")
        
        if "NOT_FOUND" in result_text or "," not in result_text:
            return f"Error: Cloud Vision could not locate '{description}'."
            
        parts = result_text.replace(" ", "").split(",")
        local_x = int(float(parts[0]))
        local_y = int(float(parts[1]))
        
        abs_x = win.left + local_x
        abs_y = win.top + local_y
        
        pyautogui.click(x=abs_x, y=abs_y)
        return f"Cloud Vision clicked '{description}' at ({abs_x}, {abs_y})"
        
    except Exception as e:
        log.error(f"Cloud Vision error: {e}")
        return f"Error using Cloud Vision: {e}. Try click_text instead."
