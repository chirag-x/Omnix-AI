"""
Phase 8 — System Intelligence Skills
Gives Omnix real-time system awareness: CPU, RAM, disk, battery, WiFi,
volume control, process management, notifications, and app launching.
"""
import os
import subprocess
from utils.logger import log


# ──────────────────────────────────────────────────────────────────────────────
# URL / BROWSER
# ──────────────────────────────────────────────────────────────────────────────

def open_url(url: str) -> str:
    """
    Open a URL directly in the user's default browser — no Start Menu, no typing.
    Also works with URI schemes: whatsapp://, spotify:, mailto:, ms-settings:, etc.

    Args:
        url: The full URL or URI to open. Examples:
             "https://gmail.com"
             "https://wa.me/919876543210"  ← opens WhatsApp chat with that number
             "spotify:search:Believer"
             "ms-settings:network-wifi"

    Returns:
        Success or error message.
    """
    log.info(f"Opening URL: {url}")
    try:
        import webbrowser
        webbrowser.open(url)
        return f"Opened in browser: {url}"
    except Exception as e:
        log.error(f"open_url error: {e}")
        return f"Error opening URL: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# DRAG & DROP
# ──────────────────────────────────────────────────────────────────────────────

def drag(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.4) -> str:
    """
    Click-hold at one position and drag to another, then release.
    Use for: moving files in Explorer, using sliders, scrollbars,
    timeline scrubbers in video editors, resizing windows manually.

    Args:
        from_x, from_y: Starting coordinates (where to click and hold).
        to_x, to_y: Ending coordinates (where to release).
        duration: How many seconds the drag takes (default 0.4s for smooth motion).

    Returns:
        Success message.
    """
    log.info(f"Dragging ({from_x},{from_y}) → ({to_x},{to_y})")
    try:
        import pyautogui
        pyautogui.moveTo(int(from_x), int(from_y), duration=0.15)
        pyautogui.mouseDown()
        pyautogui.moveTo(int(to_x), int(to_y), duration=float(duration))
        pyautogui.mouseUp()
        return f"Dragged from ({from_x},{from_y}) to ({to_x},{to_y})"
    except Exception as e:
        log.error(f"drag error: {e}")
        return f"Error dragging: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# VOLUME
# ──────────────────────────────────────────────────────────────────────────────

def get_volume() -> str:
    """
    Get the current system master volume level (0–100).

    Returns:
        A string like "Current volume: 65" or an error.
    """
    log.info("Getting system volume")
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        level = round(volume.GetMasterVolumeLevelScalar() * 100)
        muted = volume.GetMute()
        status = f"Current volume: {level}%"
        if muted:
            status += " (MUTED)"
        return status
    except ImportError:
        # pycaw not installed, use PowerShell fallback
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-AudioDevice -Playback).Volume"],
                capture_output=True, text=True, timeout=5
            )
            v = result.stdout.strip()
            return f"Current volume: {v}%" if v else "Unable to read volume (AudioDeviceCmdlets not installed)"
        except Exception as e2:
            return f"Error reading volume: {e2}"
    except Exception as e:
        log.error(f"get_volume error: {e}")
        return f"Error getting volume: {e}"


def set_volume(level: int) -> str:
    """
    Set the system master volume to an exact level from 0 to 100.
    Use this instead of volumeup/volumedown when the user specifies an exact number.

    Args:
        level: Integer from 0 (mute) to 100 (max). E.g., set_volume(50) for half volume.

    Returns:
        Confirmation or error.
    """
    level = max(0, min(100, int(level)))
    log.info(f"Setting volume to {level}%")
    try:
        # Dependency-free Windows native volume control using embedded C#
        ps_script = f"""
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute(bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{
    int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject {{}}
public class Audio {{
    public static void SetVolume(float level, bool mute) {{
        IMMDeviceEnumerator enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        IAudioEndpointVolume vol = null;
        System.Guid iid = typeof(IAudioEndpointVolume).GUID;
        dev.Activate(ref iid, 23, 0, out vol);
        vol.SetMasterVolumeLevelScalar(level, System.Guid.Empty);
        vol.SetMute(mute, System.Guid.Empty);
    }}
}}
'@
[Audio]::SetVolume({level / 100.0}, ${'true' if level == 0 else 'false'})
"""
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=5)
        return f"Volume set to {level}%"
    except Exception as e:
        log.error(f"set_volume error: {e}")
        return f"Error setting volume to {level}%: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM INFORMATION
