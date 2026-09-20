"""
Omnix — Main UI Application
============================
Fully hands-free voice assistant UI built with Flet.

Voice flow:
    WakeEngine detects "Hey Omnix"
    → CommandListener auto-starts continuous mic listening
    → Each captured phrase is transcribed and processed as a command
    → 30 s of silence → auto-sleep

UI structure:
    TopBar          (logo, wake badge, shortcut btn, settings gear)
    OrbArea         (animated glowing orb + emotion gradient glow)
    ChatLog         (scrollable conversation history, max 50 msgs)
    StatusBar       (backend · listening · models)
    InputArea       (text field + send btn + contextual stop btn)
"""

import asyncio
import threading
import sys
import os
import math

sys.path.insert(0, os.path.dirname(__file__))

import flet as ft
from core.config import Config
from core.settings import SettingsManager
from brain.orchestrator import process_command, trigger_abort
from senses.hearing import transcribe_audio
from wake_engine import WakeEngine
from command_listener import CommandListener
from tts_player import play_audio_b64
from settings_page import build_settings_page
from tray_manager import TrayManager
from utils.logger import log

# ── Emotion → orb colour map ──────────────────────────────────────────────────
EMOTION_COLORS = {
    "neutral":  "#4CAF50",
    "happy":    "#FFD700",
    "excited":  "#FF6B35",
    "sad":      "#2196F3",
    "confused": "#9C27B0",
    "thinking": "#607D8B",
}

# ── Orb states ────────────────────────────────────────────────────────────────
class OrbState:
    LOADING    = "loading"
    SLEEPING   = "sleeping"
    AWAKE_IDLE = "awake_idle"
    LISTENING  = "listening"
    THINKING   = "thinking"
    SPEAKING   = "speaking"
    ERROR      = "error"

# ── Per-state orb look ───────────────────────────────────────────────────────
_ORB_STYLE = {
    OrbState.LOADING:    dict(color="#607D8B", glow_color="#607D8B",
                              spread=6,  blur=20, scale_min=0.85, scale_max=0.90, interval=1.5,
                              label="⏳  Initializing Omnix…"),
    OrbState.SLEEPING:   dict(color="#2a2a4a", glow_color="#333366",
                              spread=4,  blur=15, scale_min=0.90, scale_max=0.90, interval=0,
                              label="💤  Say 'Hey Omnix' to wake me up"),
    OrbState.AWAKE_IDLE: dict(color="#4CAF50", glow_color="#4CAF50",
                              spread=14, blur=45, scale_min=1.00, scale_max=1.07, interval=1.2,
                              label="🟢  Ready — listening for your command…"),
    OrbState.LISTENING:  dict(color="#29B6F6", glow_color="#29B6F6",
                              spread=20, blur=60, scale_min=1.05, scale_max=1.14, interval=0.55,
                              label="🎙️  Capturing your voice…"),
    OrbState.THINKING:   dict(color="#CE93D8", glow_color="#9C27B0",
                              spread=18, blur=55, scale_min=1.00, scale_max=1.10, interval=0.40,
                              label="🧠  Processing…"),
    OrbState.SPEAKING:   dict(color="#4CAF50", glow_color="#4CAF50",
                              spread=22, blur=65, scale_min=1.02, scale_max=1.12, interval=0.45,
                              label="💬  Speaking…"),
    OrbState.ERROR:      dict(color="#f44336", glow_color="#f44336",
                              spread=10, blur=30, scale_min=1.00, scale_max=1.00, interval=0,
                              label="❌  Something went wrong"),
}

# ── Accent colours (default purple — user can change in Settings) ─────────────
_DEFAULT_ACCENT = "#7C4DFF"


class OmnixApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.is_awake = False
        self.is_processing = False

        self._loop = asyncio.get_event_loop()
        self._accent = SettingsManager.get("accent_color") or _DEFAULT_ACCENT

        # Pulse animation state
        self._should_pulse = False
        self._pulse_expanding = True
        self._pulse_timer: threading.Timer | None = None
        self._orb_state = OrbState.SLEEPING

        # Wake / command engines (initialised after UI is up)
        self.wake_engine: WakeEngine | None = None
        self.command_listener: CommandListener | None = None
        self.tray: TrayManager | None = None

        self._setup_page()
        self._build_ui()

        # Start background services after first frame renders
        threading.Thread(target=self._start_services, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE SETUP
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_page(self):
        self.page.title   = "Omnix"
        self.page.bgcolor = ft.Colors.TRANSPARENT
        self.page.padding = 0

                # Theme & Opacity from Settings
        is_dark = SettingsManager.get("dark_mode", True)
        self.page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        try:
            self.page.window.opacity = float(SettingsManager.get("window_opacity", 1.0))
        except:
            pass

        # Modern Inter Font
        self.page.fonts = {
            "Inter": "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/Inter-Regular.woff2",
            "monospace": "Consolas"
        }
        self.page.theme = ft.Theme(font_family="Inter")

        # Global modern gradient background (Theme aware)
        bg_colors = ["#0f0c29", "#302b63", "#0f0c29"] if is_dark else ["#e0eafc", "#cfdef3", "#e0eafc"]
        self.page.decoration = ft.BoxDecoration(
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=bg_colors,
            )
        )

        # Full-screen-capable, resizable, standard window chrome
        self.page.window.maximized  = True
        self.page.window.resizable  = True
        self.page.window.min_width  = 480
        self.page.window.min_height = 640

        # Intercept close
        self.page.window.prevent_close = True
        self.page.window.on_event = self._on_window_event

        # Global keyboard: Escape closes overlays
        self.page.on_keyboard_event = self._on_keyboard

    def _on_window_event(self, e: ft.WindowEvent):
        if e.type == ft.WindowEventType.CLOSE:
            # Close the app completely
            self._quit_app()

    def _on_keyboard(self, e: ft.KeyboardEvent):
        if e.key == "Escape":
            # Close any open dialog
            if self.page.dialog and self.page.dialog.open:
                self.page.dialog.open = False
                self.page.update()
                
        # Parse user hotkeys
        def check_hotkey(hotkey_str):
            if not hotkey_str: return False
            parts = [p.strip().lower() for p in hotkey_str.split("+")]
            needs_ctrl = "ctrl" in parts
            needs_shift = "shift" in parts
            needs_alt = "alt" in parts
            key = parts[-1]
            if key == "v": key = "V"
            if key == "x": key = "X"
            return (e.ctrl == needs_ctrl and 
                    e.shift == needs_shift and 
                    e.alt == needs_alt and 
                    e.key.lower() == key.lower())

        cycle_hk = SettingsManager.get("hotkey_cycle_activation", "Ctrl+Shift+V")
        stop_hk = SettingsManager.get("hotkey_stop_generation", "Ctrl+X")
        
        if check_hotkey(cycle_hk):
            print("Cycling Activation Mode via Hotkey!")
            # Logic to cycle activation mode
            modes = ["Developer Mode", "Premium Activation (Paid AI)", "Basic Activation (Free AI)", "Free Local Activation (Ollama)"]
            curr = SettingsManager.get("activation_mode", modes[-1])
            try:
                next_mode = modes[(modes.index(curr) + 1) % len(modes)]
            except:
                next_mode = modes[0]
            SettingsManager.set("activation_mode", next_mode)
            # Optionally show a snackbar
            self.page.overlay.append(ft.SnackBar(ft.Text(f"Mode switched to {next_mode}"), open=True))
            self.page.update()
            
        if check_hotkey(stop_hk):
            print("Stopping Generation via Hotkey!")
            # Add logic here to interrupt streaming/TTS
            self.page.overlay.append(ft.SnackBar(ft.Text("Generation Stopped"), open=True))
            self.page.update()

    # ══════════════════════════════════════════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self._build_top_bar()
        self._build_orb_area()
        self._build_chat_log()
        self._build_status_bar()
        self._build_input_area()
        self._build_shortcut_dialog()

        self.main_content = ft.Column(
            controls=[
                self.top_bar,
                ft.Divider(color="#1a1a2e", height=1),
                self.orb_area,
                ft.Divider(color="#111130", height=1),
                self.chat_log_container,   # expands
                self.status_bar,
                self.input_area,
            ],
            spacing=0,
            expand=True,
        )

        self.page.add(self.main_content)
        self.page.update()

        # Start in LOADING state
        self._set_orb_state(OrbState.LOADING)

    # ── Top bar ───────────────────────────────────────────────────────────────

    def _build_top_bar(self):
        # Logo mark (hex-ish unicode)
        logo_mark = ft.Text("⬡", size=22, color=self._accent, weight=ft.FontWeight.BOLD)
        logo_text = ft.Text("OMNIX", size=18, weight=ft.FontWeight.BOLD, color="white")

        # Wake badge
        self.wake_badge_text = ft.Text(
            "💤  Sleeping", size=12, weight=ft.FontWeight.BOLD, color="white"
        )
        self.wake_badge = ft.Container(
            content=self.wake_badge_text,
            bgcolor="#333355",
            border_radius=20,
            padding=ft.Padding(left=14, right=14, top=6, bottom=6),
            animate=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        )

        # Shortcut ? button
        shortcut_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            icon_color="#666",
            icon_size=20,
            tooltip="Keyboard shortcuts",
            on_click=self._show_shortcuts,
        )

        # Settings gear
        settings_btn = ft.IconButton(
            icon=ft.Icons.SETTINGS_OUTLINED,
            icon_color="#666",
            icon_size=20,
            tooltip="Settings",
            on_click=self._open_settings,
        )

        self.top_bar = ft.Container(
            content=ft.Row(
                [
                    ft.Row([logo_mark, logo_text], spacing=8),
                    ft.Row([self.wake_badge, shortcut_btn, settings_btn], spacing=2),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding(left=20, right=12, top=12, bottom=12),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            blur=ft.Blur(10, 10, ft.BlurTileMode.MIRROR),
        )

    # ── Orb area ──────────────────────────────────────────────────────────────

    def _build_orb_area(self):
        """
        Stack layout (320×280):
          [0] gradient glow blob behind the orb
          [1] orb container (animated scale + colour)
        Below stack: state label text
        """
        # Gradient glow blob (larger soft circle behind the orb)
        self.orb_glow = ft.Container(
            width=280, height=280,
            border_radius=140,
            bgcolor="#4CAF50",
            opacity=0.0,           # starts invisible; fades in when awake
            animate=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
            animate_opacity=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
        )

        # Multi-layered dynamic orb
        self.orb_core = ft.Container(
            width=140, height=140,
            border_radius=70,
            bgcolor="#2a2a4a",
            shadow=ft.BoxShadow(spread_radius=4, blur_radius=15, color="#33336688", offset=ft.Offset(0, 0)),
            animate=ft.Animation(450, ft.AnimationCurve.EASE_IN_OUT),
            animate_scale=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        )
        self.orb_ring1 = ft.Container(
            width=170, height=170,
            border_radius=85,
            border=ft.Border.all(4, "#2a2a4a"),
            animate=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
            animate_scale=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
        )
        self.orb_ring2 = ft.Container(
            width=200, height=200,
            border_radius=100,
            border=ft.Border.all(1, "#2a2a4a"),
            animate=ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT),
            animate_scale=ft.Animation(700, ft.AnimationCurve.EASE_IN_OUT),
        )

        # Wrapper for scale animation (holds the stack of rings)
        self.orb_wrapper = ft.Container(
            content=ft.Stack(
                [
                    ft.Container(content=self.orb_ring2, alignment=ft.Alignment(0, 0)),
                    ft.Container(content=self.orb_ring1, alignment=ft.Alignment(0, 0)),
                    ft.Container(content=self.orb_core, alignment=ft.Alignment(0, 0)),
                ],
                width=200, height=200,
            ),
            width=200, height=200,
            alignment=ft.Alignment(0, 0)
        )

        # State label shown below the orb
        self.orb_label = ft.Text(
            "💤  Say 'Hey Omnix' to wake me up",
            size=13,
            color="#666688",
            italic=True,
            text_align=ft.TextAlign.CENTER,
            animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        )

        # Stack: glow behind, orb on top — centred
        orb_stack = ft.Stack(
            [
                ft.Container(content=self.orb_glow, alignment=ft.Alignment(0, 0)),
                ft.Container(content=self.orb_wrapper, alignment=ft.Alignment(0, 0)),
            ],
            width=320,
            height=220,
        )

        self.orb_area = ft.Container(
            content=ft.Column(
                [orb_stack, self.orb_label],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=ft.Padding(left=0, right=0, top=16, bottom=12),
            alignment=ft.Alignment(0, 0),
        )

    # ── Chat log ─────────────────────────────────────────────────────────────

    def _build_chat_log(self):
        self.chat_log = ft.ListView(
            expand=True,
            spacing=6,
            auto_scroll=True,
            padding=ft.Padding(left=16, right=16, top=10, bottom=10),
        )

        self.chat_log_container = ft.Container(
            content=self.chat_log,
            expand=True,
            bgcolor="#09091a",
            border=ft.Border(
                top=ft.BorderSide(1, "#181830"),
                bottom=ft.BorderSide(1, "#181830"),
            ),
        )

    # ── Status bar ───────────────────────────────────────────────────────────

    def _build_status_bar(self):
        self.backend_dot   = ft.Container(width=8, height=8, border_radius=4, bgcolor="#f44336")
        self.backend_label = ft.Text("Connecting…", size=11, color="#555577")
        self.mic_status    = ft.Text("🎙 Initializing", size=11, color="#555577")
        self.model_status  = ft.Text("", size=11, color="#555577")

        self.status_bar = ft.Container(
            content=ft.Row(
                [
                    self.backend_dot,
                    self.backend_label,
                    ft.Text("·", size=11, color="#333355"),
                    self.mic_status,
                    ft.Text("·", size=11, color="#333355"),
                    self.model_status,
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            blur=ft.Blur(10, 10, ft.BlurTileMode.MIRROR),
            padding=ft.Padding(left=16, right=16, top=6, bottom=6),
            border=ft.Border(top=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE))),
        )

    # ── Input area ───────────────────────────────────────────────────────────

    def _build_input_area(self):
        self.text_input = ft.TextField(
            hint_text="Say 'Hey Omnix' to activate, or type here…",
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.4, "#111122"),
            color="white" if SettingsManager.get("dark_mode", True) else "black",
            border_color="#2a2a4a",
            focused_border_color=self._accent,
            border_radius=14,
            text_size=14,
            cursor_color=self._accent,
            hint_style=ft.TextStyle(color="#444466"),
            on_submit=self._send_text,
            disabled=True,
            multiline=True,
            min_lines=1,
            max_lines=5,
            shift_enter=True,
        )

        self.send_btn = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color="white" if SettingsManager.get("dark_mode", True) else "black",
            bgcolor=self._accent,
            icon_size=20,
            tooltip="Send (Enter)",
            on_click=self._send_text,
            disabled=True,
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
        )

        self.stop_btn = ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.STOP_CIRCLE_ROUNDED,
                icon_color="white" if SettingsManager.get("dark_mode", True) else "black",
                bgcolor="#FF5722",
                icon_size=20,
                tooltip="Stop current task  (Ctrl+X)",
                on_click=lambda e: trigger_abort(),
                style=ft.ButtonStyle(shape=ft.CircleBorder()),
            ),
            visible=False,
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        )

        self.input_area = ft.Container(
            content=ft.Row(
                [self.text_input, self.send_btn, self.stop_btn],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            padding=ft.Padding(left=16, right=16, top=12, bottom=16),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            blur=ft.Blur(10, 10, ft.BlurTileMode.MIRROR),
        )

    # ── Shortcut dialog ──────────────────────────────────────────────────────

    def _build_shortcut_dialog(self):
        def row(keys, action):
            return ft.Row([
                ft.Container(
                    content=ft.Text(keys, size=13, color="#BB86FC",
                                    weight=ft.FontWeight.BOLD, font_family="monospace"),
                    bgcolor="#1a1a30" if SettingsManager.get("dark_mode", True) else "#ffffff",
                    border_radius=6,
                    padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                    width=180,
                ),
                ft.Text(action, size=13, color="#aaaacc"),
            ], spacing=12)

        self.shortcut_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⌨️  Keyboard Shortcuts", size=16, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor="#0d0d1a" if SettingsManager.get("dark_mode", True) else "#f4f6f9",
            content=ft.Column(
                [
                    row("Hey Omnix",       "Wake Omnix (voice)"),
                    row("Enter",           "Send typed message"),
                    row("Ctrl + X",        "Stop current task"),
                    row("Escape",          "Close this panel"),
                ],
                spacing=12,
                tight=True,
            ),
            actions=[
                ft.TextButton(
                    "Close",
                    style=ft.ButtonStyle(color=self._accent),
                    on_click=lambda e: self._close_dialog(),
                )
            ],
        )
        self.page.dialog = self.shortcut_dialog

    def _show_shortcuts(self, e=None):
        self.shortcut_dialog.open = True
        self.page.update()

    def _close_dialog(self):
        self.shortcut_dialog.open = False
        self.page.update()

    # ══════════════════════════════════════════════════════════════════════════
    #  SETTINGS VIEW
    # ══════════════════════════════════════════════════════════════════════════

    def _open_settings(self, e=None):
        self.page.controls.clear()
        self.page.add(ft.Container(
            content=build_settings_page(self.page, self._close_settings),
            expand=True,
            bgcolor="#0d0d1a" if SettingsManager.get("dark_mode", True) else "#f4f6f9",
        ))
        self.page.update()

    def _close_settings(self):
        # Reload accent colour in case user changed it
        self._accent = SettingsManager.get("accent_color") or _DEFAULT_ACCENT
        self.page.controls.clear()
        self.page.add(self.main_content)
        self.page.update()

    # ══════════════════════════════════════════════════════════════════════════
    #  ORB STATE MACHINE
    # ══════════════════════════════════════════════════════════════════════════

    def _set_orb_state(self, state: str, emotion: str = "neutral"):
        self._orb_state = state
        style = _ORB_STYLE.get(state, _ORB_STYLE[OrbState.SLEEPING])

        # Override colour for SPEAKING state using emotion map
        if state == OrbState.SPEAKING:
            color = EMOTION_COLORS.get(emotion, "#4CAF50")
            style = {**style, "color": color, "glow_color": color}

        # Stop any running pulse
        self._stop_pulse_loop()

        # Apply orb colour + shadow to all layers
        self.orb_core.bgcolor = style["color"]
        self.orb_ring1.border = ft.Border.all(4, style["color"])
        self.orb_ring2.border = ft.Border.all(1, style["color"])
        
        self.orb_core.shadow = ft.BoxShadow(
            spread_radius=style["spread"],
            blur_radius=style["blur"],
            color=style["glow_color"] + "88",
            offset=ft.Offset(0, 0),
        )

        # Gradient glow behind the orb
        if state in (OrbState.SLEEPING, OrbState.LOADING):
            self.orb_glow.opacity = 0.0
        else:
            self.orb_glow.bgcolor = style["glow_color"]
            self.orb_glow.opacity = 0.10

        # State label
        self.orb_label.value = style["label"]
        self.orb_label.color = "#666688" if state == OrbState.SLEEPING else "#aaaacc"

        try:
            self.page.update()
        except Exception:
            pass

        # Start pulse loop if needed
        if style["interval"] > 0:
            self._start_pulse_loop(
                scale_min=style["scale_min"],
                scale_max=style["scale_max"],
                interval=style["interval"],
            )
        else:
            # Snap to resting scale
            self.orb_wrapper.scale = ft.Scale(style["scale_min"])
            try:
                self.page.update()
            except Exception:
                pass

    # ── Pulse loop ────────────────────────────────────────────────────────────

    def _start_pulse_loop(self, scale_min: float, scale_max: float, interval: float):
        self._should_pulse = True
        self._pulse_expanding = True
        self._scale_min = scale_min
        self._scale_max = scale_max
        self._pulse_interval = interval
        self._run_pulse_step()

    def _stop_pulse_loop(self):
        self._should_pulse = False
        if self._pulse_timer:
            self._pulse_timer.cancel()
            self._pulse_timer = None

    def _run_pulse_step(self):
        if not self._should_pulse:
            return
        try:
            if self._pulse_expanding:
                self.orb_core.scale = ft.Scale(self._scale_max)
                self.orb_ring1.scale = ft.Scale(self._scale_max * 1.05)
                self.orb_ring2.scale = ft.Scale(self._scale_max * 1.10)
                self._pulse_expanding = False
            else:
                self.orb_core.scale = ft.Scale(self._scale_min)
                self.orb_ring1.scale = ft.Scale(self._scale_min)
                self.orb_ring2.scale = ft.Scale(self._scale_min)
                self._pulse_expanding = True
            self.page.update()
        except Exception:
            return  # Page closing

        self._pulse_timer = threading.Timer(self._pulse_interval, self._run_pulse_step)
        self._pulse_timer.daemon = True
        self._pulse_timer.start()

    # ══════════════════════════════════════════════════════════════════════════
    #  CHAT LOG
    # ══════════════════════════════════════════════════════════════════════════

    def _add_user_bubble(self, text: str):
        import datetime
        timestamp = datetime.datetime.now().strftime("%I:%M %p")
        
        bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Text(text, color="white" if SettingsManager.get("dark_mode", True) else "black", size=14, selectable=True),
                    ft.Text(timestamp, size=10, color="#666688", italic=True),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.END,
            ),
            bgcolor=ft.Colors.with_opacity(0.8, "#2a1f5a"),
            border_radius=ft.BorderRadius(
                top_left=16, top_right=4, bottom_left=16, bottom_right=16
            ),
            padding=ft.Padding(left=16, right=16, top=10, bottom=10),
            margin=ft.Margin(left=80, right=4, top=2, bottom=2),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN),
            opacity=1,
            blur=ft.Blur(5, 5, ft.BlurTileMode.MIRROR)
        )
        self.chat_log.controls.append(ft.Row([bubble], alignment=ft.MainAxisAlignment.END))
        self._trim_chat_log()
        try:
            self.page.update()
        except Exception:
            pass

    def _add_omnix_bubble(self, text: str, emotion: str = "neutral"):
        color = EMOTION_COLORS.get(emotion, "#4CAF50")
        import datetime
        timestamp = datetime.datetime.now().strftime("%I:%M %p")
        
        def copy_click(e):
            self.page.set_clipboard(text)
            self.show_toast("📋 Copied to clipboard!")
        
        md = ft.Markdown(
            text,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            code_theme="atom-one-dark",
            on_tap_link=lambda e: self.page.launch_url(e.data)
        )
        
        copy_btn = ft.IconButton(
            ft.Icons.COPY_ROUNDED,
            icon_size=16,
            icon_color="#666688",
            tooltip="Copy message",
            on_click=copy_click,
            padding=0,
            width=28,
            height=28
        )
        
        bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Container(content=md, expand=True), copy_btn], vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Text(timestamp, size=10, color="#666688", italic=True),
                ],
                spacing=4,
            ),
            bgcolor=ft.Colors.with_opacity(0.5, "#0f0f24"),
            border=ft.Border(left=ft.BorderSide(3, color)),
            border_radius=ft.BorderRadius(
                top_left=4, top_right=16, bottom_left=16, bottom_right=16
            ),
            padding=ft.Padding(left=14, right=16, top=10, bottom=10),
            margin=ft.Margin(left=4, right=80, top=2, bottom=2),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN),
            opacity=1,
            blur=ft.Blur(5, 5, ft.BlurTileMode.MIRROR)
        )
        self.chat_log.controls.append(ft.Row([bubble]))
        self._trim_chat_log()
        try:
            self.page.update()
        except Exception:
            pass

    def _trim_chat_log(self):
        """Keep at most 50 message bubbles in the log."""
        if len(self.chat_log.controls) > 50:
            del self.chat_log.controls[: len(self.chat_log.controls) - 50]

    # ── System status messages (italic, centred) ──────────────────────────────

    def _add_system_message(self, text: str, color: str = "#444466"):
        label = ft.Container(
            content=ft.Text(text, size=12, color=color, italic=True,
                            text_align=ft.TextAlign.CENTER),
            margin=ft.Margin(top=4, bottom=4, left=0, right=0),
        )
        self.chat_log.controls.append(ft.Row([label], alignment=ft.MainAxisAlignment.CENTER))
        try:
            self.page.update()
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  TOAST NOTIFICATION
    # ══════════════════════════════════════════════════════════════════════════

    def show_toast(self, message: str, color: str = "#4CAF50"):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color="white"),
            bgcolor=color,
            duration=3000,
        )
        self.page.snack_bar.open = True
        try:
            self.page.update()
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  WAKE / SLEEP
    # ══════════════════════════════════════════════════════════════════════════

    def _on_wake(self):
        if self.is_awake:
            return
        self.is_awake = True
        if self.wake_engine:
            self.wake_engine.set_awake(True)
        self._set_awake_ui(True)

        # Start hands-free listener
        if self.command_listener:
            self.command_listener.start_listening()

        if self.tray:
            self.tray.update_state("awake")

        asyncio.run_coroutine_threadsafe(
            self._speak_phrase("Hey! I'm awake and ready. What would you like me to do?"),
            self._loop,
        )

    def _on_sleep(self):
        if not self.is_awake:
            return
        self.is_awake = False
        if self.wake_engine:
            self.wake_engine.set_awake(False)
        if self.command_listener:
            self.command_listener.stop_listening()

        self._set_awake_ui(False)

        if self.tray:
            self.tray.update_state("sleeping")

        asyncio.run_coroutine_threadsafe(
            self._speak_phrase("Going to sleep. Say Hey Omnix to wake me up."),
            self._loop,
        )

    def _set_awake_ui(self, awake: bool):
        if awake:
            self.wake_badge_text.value = "🟢  Awake"
            self.wake_badge.bgcolor    = "#1b5e20"
            self.text_input.disabled   = False
            self.text_input.hint_text  = "Type a command or just speak…"
            self.send_btn.disabled     = False
            self.mic_status.value      = "🎙 Listening"
            self._set_orb_state(OrbState.AWAKE_IDLE)
            self._add_system_message("— Omnix is awake —", "#4CAF5088")
        else:
            self.wake_badge_text.value = "💤  Sleeping"
            self.wake_badge.bgcolor    = "#333355"
            self.text_input.disabled   = True
            self.text_input.hint_text  = "Say 'Hey Omnix' to activate…"
            self.send_btn.disabled     = True
            self.mic_status.value      = "🎙 Idle"
            self._set_orb_state(OrbState.SLEEPING)
            self._add_system_message("— Omnix went to sleep —", "#33335588")

        try:
            self.page.update()
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  COMMAND LISTENER CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════

    def _on_voice_speech_start(self):
        """Called when CommandListener detects audio arriving (before transcription)."""
        self._set_orb_state(OrbState.LISTENING)
        self.mic_status.value = "🎙 Capturing…"
        try:
            self.page.update()
        except Exception:
            pass

    def _on_voice_speech_end(self):
        """Called when CommandListener finishes transcription with no usable text."""
        if self.is_awake and not self.is_processing:
            self._set_orb_state(OrbState.AWAKE_IDLE)
            self.mic_status.value = "🎙 Listening"
            try:
                self.page.update()
            except Exception:
                pass

    def _on_voice_command(self, text: str):
        """Called when CommandListener has a transcribed command ready."""
        self._add_user_bubble(text)
        asyncio.run_coroutine_threadsafe(self._run_command(text), self._loop)

    def _on_voice_silence(self):
        """Called by CommandListener after silence timeout — go to sleep."""
        self._on_sleep()

    # ══════════════════════════════════════════════════════════════════════════
    #  TEXT INPUT
    # ══════════════════════════════════════════════════════════════════════════

    def _send_text(self, e=None):
        text = (self.text_input.value or "").strip()
        if not text:
            return
        self.text_input.value = ""
        self._add_user_bubble(text)
        asyncio.run_coroutine_threadsafe(self._run_command(text), self._loop)

    # ══════════════════════════════════════════════════════════════════════════
    #  COMMAND EXECUTION
    # ══════════════════════════════════════════════════════════════════════════

    async def _run_command(self, text: str):
        self.is_processing = True
        if self.command_listener:
            self.command_listener.set_processing(True)

        # Show thinking state
        self._set_orb_state(OrbState.THINKING)
        self.stop_btn.visible = True
        if self.tray:
            self.tray.update_state("thinking")
        try:
            self.page.update()
        except Exception:
            pass

        try:
            await process_command(text, self._on_response)
        except Exception as e:
            import traceback
            log.error(f"process_command crashed: {e}\n{traceback.format_exc()}")
        finally:
            self.is_processing = False
            if self.command_listener:
                self.command_listener.set_processing(False)

            # Back to idle if still awake
            if self.is_awake:
                self._set_orb_state(OrbState.AWAKE_IDLE)
                if self.tray:
                    self.tray.update_state("awake")

            self.stop_btn.visible = False
            try:
                self.page.update()
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════════════════
    #  RESPONSE HANDLER
    # ══════════════════════════════════════════════════════════════════════════

    def _on_response(self, text: str, emotion: str, audio_b64: str):
        self._add_omnix_bubble(text, emotion)
        self._set_orb_state(OrbState.SPEAKING, emotion)
        try:
            self.page.update()
        except Exception:
            pass
        if audio_b64:
            play_audio_b64(audio_b64)

    # ══════════════════════════════════════════════════════════════════════════
    #  TTS HELPER
    # ══════════════════════════════════════════════════════════════════════════

    async def _speak_phrase(self, text: str):
        from senses.speech import generate_audio
        audio_b64 = await generate_audio(text)
        play_audio_b64(audio_b64)

    # ══════════════════════════════════════════════════════════════════════════
    #  BACKGROUND SERVICES STARTUP
    # ══════════════════════════════════════════════════════════════════════════

    def _start_services(self):
        """Runs in a background thread — keeps UI responsive during init."""

        # Step 1: Check OmniRoute backend
        self._loading_step("🔌  Checking AI backend connection…")
        self._check_omniroute()

        # Step 2: Test / warm up models
        self._loading_step("⚡  Discovering available AI models…")
        try:
            from brain.llm_provider import initialize_models
            count = initialize_models()
            self.model_status.value = f"⚡ {count} models online" if count else "⚡ No models"
        except Exception as e:
            log.warning(f"Model init error: {e}")
            self.model_status.value = "⚡ Model check failed"

        try:
            self.page.update()
        except Exception:
            pass

        # Step 3: Start wake engine (loads tiny Whisper + calibrates mic)
        self._loading_step("🧠  Loading wake-word model…")
        self._start_wake_engine()

        # Step 4: Ready
        self._set_orb_state(OrbState.SLEEPING)
        self._add_system_message("✅  Omnix is ready — say 'Hey Omnix' to begin", "#4CAF5099")
        self.mic_status.value = "🎙 Idle"
        try:
            self.page.update()
        except Exception:
            pass

        # Step 5: System tray
        self._start_tray()

    def _loading_step(self, message: str):
        self._add_system_message(message, "#556688")
        try:
            self.page.update()
        except Exception:
            pass

    def _start_wake_engine(self):
        self.wake_engine = WakeEngine(on_wake_detected=self._on_wake)
        self.wake_engine.start()

        # Wait until the WakeEngine has loaded its model (poll longer for first-time downloads)
        import time
        for _ in range(600):  # up to 300 seconds for initial download
            if self.wake_engine.model is not None:
                break
            time.sleep(0.5)

        # Build independent CommandListener
        self.command_listener = CommandListener(
            on_command        = self._on_voice_command,
            on_silence        = self._on_voice_silence,
            on_speech_start   = self._on_voice_speech_start,
            on_speech_end     = self._on_voice_speech_end,
        )

    def _start_tray(self):
        self.tray = TrayManager(
            on_wake  = self._on_wake,
            on_sleep = self._on_sleep,
            on_open  = self._restore_window,
            on_quit  = self._quit_app,
        )
        self.tray.start()

    # ── OmniRoute health check ─────────────────────────────────────────────

    def _check_omniroute(self):
        from core.config import SettingsManager
        mode = SettingsManager.get("activation_mode", "Free Local Activation (Ollama)")
        if mode != "Developer Mode":
            self.backend_dot.bgcolor = "#4CAF50"
            self.backend_label.value = "Brain Ready (External)"
            try:
                self.page.update()
            except Exception:
                pass
            return
            
        autostart = SettingsManager.get("omniroute_autostart", True)
        import socket
        import subprocess
        import time

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", 20128))

        if result != 0:
            if autostart:
                log.warning("OmniRoute offline — auto-starting…")
                subprocess.Popen("start cmd /k omniroute", shell=True)
                time.sleep(3)
            else:
                log.warning("OmniRoute offline (Auto-start disabled in Settings)")

        self.backend_dot.bgcolor   = "#4CAF50"
        self.backend_label.value   = "Brain Connected"
        try:
            self.page.update()
        except Exception:
            pass

    # ── Window management ─────────────────────────────────────────────────

    def _restore_window(self):
        self.page.window.visible = True
        self.page.window.bring_to_front()
        try:
            self.page.update()
        except Exception:
            pass

    def _quit_app(self):
        if self.tray:
            self.tray.stop()
        try:
            self.page.window.prevent_close = False
            self.page.run_task(self.page.window.destroy)
        except Exception:
            pass
            
        import threading, time, os, subprocess
        def kill_soon():
            time.sleep(0.3)
            # Use Windows taskkill to forcibly kill Python and the Flet UI child process
            subprocess.Popen(f"taskkill /F /T /PID {os.getpid()}", shell=True)
            
        t = threading.Thread(target=kill_soon, daemon=True)
        t.start()

    def _show_shortcuts(self, e):
        from core.settings import SettingsManager
        hk_cycle = SettingsManager.get("hotkey_cycle_activation", "Ctrl+Shift+V")
        hk_stop = SettingsManager.get("hotkey_stop_generation", "Ctrl+X")
        is_changed = hk_cycle != "Ctrl+Shift+V" or hk_stop != "Ctrl+X"
        title = "Changed Shortcut Keys" if is_changed else "Keyboard Shortcuts"
        
        dlg = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text(f"Cycle Activation Mode: {hk_cycle}", size=14),
                ft.Text(f"Stop Generation: {hk_stop}", size=14)
            ], tight=True),
            actions=[ft.TextButton("Close", on_click=lambda e: self._close_dlg(dlg))]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _close_dlg(self, dlg):
        dlg.open = False
        self.page.update()


