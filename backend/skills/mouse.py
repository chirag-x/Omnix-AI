"""
Phase 3 — The Hands: Upgraded mouse skills using pywinauto UIAutomation.
Provides coordinate-free clicking by element name + window focus control.
"""
import time
import re
import threading
import json
import pyautogui
import pygetwindow as gw
from pywinauto import Desktop
from utils.logger import log
from core.task_control import check_cancelled, TaskCancelled
from perception.text_targeting import (
    TextCandidate,
    build_ocr_candidates,
    build_tesseract_candidates,
    normalize_text,
    select_text_candidate,
)

pyautogui.FAILSAFE = False

_ocr_readers = {}
_ocr_lock = threading.Lock()


def _get_ocr_reader():
    """Reuse the expensive OCR model, respecting the selected compute device."""
    from core.settings import SettingsManager
    device = SettingsManager.get("vision_device", "auto")
    with _ocr_lock:
        if device not in _ocr_readers:
            import easyocr
            gpu = device == "cuda"
            if device == "auto":
                import torch
                gpu = torch.cuda.is_available()
            _ocr_readers[device] = easyocr.Reader(['en'], gpu=gpu, verbose=False)
        return _ocr_readers[device]


def _window_snapshot(win):
    return (win._hWnd, win.left, win.top, win.right, win.bottom)


def _click_observed_point(snapshot, x, y):
    """Reject stale window coordinates and honor a stop received during vision."""
    check_cancelled()
    current = gw.getActiveWindow()
    if not current or _window_snapshot(current) != snapshot:
        return "Error: The active window moved or changed. Observe again before clicking."
    _, left, top, right, bottom = snapshot
    if not left <= x < right or not top <= y < bottom:
        return "Error: Vision returned a point outside the captured window."
    pyautogui.click(x=x, y=y)
    return None


def _window_bounds(win):
    return (win.left, win.top, win.right, win.bottom)


