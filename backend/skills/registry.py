from skills.keyboard import press_key, type_text, clear_and_type
from skills.mouse import click, scroll, click_element, find_window, click_text
from perception.vision_engine import observe
from skills.os_ops import verify_file, write_to_file

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
