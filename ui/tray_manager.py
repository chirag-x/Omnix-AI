import threading
import io
from utils.logger import log

# ── Graceful import — if pystray/Pillow aren't installed, tray silently disables ──
try:
    import pystray
    from PIL import Image, ImageDraw
    _TRAY_AVAILABLE = True
except ImportError:
    _TRAY_AVAILABLE = False
    log.warning(
        "TrayManager: 'pystray' or 'Pillow' not installed — system tray disabled. "
        "Run: pip install pystray pillow"
    )


# ── Orb colours matching the app ───────────────────────────────────────────────
_COLOR_AWAKE   = (76, 175, 80)    # #4CAF50 green
_COLOR_SLEEP   = (96, 125, 139)   # #607D8B grey-blue
_COLOR_THINK   = (156, 39, 176)   # #9C27B0 purple
_COLOR_ERROR   = (244, 67, 54)    # #f44336 red


def _make_icon_image(rgb: tuple) -> "Image.Image":
    """Draw a 64×64 glowing-orb icon for the system tray."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer soft glow ring
    glow_color = (*rgb, 80)   # semi-transparent
    draw.ellipse([2, 2, size - 2, size - 2], outline=glow_color, width=4)

    # Solid orb
    draw.ellipse([8, 8, size - 8, size - 8], fill=(*rgb, 255))

    # Specular highlight (top-left white blob)
    draw.ellipse([14, 14, 28, 24], fill=(255, 255, 255, 90))
    return img


class TrayManager:
    """
    Manages the Windows system tray icon for Omnix.

    The tray icon:
      - Shows the current awake/sleeping state via orb colour
      - Provides a right-click menu to wake, sleep, open, or quit
      - Closing the main window hides it here instead of terminating the app

    Usage:
        tray = TrayManager(on_wake, on_sleep, on_open, on_quit)
        tray.start()                    # non-blocking, runs in background thread
        tray.update_state("awake")     # or "sleeping" / "thinking"
        tray.stop()
    """

    _STATES = {
        "awake":    (_COLOR_AWAKE,  "Omnix  —  Awake"),
        "sleeping": (_COLOR_SLEEP,  "Omnix  —  Sleeping"),
        "thinking": (_COLOR_THINK,  "Omnix  —  Thinking…"),
        "error":    (_COLOR_ERROR,  "Omnix  —  Error"),
    }

    def __init__(self, on_wake, on_sleep, on_open, on_quit):
        self._on_wake  = on_wake
        self._on_sleep = on_sleep
        self._on_open  = on_open
        self._on_quit  = on_quit

        self._icon = None
        self._thread: threading.Thread | None = None
        self._available = _TRAY_AVAILABLE

    # ─── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Start the tray icon in a background daemon thread."""
        if not self._available:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="TrayManager")
        self._thread.start()

    def stop(self):
        """Remove the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def update_state(self, state: str):
        """
        Update the tray icon colour and tooltip.
        state must be one of: 'awake', 'sleeping', 'thinking', 'error'.
        """
        if not self._icon or not self._available:
            return
        rgb, title = self._STATES.get(state, self._STATES["sleeping"])
        try:
            self._icon.icon  = _make_icon_image(rgb)
            self._icon.title = title
        except Exception as e:
            log.error(f"TrayManager.update_state error: {e}")

    @property
    def available(self) -> bool:
        return self._available

    # ─── Internal ──────────────────────────────────────────────────────────────

    def _run(self):
        """Blocking tray icon run — called in background thread."""
        try:
            menu = pystray.Menu(
                pystray.MenuItem("Open Omnix",    self._safe(self._on_open),  default=True),
                pystray.MenuItem("Wake Up",       self._safe(self._on_wake)),
                pystray.MenuItem("Sleep",         self._safe(self._on_sleep)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit Omnix",    self._safe(self._on_quit)),
            )
            self._icon = pystray.Icon(
                name   = "Omnix",
                icon   = _make_icon_image(_COLOR_SLEEP),
                title  = "Omnix  —  Sleeping",
                menu   = menu,
            )
            self._icon.run()
        except Exception as e:
            log.error(f"TrayManager: Tray icon error: {e}")

    @staticmethod
    def _safe(fn):
        """Wrap a callback so tray clicks don't crash if callback raises."""
        def wrapper(icon=None, item=None):
            try:
                fn()
            except Exception as exc:
                log.error(f"TrayManager callback error: {exc}")
        return wrapper
