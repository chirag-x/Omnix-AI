from skills.keyboard import press_key, type_text, clear_and_type, wait
from skills.mouse import click, scroll, click_element, find_window, click_text
from perception.vision_engine import observe
from skills.os_ops import verify_file, write_to_file

from skills.memory import memorize_fact, forget_fact
from skills.advanced_system import run_terminal_command, read_file, list_directory, web_search, search_files, open_file_or_folder

SKILL_REGISTRY = {
    "press_key":     press_key,
    "type_text":     type_text,
    "clear_and_type": clear_and_type,
    "click":         click,
    "scroll":        scroll,
    "click_element": click_element,
    "click_text":    click_text,
    "find_window":   find_window,
    "observe":       observe,
    "verify_file":   verify_file,
    "write_to_file": write_to_file,
    "run_terminal_command": run_terminal_command,
    "read_file":     read_file,
    "list_directory": list_directory,
    "search_files":  search_files,
    "open_file_or_folder": open_file_or_folder,
    "web_search":    web_search,
    "memorize_fact": memorize_fact,
    "forget_fact":   forget_fact,
    "wait":          wait,
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