# ──────────────────────────────────────────────────────────────────────────────

def get_system_info() -> str:
    """
    Get real-time system resource usage: CPU%, RAM, disk space, and uptime.
    Use when the user asks 'how is my PC doing?', 'is my RAM full?', etc.

    Returns:
        A formatted summary of system resources.
    """
    log.info("Getting system info")
    try:
        import psutil
        import datetime

        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        uptime_s = (datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())).seconds
        uptime_h = uptime_s // 3600
        uptime_m = (uptime_s % 3600) // 60

        ram_used = ram.used / (1024 ** 3)
        ram_total = ram.total / (1024 ** 3)
        disk_used = disk.used / (1024 ** 3)
        disk_total = disk.total / (1024 ** 3)

        return (
            f"System Status:\n"
            f"  CPU Usage: {cpu}%\n"
            f"  RAM: {ram_used:.1f} GB used / {ram_total:.1f} GB total ({ram.percent}% used)\n"
            f"  Disk (C:): {disk_used:.1f} GB used / {disk_total:.1f} GB total ({disk.percent}% used)\n"
            f"  Uptime: {uptime_h}h {uptime_m}m"
        )
    except ImportError:
        return "Error: psutil not installed. Run: pip install psutil"
    except Exception as e:
        log.error(f"get_system_info error: {e}")
        return f"Error getting system info: {e}"


def get_battery_status() -> str:
    """
    Get the current battery level and charging status.
    Use when the user asks 'how's my battery?', 'is my laptop charging?', etc.

    Returns:
        Battery percentage and charging status, or a message if no battery detected.
    """
    log.info("Getting battery status")
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            return "No battery detected — this may be a desktop PC or battery info is unavailable."
        pct = round(battery.percent)
        charging = battery.power_plugged
        secs_left = battery.secsleft

        status = f"Battery: {pct}% — {'Charging 🔌' if charging else 'On Battery 🔋'}"
        if not charging and secs_left > 0 and secs_left != psutil.POWER_TIME_UNLIMITED:
            h = secs_left // 3600
            m = (secs_left % 3600) // 60
            status += f" — ~{h}h {m}m remaining"
        return status
    except ImportError:
        return "Error: psutil not installed."
    except Exception as e:
        log.error(f"get_battery_status error: {e}")
        return f"Error getting battery: {e}"


def get_network_info() -> str:
    """
    Get current network information: WiFi name, local IP, and connection status.
    Use when the user asks 'what WiFi am I on?', 'what's my IP?', 'am I connected?'

    Returns:
        Network summary string.
    """
    log.info("Getting network info")
    try:
        import psutil
        import socket

        # Get local IP
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "Unknown"

        # Get WiFi SSID via netsh
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=5
            )
            ssid = "Not connected to WiFi"
            for line in result.stdout.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    ssid = line.split(":", 1)[-1].strip()
                    break
        except Exception:
            ssid = "Unable to read WiFi name"

        # Check internet
        try:
            import urllib.request
            urllib.request.urlopen("http://www.google.com", timeout=3)
            internet = "Connected ✅"
        except Exception:
            internet = "No internet ❌"

        return (
            f"Network Info:\n"
            f"  WiFi: {ssid}\n"
            f"  Local IP: {local_ip}\n"
            f"  Internet: {internet}"
        )
    except Exception as e:
        log.error(f"get_network_info error: {e}")
        return f"Error getting network info: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# PROCESS MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