def _uia_text_candidates(win, control_types=None):
    """Collect accessible labels without clicking the first partial match."""
    candidates = []
    types = control_types or [
        "Button", "MenuItem", "ListItem", "Hyperlink", "CheckBox",
        "RadioButton", "Edit", "Text",
    ]
    app = Desktop(backend="uia").window(handle=win._hWnd)
    for control_type in types:
        try:
            controls = app.descendants(control_type=control_type)
        except Exception:
            continue
        for control in controls:
            try:
                name = (control.element_info.name or control.window_text() or "").strip()
                rect = control.rectangle()
                if not name or rect.width() <= 0 or rect.height() <= 0:
                    continue
                if not (win.left <= (rect.left + rect.right) // 2 < win.right
                        and win.top <= (rect.top + rect.bottom) // 2 < win.bottom):
                    continue
                candidates.append(TextCandidate(
                    name, rect.left, rect.top, rect.right, rect.bottom,
                    1.0, f"uia-{control_type.lower()}", control,
                ))
            except Exception:
                continue
    return candidates


def _tesseract_candidates(img, win):
    import os
    import pytesseract
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    return build_tesseract_candidates(data, win.left, win.top)


def _ocr_candidates(img, win, reader=None):
    if reader is not None:
        import numpy as np
        return build_ocr_candidates(reader.readtext(np.array(img)), win.left, win.top)
    return _tesseract_candidates(img, win)


def _parse_json_object(value):
    """Parse a single JSON object, tolerating Markdown fences but no prose."""
    text = str(value or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    match = re.fullmatch(r"\s*(\{.*\})\s*", text, flags=re.DOTALL)
    if not match:
        raise ValueError("response was not one JSON object")
    parsed = json.loads(match.group(1))
    if not isinstance(parsed, dict):
        raise ValueError("response was not a JSON object")
    return parsed


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


def click_element(name: str, timeout: float = 5.0, region: str = "any", exact: bool = True) -> str:
    """
    Find a UI element by its accessible name anywhere in the active window
    and click it — no coordinates needed.

    Args:
        name: The text/label/name of the button, link, or control to click.
        timeout: How many seconds to wait for the element to appear.
        region: Optional window region such as left, top_right, or bottom_right.
        exact: Prefer an exact accessible label. Fuzzy matching remains strict.

    Returns:
        Success or failure message for the LLM.
    """
    log.info(f"Searching for UI element: '{name}'")
    deadline = time.time() + timeout

    while time.time() < deadline:
        check_cancelled()
        try:
            win = gw.getActiveWindow()
            if not win:
                return "Error: No active window found."

            candidates = _uia_text_candidates(
                win,
                ["Button", "MenuItem", "ListItem", "Hyperlink", "CheckBox", "RadioButton", "Edit"],
            )
            target, error = select_text_candidate(
                candidates, name, _window_bounds(win), region=region, exact=exact,
                min_confidence=1.0,
            )
            if target:
                cx, cy = target.center
                log.info("Found reliable UIA target '%s' at (%s, %s).", target.text, cx, cy)
                check_cancelled()
                target.payload.click_input()
                return (
                    f"Success: Clicked accessible element '{target.text}' at ({cx}, {cy}) "
                    f"in region '{region}'."
                )
            if error and "Ambiguous" in error:
                return error

        except TaskCancelled:
            raise
        except Exception as e:
            log.warning(f"click_element search error: {e}")

        time.sleep(0.3)

    return (
        f"Error: Could not find one reliable UI element named '{name}' in the active window "
        f"after {timeout:.0f}s. Use observe() to see what's actually on screen, "
        f"then narrow the target text or region."
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
            return f"Success: Window '{win.title}' brought to foreground."
        else:
            return f"Error: No open window found matching '{app_name}'. The app may not be running."

    except Exception as e:
        log.error(f"find_window error: {e}")
        return f"Error focusing window '{app_name}': {e}"


def _locate_text(text, timeout=5.0, region="any", exact=True):
    """Locate one unambiguous label and return its candidate plus window lease."""
    from PIL import ImageGrab
    if not normalize_text(text):
        return None, None, "Error: Provide non-empty text to find."

    try:
        min_confidence = float(__import__("core.settings", fromlist=["SettingsManager"])
                               .SettingsManager.get("vision_min_ocr_confidence", 0.50))
    except (TypeError, ValueError):
        min_confidence = 0.50
    min_confidence = max(0.0, min(1.0, min_confidence))

    reader = None
    try:
        reader = _get_ocr_reader()
    except Exception as exc:
        log.warning(f"EasyOCR init failed; using Tesseract: {exc}")

    deadline = time.monotonic() + max(0.0, float(timeout))
    last_error = None
    while time.monotonic() < deadline:
        check_cancelled()
        win = gw.getActiveWindow()
        if not win:
            return None, None, "Error: No active window found for text targeting."
        snapshot = _window_snapshot(win)

        # Accessibility labels are more reliable than pixels. Prefer them when
        # one unique target is exposed, then fall back to OCR.
        try:
            uia_candidates = _uia_text_candidates(win)
            target, error = select_text_candidate(
                uia_candidates, text, _window_bounds(win), region=region,
                exact=exact, min_confidence=1.0,
            )
            if target:
                return target, snapshot, None
            if error and "Ambiguous" in error:
                return None, snapshot, error
        except TaskCancelled:
            raise
        except Exception as exc:
            log.debug(f"UIA text targeting unavailable: {exc}")

        try:
            img = ImageGrab.grab(_window_bounds(win), all_screens=True)
            candidates = _ocr_candidates(img, win, reader)
            target, error = select_text_candidate(
                candidates, text, _window_bounds(win), region=region,
                exact=exact, min_confidence=min_confidence,
            )
            if target:
                return target, snapshot, None
            last_error = error
            if error and "Ambiguous" in error:
                return None, snapshot, error
        except TaskCancelled:
            raise
        except Exception as exc:
            last_error = f"Error: OCR targeting failed: {exc}"
            log.warning(last_error)
        time.sleep(0.35)

    return None, None, last_error or (
        f"Error: Could not find one reliable match for '{text}' after {timeout:.0f}s."
    )


def verify_text(text: str, timeout: float = 3.0, region: str = "any", exact: bool = True) -> str:
    """Verify one unambiguous label without moving the mouse."""
    log.info("Verifying text '%s' in region '%s'.", text, region)
    target, _snapshot, error = _locate_text(text, timeout, region, exact)
    if error:
        return error
    x, y = target.center
    return (
        f"Success: Verified exact visual identity '{target.text}' at ({x}, {y}) "
        f"in region '{region}' using {target.source}."
    )


def click_text(text: str, timeout: float = 5.0, region: str = "any", exact: bool = True) -> str:
    """Click one reliable UIA/OCR text target, refusing ambiguous matches."""
    log.info("Searching for reliable text target '%s' in region '%s'.", text, region)
    target, snapshot, error = _locate_text(text, timeout, region, exact)
    if error:
        return error
    check_cancelled()
    x, y = target.center
    if target.payload is not None and str(target.source).startswith("uia-"):
        current = gw.getActiveWindow()
        if not current or _window_snapshot(current) != snapshot:
            return "Error: The active window moved or changed. Observe again before clicking."
        target.payload.click_input()
    else:
        error = _click_observed_point(snapshot, x, y)
        if error:
            return error
    return (
        f"Success: Clicked verified text '{target.text}' at ({x}, {y}) "
        f"in region '{region}' using {target.source}."
    )


def click_visual(description: str) -> str:
    """Use cloud vision to propose and independently verify one target."""
    import base64
    import io
    from PIL import ImageGrab
    from core.settings import SettingsManager
    
    log.info(f"Visual Click Request: '{description}'")
    
    vision_mode = SettingsManager.get("vision_engine_type", "Cloud (LLM Vision)")
    if "Local" in vision_mode:
        log.info("Cloud vision is disabled, falling back to click_text")
        return click_text(description)

    if not description.strip():
        return "Error: Provide a description of the element to find."
    check_cancelled()
        
    win = gw.getActiveWindow()
    if not win:
        return "Error: No active window to look at."
        
    bbox = (win.left, win.top, win.right, win.bottom)
    snapshot = _window_snapshot(win)
    img = ImageGrab.grab(bbox, all_screens=True)
    width, height = img.size
    
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    prompt = (
        "Act as a cautious UI target detector. Never guess and never choose a nearby item.\n"
        f"Target: {description!r}\nImage coordinates: 0,0 to {width - 1},{height - 1}.\n"
        "Return exactly one JSON object with this schema: "
        '{"found":true,"confidence":0.0,"label":"visible identity",'
        '"bbox":[left,top,right,bottom],"point":[x,y],"alternatives":0,"reason":"short reason"}. '
        "The point must be inside the target bbox. If the exact target is absent, partly hidden, "
        "or more than one plausible target exists, return found=false and do not guess."
    )
    
    try:
        from brain import llm_provider
        if not llm_provider.FAST_MODEL:
            llm_provider.initialize_models()
        model = llm_provider.FAST_MODEL
        base = llm_provider.ACTIVE_URL
        if not model or not base:
            return "Error: No configured model is available for visual clicking."
        check_cancelled()
        
        import requests
        headers = {"Authorization": f"Bearer {llm_provider.ACTIVE_KEY}", "Content-Type": "application/json"}
        url = f"{base.strip().rstrip('/')}/chat/completions"

        def request_vision(text_prompt, image_data):
            payload = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                    ],
                }],
                "max_tokens": 220,
                "temperature": 0.0,
            }
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            check_cancelled()
            response.raise_for_status()
            return _parse_json_object(response.json()["choices"][0]["message"]["content"])

        log.info(f"Querying Cloud Vision ({model}) for a bounded target proposal...")
        proposal = request_vision(prompt, img_b64)
        if proposal.get("found") is not True:
            return f"Error: Cloud Vision could not uniquely locate '{description}'."
        try:
            confidence = float(proposal["confidence"])
            box = [int(round(float(value))) for value in proposal["bbox"]]
            point = [int(round(float(value))) for value in proposal["point"]]
            alternatives = int(proposal.get("alternatives", 0))
        except (KeyError, TypeError, ValueError):
            return "Error: Cloud Vision returned an incomplete target proposal."

        try:
            threshold = float(SettingsManager.get("vision_cloud_confidence", 0.86))
        except (TypeError, ValueError):
            threshold = 0.86
        threshold = max(0.70, min(0.99, threshold))
        if confidence < threshold:
            return (
                f"Error: Cloud Vision confidence {confidence:.2f} is below the required "
                f"{threshold:.2f}; refusing to click."
            )
        if alternatives > 0:
            return "Error: Cloud Vision found multiple plausible targets; refusing an ambiguous click."
        if len(box) != 4 or len(point) != 2:
            return "Error: Cloud Vision returned malformed target geometry."
        left, top, right, bottom = box
        local_x, local_y = point
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            return "Error: Cloud Vision returned a bounding box outside the captured image."
        if not (left <= local_x < right and top <= local_y < bottom):
            return "Error: Cloud Vision returned a click point outside its own target box."
        area_ratio = ((right - left) * (bottom - top)) / max(1, width * height)
        if area_ratio > 0.60:
            return "Error: Cloud Vision target box is too broad to click safely."

        # Verify a padded crop in a second model call. The verifier does not see
        # the full screen coordinates, so it must judge the proposed identity.
        pad_x = max(8, int((right - left) * 0.35))
        pad_y = max(8, int((bottom - top) * 0.60))
        crop_box = (
            max(0, left - pad_x), max(0, top - pad_y),
            min(width, right + pad_x), min(height, bottom + pad_y),
        )
        crop = img.crop(crop_box)
        crop_buffer = io.BytesIO()
        crop.save(crop_buffer, format="JPEG", quality=92)
        crop_b64 = base64.b64encode(crop_buffer.getvalue()).decode("utf-8")
        verify_prompt = (
            f"Verify whether this crop clearly contains the exact UI target {description!r}. "
            "Nearby labels do not count. Return exactly one JSON object: "
            '{"match":true,"confidence":0.0,"label":"visible identity","reason":"short reason"}. '
            "Return match=false if uncertain, clipped, or ambiguous."
        )
        check_cancelled()
        verification = request_vision(verify_prompt, crop_b64)
        try:
            verification_confidence = float(verification["confidence"])
        except (KeyError, TypeError, ValueError):
            return "Error: Cloud Vision verifier returned an incomplete result."
        if verification.get("match") is not True or verification_confidence < threshold:
            return (
                f"Error: Cloud Vision could not verify '{description}' with enough confidence; "
                "no click was made."
            )
        
        abs_x = win.left + local_x
        abs_y = win.top + local_y
        
        error = _click_observed_point(snapshot, abs_x, abs_y)
        if error:
            return error
        return (
            f"Success: Cloud Vision proposed and verified '{description}' "
            f"and clicked it at ({abs_x}, {abs_y})."
        )
        
    except TaskCancelled:
        raise
    except Exception as e:
        log.error(f"Cloud Vision error: {e}")
        return f"Error using Cloud Vision: {e}. Try click_text instead."
