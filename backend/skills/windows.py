"""
Phase 7 — Window Management & Power Control Skills (Revised)
Deep window finding using win32gui + psutil for maximum compatibility.
Handles UWP apps (Spotify, WhatsApp Desktop, Discord) and system tray apps
that hide from standard pygetwindow enumeration.
"""
import subprocess
import time
import pygetwindow as gw
from utils.logger import log


# ──────────────────────────────────────────────────────────────────────────────
# MONITOR DETECTION
# ──────────────────────────────────────────────────────────────────────────────

def _get_monitors():
    """Returns list of monitor rects as (left, top, right, bottom)."""
    try:
        import win32api
        monitors = []
        for m in win32api.EnumDisplayMonitors():
            info = win32api.GetMonitorInfo(m[0])
            r = info["Monitor"]
            monitors.append((r[0], r[1], r[2], r[3]))
        return monitors
    except Exception:
        return [(0, 0, 1920, 1080)]


# ──────────────────────────────────────────────────────────────────────────────
# 3-STRATEGY WINDOW FINDER
# ──────────────────────────────────────────────────────────────────────────────

def _find_window_advanced(app_name: str):
    """
    Multi-strategy window finder.
    Strategy 1: pygetwindow fast path (visible windows).
    Strategy 2: win32gui EnumWindows (catches minimized & tray apps).
    Strategy 3: psutil process name match (catches apps with dynamic titles like Spotify).

    Returns (hwnd: int, was_hidden: bool) or (None, False).
    """
    import win32gui

    app_lower = app_name.lower()

    # ── Strategy 1: Standard visible windows ─────────────────────────────────
    for win in gw.getAllWindows():
        if win.title and app_lower in win.title.lower() and win.width > 0:
            return win._hWnd, False

    # ── Strategy 2: ALL windows via EnumWindows (catches tray/hidden) ─────────
    found = [None]

    def _check_title(hwnd, _):
        if found[0]:
            return
        try:
            title = win32gui.GetWindowText(hwnd)
            if title and app_lower in title.lower():
                found[0] = hwnd
        except Exception:
            pass

    win32gui.EnumWindows(_check_title, None)
    if found[0]:
        return found[0], True

    # ── Strategy 3: Process name match via psutil ─────────────────────────────
    try:
        import psutil
        import win32process

        target_pids = set()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if app_lower in proc.info['name'].lower():
                    target_pids.add(proc.info['pid'])
            except Exception:
                pass

        if target_pids:
            def _check_pid(hwnd, _):
                if found[0]:
                    return
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid in target_pids and win32gui.GetParent(hwnd) == 0:
                        rect = win32gui.GetWindowRect(hwnd)
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        if w > 100 and h > 100:
                            found[0] = hwnd
                except Exception:
                    pass

            win32gui.EnumWindows(_check_pid, None)
            if found[0]:
                return found[0], True

    except ImportError:
        log.warning("psutil not installed — Strategy 3 unavailable.")

    return None, False


def _restore_and_position(hwnd: int, left: int, top: int, width: int, height: int):
    """Restores a window and moves it to exact screen coordinates via win32gui."""
    import win32gui
    import win32con

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.25)
    win32gui.ShowWindow(hwnd, win32con.SW_NORMAL)
    time.sleep(0.15)
    win32gui.MoveWindow(hwnd, left, top, width, height, True)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    log.info(f"Positioned hwnd={hwnd} → ({left},{top}) {width}×{height}")


# ──────────────────────────────────────────────────────────────────────────────
# WINDOW MANAGEMENT SKILLS
# ──────────────────────────────────────────────────────────────────────────────

