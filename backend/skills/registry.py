from skills.keyboard import press_key, type_text, clear_and_type, wait
from core.task_control import check_cancelled, TaskCancelled
from skills.mouse import click, right_click, scroll, click_element, find_window, click_text, click_visual, verify_text
from skills.messaging import open_whatsapp_chat, send_whatsapp_message
from perception.vision_engine import observe
from skills.os_ops import verify_file, write_to_file

from skills.memory import memorize_fact, forget_fact
from skills.advanced_system import run_terminal_command, read_file, list_directory, web_search, search_files, open_file_or_folder
from skills.windows import (
    snap_window, minimize_window, minimize_all_windows, restore_all_windows,
    maximize_window, close_window, list_open_windows, system_power
)
# ── Phase 8 ────────────────────────────────────────────────────────────────────
from skills.clipboard import get_clipboard, set_clipboard
from skills.file_ops import copy_file, move_file, delete_file, create_folder, get_file_info, download_file
from core.known_folders import resolve_known_folder
from skills.system_intel import (
    open_url, drag,
    get_volume, set_volume,
    get_system_info, get_battery_status, get_network_info,
    kill_process, is_app_running,
    show_notification, launch_app, get_media_info
)

SKILL_REGISTRY = {
    # ── Input ──────────────────────────────────────────────────────────────────
    "press_key":     press_key,
    "type_text":     type_text,
    "clear_and_type": clear_and_type,
    "click":         click,
    "right_click":   right_click,
    "scroll":        scroll,
    "click_element": click_element,
    "click_text":    click_text,
    "click_visual":  click_visual,
    "verify_text":   verify_text,
    "find_window":   find_window,
    "drag":          drag,
    # ── Vision ─────────────────────────────────────────────────────────────────
    "observe":       observe,
    "open_whatsapp_chat": open_whatsapp_chat,
    "send_whatsapp_message": send_whatsapp_message,
    # ── File System ────────────────────────────────────────────────────────────
    "verify_file":          verify_file,
    "write_to_file":        write_to_file,
    "read_file":            read_file,
    "list_directory":       list_directory,
    "search_files":         search_files,
    "open_file_or_folder":  open_file_or_folder,
    "copy_file":            copy_file,
    "move_file":            move_file,
    "delete_file":          delete_file,
    "create_folder":        create_folder,
    "get_file_info":        get_file_info,
    "download_file":        download_file,
    "resolve_known_folder": resolve_known_folder,
    # ── Web & Network ──────────────────────────────────────────────────────────
    "web_search":       web_search,
    "open_url":         open_url,
    "get_network_info": get_network_info,
    # ── Clipboard ──────────────────────────────────────────────────────────────
    "get_clipboard":  get_clipboard,
    "set_clipboard":  set_clipboard,
    # ── System Intel ───────────────────────────────────────────────────────────
    "get_system_info":    get_system_info,
    "get_battery_status": get_battery_status,
    "get_volume":         get_volume,
    "set_volume":         set_volume,
    "get_media_info":     get_media_info,
    "kill_process":       kill_process,
    "is_app_running":     is_app_running,
    "show_notification":  show_notification,
    "launch_app":         launch_app,
    # ── System Commands ────────────────────────────────────────────────────────
    "run_terminal_command": run_terminal_command,
    # ── Memory ─────────────────────────────────────────────────────────────────
    "memorize_fact":  memorize_fact,
    "forget_fact":    forget_fact,
    # ── Window Management ──────────────────────────────────────────────────────
    "snap_window":          snap_window,
    "minimize_window":      minimize_window,
    "minimize_all_windows": minimize_all_windows,
    "restore_all_windows":  restore_all_windows,
    "maximize_window":      maximize_window,
    "close_window":         close_window,
    "list_open_windows":    list_open_windows,
    # ── Power ──────────────────────────────────────────────────────────────────
    "system_power":         system_power,
    # ── Timing ─────────────────────────────────────────────────────────────────
    "wait":          wait,
    # ── Meta ───────────────────────────────────────────────────────────────────
    "handoff_to_expert": lambda query, reasoning="": f"Handed off to expert model: {query}",
    "ask_user": lambda question="": f"Asked user: {question}. Waiting for voice response.",
    "reply":    lambda: "Responded to user.",
    "done":     lambda: "Task marked as done."
}


def execute_skill(skill_name: str, args: dict) -> str:
    check_cancelled()
    if not isinstance(skill_name, str):
        return "Error: Skill name must be a string."
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return "Error: Skill arguments must be an object."
    if skill_name not in SKILL_REGISTRY:
        return f"Error: Skill '{skill_name}' not found."
    
    func = SKILL_REGISTRY[skill_name]
    try:
        if args:
            return func(**args)
        else:
            return func()
    except TaskCancelled:
        raise
    except Exception as e:
        return f"Error executing {skill_name}: {str(e)}"
