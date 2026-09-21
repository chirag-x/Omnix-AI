from skills.keyboard import press_key, type_text, clear_and_type, wait
from skills.mouse import click, right_click, scroll, click_element, find_window, click_text, click_visual
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
    "find_window":   find_window,
    "drag":          drag,
    # ── Vision ─────────────────────────────────────────────────────────────────
    "observe":       observe,
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
    if skill_name not in SKILL_REGISTRY:
        return f"Error: Skill '{skill_name}' not found."
    
    func = SKILL_REGISTRY[skill_name]
    try:
        if args:
            return func(**args)
        else:
            return func()
    except Exception as e:
        return f"Error executing {skill_name}: {str(e)}"