def snap_window(app_name: str, position: str) -> str:
    """
    Snap a window to a screen position or monitor. Works with all apps including
    UWP/Store apps (Spotify, WhatsApp Desktop) and minimized/tray apps.

    Args:
        app_name: Partial name of the window or process (e.g., "Chrome", "Spotify").
        position: "left_half", "right_half", "top_half", "bottom_half",
                  "maximize", "monitor_1", "monitor_2"
    """
    log.info(f"Snapping '{app_name}' to '{position}'")

    hwnd, was_hidden = _find_window_advanced(app_name)
    if not hwnd:
        return (f"Error: No window or process found matching '{app_name}'. "
                f"Launch the app first, then snap.")

    try:
        import win32gui
        import win32con

        if was_hidden:
            log.info(f"Restoring hidden window hwnd={hwnd}...")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)

        monitors = _get_monitors()
        pos = position.lower().strip()

        if pos in ("monitor_1", "monitor1"):
            m = monitors[0]
            _restore_and_position(hwnd, m[0], m[1], m[2]-m[0], m[3]-m[1])
            return f"Moved '{app_name}' to Monitor 1 (full screen)."

        elif pos in ("monitor_2", "monitor2"):
            if len(monitors) < 2:
                return "Error: Second monitor not detected. Check Display Settings."
            m = monitors[1]
            _restore_and_position(hwnd, m[0], m[1], m[2]-m[0], m[3]-m[1])
            return f"Moved '{app_name}' to Monitor 2 (full screen)."

        else:
            # Snap within current monitor
            try:
                rect = win32gui.GetWindowRect(hwnd)
                cx = (rect[0] + rect[2]) // 2
                cy = (rect[1] + rect[3]) // 2
            except Exception:
                cx, cy = 960, 540

            cur_mon = monitors[0]
            for m in monitors:
                if m[0] <= cx < m[2] and m[1] <= cy < m[3]:
                    cur_mon = m
                    break

            ml, mt, mr, mb = cur_mon
            mw, mh = mr - ml, mb - mt

            if pos == "left_half":
                _restore_and_position(hwnd, ml, mt, mw // 2, mh)
                return f"Snapped '{app_name}' to left half."
            elif pos == "right_half":
                _restore_and_position(hwnd, ml + mw // 2, mt, mw // 2, mh)
                return f"Snapped '{app_name}' to right half."
            elif pos == "top_half":
                _restore_and_position(hwnd, ml, mt, mw, mh // 2)
                return f"Snapped '{app_name}' to top half."
            elif pos == "bottom_half":
                _restore_and_position(hwnd, ml, mt + mh // 2, mw, mh // 2)
                return f"Snapped '{app_name}' to bottom half."
            elif pos == "maximize":
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return f"Maximized '{app_name}'."
            else:
                return (f"Error: Unknown position '{position}'. "
                        f"Valid: left_half, right_half, top_half, bottom_half, maximize, monitor_1, monitor_2")

    except Exception as e:
        log.error(f"snap_window error: {e}")
        return f"Error snapping '{app_name}': {e}"


def minimize_window(app_name: str) -> str:
    """Minimize a specific window by name."""
    log.info(f"Minimizing: '{app_name}'")
    hwnd, _ = _find_window_advanced(app_name)
    if not hwnd:
        return f"Error: No window found matching '{app_name}'."
    try:
        import win32gui, win32con
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return f"Minimized '{app_name}'."
    except Exception as e:
        return f"Error: {e}"


def minimize_all_windows() -> str:
    """Minimize ALL open windows and show the Desktop (Win+D)."""
    log.info("Minimizing all windows")
    try:
        import pyautogui
        pyautogui.hotkey('win', 'd')
        return "All windows minimized. Desktop is visible."
    except Exception as e:
        return f"Error: {e}"


def restore_all_windows() -> str:
    """Restore all previously minimized windows back to screen (Win+D toggle)."""
    log.info("Restoring all windows")
    try:
        import pyautogui
        pyautogui.hotkey('win', 'd')
        return "All windows restored to their previous positions."
    except Exception as e:
        return f"Error: {e}"


def maximize_window(app_name: str) -> str:
    """Maximize a specific window by name."""
    log.info(f"Maximizing: '{app_name}'")
    hwnd, was_hidden = _find_window_advanced(app_name)
    if not hwnd:
        return f"Error: No window found matching '{app_name}'."
    try:
        import win32gui, win32con
        if was_hidden:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        win32gui.SetForegroundWindow(hwnd)
        return f"Maximized '{app_name}'."
    except Exception as e:
        return f"Error: {e}"


def close_window(app_name: str) -> str:
    """Close a specific window gracefully by name."""
    log.info(f"Closing: '{app_name}'")
    hwnd, _ = _find_window_advanced(app_name)
    if not hwnd:
        return f"Error: No window found matching '{app_name}'."
    try:
        import win32gui, win32con
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return f"Closed '{app_name}'."
    except Exception as e:
        return f"Error: {e}"


def list_open_windows() -> str:
    """
    Returns all open window titles, including hidden and tray apps (Spotify, etc.).
    Always call this ALONE in a single turn — read the result, THEN act on it.
    """
    log.info("Listing all open windows")
    try:
        import win32gui

        titles = set()

        # Visible via pygetwindow
        for w in gw.getAllWindows():
            if w.title and w.width > 0:
                titles.add(w.title)

        # All windows including hidden/minimized via EnumWindows
        def _enum(hwnd, _):
            try:
                title = win32gui.GetWindowText(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if title and w > 100 and h > 50:
                    titles.add(title)
            except Exception:
                pass

        win32gui.EnumWindows(_enum, None)

        if not titles:
            return "No open windows found."
        return "Open Windows:\n" + "\n".join(f"- {t}" for t in sorted(titles))

    except Exception as e:
        log.error(f"list_open_windows error: {e}")
        fallback = [w.title for w in gw.getAllWindows() if w.title and w.width > 0]
        return "Open Windows:\n" + "\n".join(f"- {t}" for t in fallback) if fallback else "No open windows found."


# ──────────────────────────────────────────────────────────────────────────────
# POWER CONTROL SKILLS
# ──────────────────────────────────────────────────────────────────────────────

def system_power(action: str) -> str:
    """
    Execute a system power action.
    lock / sleep — safe, no confirmation needed.
    shutdown / restart — DESTRUCTIVE: AI must confirm with ask_user first.

    Args:
        action: "lock", "sleep", "shutdown", "restart"
    """
    action_lower = action.lower().strip()
    log.info(f"System power: '{action_lower}'")

    commands = {
        "lock":     "rundll32.exe user32.dll,LockWorkStation",
        "sleep":    "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        "shutdown": "shutdown /s /t 5",
        "restart":  "shutdown /r /t 5",
    }

    if action_lower not in commands:
        return f"Error: Unknown power action '{action}'. Valid: lock, sleep, shutdown, restart."

    try:
        subprocess.Popen(commands[action_lower], shell=True)
        return {
            "lock":     "PC locked successfully.",
            "sleep":    "PC going to sleep now.",
            "shutdown": "Shutdown initiated. PC turns off in 5 seconds.",
            "restart":  "Restart initiated. PC reboots in 5 seconds.",
        }[action_lower]
    except Exception as e:
        log.error(f"system_power error: {e}")
        return f"Error executing '{action}': {e}"