def kill_process(name: str) -> str:
    """
    Force-terminate a running process by its name or partial name.
    Use when an app is frozen and the user wants to kill it without clicking.
    E.g., kill_process("chrome") kills all Chrome processes.

    Args:
        name: Process name or partial name (e.g., "chrome", "spotify", "notepad").

    Returns:
        How many processes were killed, or an error.
    """
    log.warning(f"Killing process: '{name}'")
    try:
        import psutil
        killed = 0
        name_lower = name.lower().replace(".exe", "")

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower().replace(".exe", "")
                if name_lower in proc_name:
                    proc.kill()
                    killed += 1
                    log.warning(f"Killed PID {proc.info['pid']} ({proc.info['name']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if killed == 0:
            return f"No running process found matching '{name}'. Is it running?"
        return f"Killed {killed} process(es) matching '{name}'."
    except ImportError:
        return "Error: psutil not installed."
    except Exception as e:
        log.error(f"kill_process error: {e}")
        return f"Error killing process '{name}': {e}"


def is_app_running(name: str) -> str:
    """
    Check if a specific application is currently running.
    Use this BEFORE trying to snap, focus, or interact with an app
    to avoid errors when the app is not open.

    Args:
        name: App name or process name (e.g., "spotify", "chrome", "notepad").

    Returns:
        "Running" or "Not running" with the PID if found.
    """
    log.info(f"Checking if '{name}' is running")
    try:
        import psutil
        name_lower = name.lower().replace(".exe", "")
        matches = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pn = proc.info['name'].lower().replace(".exe", "")
                if name_lower in pn:
                    matches.append(f"{proc.info['name']} (PID {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if matches:
            return f"Running: {', '.join(matches[:3])}"
        return f"Not running: No process found matching '{name}'"
    except ImportError:
        return "Error: psutil not installed."
    except Exception as e:
        return f"Error checking process: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS
# ──────────────────────────────────────────────────────────────────────────────

def show_notification(title: str, message: str) -> str:
    """
    Display a Windows 11 toast notification in the bottom-right corner of the screen.
    Use this when a background task finishes (download complete, reminder fired, etc.)
    or when the user is not looking at the Omnix window.

    Args:
        title: The bold title line of the notification.
        message: The body text of the notification.

    Returns:
        Success or error.
    """
    log.info(f"Showing notification: [{title}] {message}")
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            duration=6,
            threaded=True
        )
        return f"Notification shown: '{title}'"
    except ImportError:
        # Fallback: PowerShell BalloonTip
        try:
            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(5000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -s 5
$n.Dispose()
"""
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return f"Notification shown: '{title}' (via PowerShell)"
        except Exception as e2:
            return f"Error showing notification: {e2}"
    except Exception as e:
        log.error(f"show_notification error: {e}")
        return f"Error showing notification: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# APP LAUNCHER
# ──────────────────────────────────────────────────────────────────────────────

def launch_app(path_or_name: str) -> str:
    """
    Launch an application by its executable path or registered app name.
    More reliable than Start Menu searching for apps with known paths.

    Args:
        path_or_name: Full path to an executable, OR a registered app name
                      (e.g., "notepad", "calc", "mspaint", "explorer",
                      "C:\\Program Files\\Spotify\\Spotify.exe")

    Returns:
        Success or error message.
    """
    log.info(f"Launching app: '{path_or_name}'")
    try:
        expanded = os.path.expanduser(path_or_name)
        if os.path.exists(expanded):
            subprocess.Popen([expanded])
            return f"Launched: {expanded}"
        else:
            # Try as a registered Windows app name
            subprocess.Popen(path_or_name, shell=True)
            return f"Launched: {path_or_name}"
    except Exception as e:
        log.error(f"launch_app error: {e}")
        return f"Error launching '{path_or_name}': {e}"


# ──────────────────────────────────────────────────────────────────────────────
# MEDIA INFO
# ──────────────────────────────────────────────────────────────────────────────

def get_media_info() -> str:
    """
    Get what's currently playing on this PC using the Windows Media Session API.
    Works with Spotify, YouTube in Chrome, Windows Media Player, and any app
    that registers with the Windows media transport controls.

    Returns:
        Currently playing song/video title and artist, or 'Nothing playing'.
    """
    log.info("Getting media info from Windows Media Session")
    try:
        # Use winrt (Windows Runtime) to query media session
        import winrt.windows.media.control as wmc
        import asyncio

        async def _get():
            manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = manager.get_current_session()
            if not session:
                return None
            info = await session.try_get_media_properties_async()
            return info

        loop = asyncio.new_event_loop()
        info = loop.run_until_complete(_get())
        loop.close()

        if info:
            title = info.title or "Unknown title"
            artist = info.artist or "Unknown artist"
            return f"Now playing: '{title}' by {artist}"
        return "Nothing is currently playing."

    except ImportError:
        # Fallback: read Spotify window title (it shows song - artist)
        try:
            import pygetwindow as gw
            for win in gw.getAllWindows():
                if "Spotify" in (win.title or ""):
                    t = win.title.strip()
                    if t and t != "Spotify":
                        return f"Now playing (Spotify): {t}"
            return "Nothing is currently playing (or Spotify is not open)."
        except Exception as e2:
            return f"Media info unavailable: {e2}"
    except Exception as e:
        log.error(f"get_media_info error: {e}")
        return f"Error getting media info: {e}"
