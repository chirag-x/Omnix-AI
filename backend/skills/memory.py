import os
import json
from utils.logger import log
from core.settings import SettingsManager

def _get_memory_file():
    # Store memory in the root project folder so it is highly visible to the user
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base, "user_memory.json")

def get_all_memories() -> list[str]:
    mem_file = _get_memory_file()
    if not os.path.exists(mem_file):
        return []
    try:
        with open(mem_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to read memory: {e}")
        return []

def memorize_fact(fact: str) -> str:
    """Saves a fact to the user's long-term memory."""
    mem_file = _get_memory_file()
    memories = get_all_memories()
    if fact not in memories:
        memories.append(fact)
        try:
            with open(mem_file, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=4)
            log.info(f"Memorized fact: {fact}")
            return f"Successfully memorized: {fact}"
        except Exception as e:
            log.error(f"Failed to write memory: {e}")
            return f"Error saving memory: {e}"
    return "Fact is already in memory."

def forget_fact(fact: str) -> str:
    """Removes a fact from the user's long-term memory."""
    mem_file = _get_memory_file()
    memories = get_all_memories()
    if fact in memories:
        memories.remove(fact)
        try:
            with open(mem_file, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=4)
            log.info(f"Forgot fact: {fact}")
            return f"Successfully forgot: {fact}"
        except Exception as e:
            log.error(f"Failed to write memory: {e}")
            return f"Error updating memory: {e}"
    return "Fact not found in memory."
