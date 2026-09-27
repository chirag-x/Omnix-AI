import asyncio
import json
import re
import threading
import keyboard
from core.settings import SettingsManager
from core.task_control import request_stop, reset, check_cancelled, TaskCancelled
from brain.llm_provider import generate_response
from brain.prompts import get_system_prompt
from skills.registry import execute_skill
from memory.short_term import ShortTermMemory
from senses.speech import generate_audio
from utils.logger import log
from backend.embodiment.events import event_bus
from backend.embodiment.models import OmnixEvent, EventTypes

memory = ShortTermMemory()
_command_lock = threading.Lock()
MAX_ACTIONS = 20
MAX_MODEL_TURNS = 30

# Answers from these tools must be observed before Omnix speaks about the result.
RESULT_REQUIRED_SKILLS = {
    "get_volume", "get_system_info", "get_battery_status", "get_network_info",
    "get_media_info", "get_clipboard", "get_file_info", "is_app_running",
    "list_open_windows", "read_file", "list_directory", "search_files",
    "web_search", "verify_file", "observe", "resolve_known_folder",
    "run_terminal_command", "find_window", "verify_text",
    "click", "right_click", "drag", "click_element", "click_text", "click_visual",
}


def _normalize_actions(response):
    actions = response.get("actions", [])
    if isinstance(actions, dict):
        actions = [actions]
    elif isinstance(actions, str):
        try:
            parsed = json.loads(actions)
            actions = [parsed] if isinstance(parsed, dict) else parsed
        except (TypeError, json.JSONDecodeError):
            actions = []
    if not isinstance(actions, list):
        actions = []
    if not actions and response.get("skill"):
        actions = [{"skill": response["skill"], "args": response.get("args") or {}}]
    return actions


def _extract_literal_content(goal, skill):
    """Preserve text explicitly dictated after 'type' or 'containing'."""
    if skill == "write_to_file":
        pattern = r"\b(?:containing|with\s+(?:the\s+)?text)\s*[:\-]?\s*(.+)$"
    elif skill == "type_text":
        pattern = r"\btype\s*[:\-]?\s+(.+)$"
    else:
        return None
    match = re.search(pattern, goal.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    text = match.group(1).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    return text or None


def _extract_whatsapp_literals(goal):
    """Extract contact/message only from clear, common command forms."""
    value = str(goal or "").strip()
    patterns = [
        # Open chat with Aman and send hi
        (r"\bopen\s+(?:the\s+)?chat\s+(?:of|with)\s+(.+?)\s+(?:and\s+)?send\s+(.+)$", 1, 2),
        # Send a message to Aman saying hi
        (r"\bsend\s+(?:a\s+)?message\s+to\s+(.+?)\s+(?:saying|that\s+says|with\s+(?:the\s+)?text)\s+(.+)$", 1, 2),
        # Send "hi there" to Aman
        (r"\bsend\s+([\"'])(.+?)\1\s+to\s+(.+)$", 3, 2),
        # Send hi to Aman
        (r"\bsend\s+(.+?)\s+to\s+(.+)$", 2, 1),
    ]
    for pattern, contact_group, message_group in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        contact = match.group(contact_group).strip(" \t\r\n.,!?\"'")
        message = match.group(message_group).strip()
        if len(message) >= 2 and message[0] == message[-1] and message[0] in "\"'":
            message = message[1:-1]
        message = message.strip()
        if contact and message:
            return contact, message
    return None

def trigger_abort():
    request_stop()
    log.warning("USER TRIGGERED MANUAL ABORT")

try:
    keyboard.add_hotkey(SettingsManager.get("hotkey_stop_generation", "Ctrl+X") or "Ctrl+X", trigger_abort)
except Exception as exc:
    log.warning(f"Unable to register stop hotkey; the Stop button remains available: {exc}")

async def process_command(user_text: str, on_response):
    """Run one desktop task at a time without resetting another task's state."""
    if not _command_lock.acquire(blocking=False):
        if on_response:
            on_response("I'm still working on your previous request. Stop it or wait before starting another.", "neutral", "")
        return
    try:
        reset()
        event_bus.publish(OmnixEvent(event_type=EventTypes.TASK_STARTED, payload={"command": user_text}))
        await _process_command(user_text, on_response)
        event_bus.publish(OmnixEvent(event_type=EventTypes.TASK_SUCCEEDED, payload={"command": user_text}))
    except TaskCancelled:
        event_bus.publish(OmnixEvent(event_type=EventTypes.TASK_INTERRUPTED))
        log.info("Task stopped by user; remaining actions discarded.")
        if on_response:
            on_response("Task stopped by user.", "neutral", "")
    finally:
        _command_lock.release()


async def _process_command(user_text: str, on_response):
    """
    Process a voice/text command from the user.
    
    Args:
        user_text: The transcribed user command
        on_response: Callable(text, emotion, audio_b64) — updates the UI
    """
    original_goal = user_text
    current_input = f"User Request: {original_goal}"

    # Reset the step counter for this new command (each command gets a fresh 20-step budget)
    # Keep conversation history intact for context, only clear the action tracking
    memory.skill_history = []
    
    use_expert = False

    for _ in range(MAX_MODEL_TURNS):
        check_cancelled()

        # ── Hard cap: never exceed 20 steps on a single task ──────────────────
        if memory.total_steps() >= MAX_ACTIONS:
            log.warning("Hard step cap (20) reached — forcing task completion.")
            audio_b64 = await generate_audio("I couldn't complete that task after many attempts. Please try again with a different approach.")
            check_cancelled()
            if on_response:
                on_response("I reached my action limit without completing the task. Please try again.", "confused", audio_b64)
            break

        memory.add_message("user", current_input)

        event_bus.publish(OmnixEvent(event_type=EventTypes.THINKING_STARTED))
        # 1. Think
        prompt = get_system_prompt()
        response = await asyncio.to_thread(generate_response, prompt, list(memory.get_history()), expert_override=use_expert)
        check_cancelled()
        if not isinstance(response, dict):
            current_input = "SYSTEM WARNING: Return a JSON object with text and an actions array."
            continue
        log.info(f"Brain reasoning: {response.get('thought')}")
        log.info(f"Brain Raw JSON Output: {json.dumps(response, indent=2)}")
        event_bus.publish(OmnixEvent(event_type=EventTypes.THINKING_ENDED))
        emotion = response.get("emotion", "neutral")
        event_bus.publish(OmnixEvent(event_type=EventTypes.EMOTION_CHANGED, payload={"emotion": emotion}))
        memory.add_message("assistant", json.dumps(response))

        # Normalize the plan before speaking. This lets the runtime prevent a
        # model from announcing an answer it has not retrieved yet.
        actions = _normalize_actions(response)
        result_pending = any(
            isinstance(action, dict) and action.get("skill") in RESULT_REQUIRED_SKILLS
            for action in actions
        )

        # 2. Speak (With Silencer Middleware)
        text_to_speak = response.get("text", "") or response.get("response", "") or response.get("message", "") or ""
        if not text_to_speak:
            # Fallback: Check if the text was placed inside the args of a reply or done skill
            act = response.get("actions", [])
            if isinstance(act, dict): act = [act]
            elif isinstance(act, str):
                try: act = json.loads(act)
                except: act = []
            
            if isinstance(act, list) and act:
                for a in act:
                    if isinstance(a, dict) and a.get("skill") in ["reply", "done"]:
                        args = a.get("args", {})
                        if isinstance(args, dict):
                            text_to_speak = args.get("text", "") or args.get("response", "") or args.get("message", "") or ""
                            if text_to_speak: break
                            
        # Also check old 'skill' key at top level
        if not text_to_speak and response.get("skill") in ["reply", "done"]:
            args = response.get("args", {})
            if isinstance(args, dict):
                text_to_speak = args.get("text", "") or args.get("response", "") or args.get("message", "") or ""

        if result_pending and text_to_speak:
            log.info("Deferring speech until result-producing tools return: %s", text_to_speak)
            text_to_speak = ""
        log.info(f"Extracted text_to_speak: {text_to_speak}")
        if text_to_speak and isinstance(text_to_speak, str):
            import re
            # Only silence first-person robotic action narration like:
            # "I am clicking", "I'm typing", "Now pressing", "I will click"
            # This does NOT silence natural speech that happens to contain words like
            # "wait", "type", "play", "click" in conversation.
            _ROBOTIC_PATTERNS = re.compile(
                r"\b("
                r"i(?:'m|\s+am)\s+(?:now\s+)?(?:clicking|typing|pressing|waiting|scrolling|opening|closing|searching|dragging)|"
                r"i\s+(?:will|shall)\s+(?:now\s+)?(?:click|type|press|wait|scroll|open|close|search|drag|clicking|typing|pressing|scrolling)|"
                r"now\s+(?:clicking|typing|pressing|waiting|scrolling|opening|searching)"
                r")\b",
                re.IGNORECASE
            )
            if _ROBOTIC_PATTERNS.search(text_to_speak):
                log.info(f"TTS Silenced (Robotic narration): {text_to_speak}")
                # Still update UI text, just no audio
                if on_response:
                    on_response(text_to_speak, response.get("emotion", "neutral"), "")
            else:
                audio_b64 = await generate_audio(text_to_speak, emotion=response.get("emotion", "neutral"))
                check_cancelled()
                if on_response:
                    on_response(text_to_speak, response.get("emotion", "neutral"), audio_b64)

        # 3. Act
        if not actions:
            if text_to_speak:
                log.info("No actions provided, but agent spoke. Assuming task complete (implicit reply).")
                break
            else:
                log.warning("LLM returned empty actions. Retrying...")
                current_input = "SYSTEM WARNING: You returned no actions. You MUST output a valid 'actions' array."
                continue

        is_done = False
        observations = []
        last_type_index = max(
            (index for index, item in enumerate(actions)
             if isinstance(item, dict) and item.get("skill") == "type_text"),
            default=-1,
        )

        for action_index, action in enumerate(actions):
            check_cancelled()
            if not isinstance(action, dict):
                log.warning(f"LLM hallucinated action format: {action}")
                observations.append(f"SYSTEM WARNING: Malformed action '{action}'. You MUST provide a valid dictionary with 'skill' and 'args'.")
                continue
                
            skill = action.get("skill")
            args = action.get("args") or {}
            if not isinstance(args, dict):
                observations.append("Error: Action arguments must be a JSON object.")
                break

            # ── Failsafe for hallucinated JSON schema (e.g., {"click": {"x": 10}}) ──
            if not skill and len(action) == 1:
                potential_skill = list(action.keys())[0]
                if isinstance(action[potential_skill], dict):
                    skill = potential_skill
                    args = action[potential_skill]
                    log.warning(f"Auto-fixed hallucinated JSON schema: {skill} -> {args}")

            if skill == "done":
                if observations:
                    log.info("Deferred premature 'done' until action results are reviewed.")
                    observations.append(
                        "SYSTEM: Completion was deferred. Review every result above before reporting success."
                    )
                    break
                log.info("Task completed by agent.")
                is_done = True
                break

            if skill == "ask_user":
                if observations:
                    observations.append(
                        "SYSTEM: Review the action results before deciding whether clarification is needed."
                    )
                    break
                question = args.get("question", "")
                log.info(f"Asking user for clarification: {question}")
                if question and question != text_to_speak:
                    audio_b64 = await generate_audio(question)
                    check_cancelled()
                    if on_response:
                        on_response(question, "confused", audio_b64)
                is_done = True
                break
                
            if skill == "reply":
                if observations:
                    observations.append(
                        "SYSTEM: The reply was deferred until the action results are reviewed."
                    )
                    break
                log.info("Agent used reply skill. Treating as task complete.")
                is_done = True
                break
                
            if skill == "handoff_to_expert":
                query = args.get("query", original_goal)
                log.info(f"Handoff to expert requested. Query: {query}")
                use_expert = True
                current_input = f"[SYSTEM_OVERRIDE] The Fast Model handed this task to you (The Expert). Query: {query}"
                observations.append(f"Handed off to expert model: {query}")
                break

            if memory.total_steps() >= MAX_ACTIONS:
                if on_response:
                    on_response("I reached my action limit without completing the task. Please try again.", "confused", "")
                return

            literal = _extract_literal_content(original_goal, skill)
            if literal is not None and (
                skill == "write_to_file" or (skill == "type_text" and action_index == last_type_index)
            ):
                previous = args.get("text")
                if previous != literal:
                    log.info("Preserving dictated text for %s (%d characters).", skill, len(literal))
                    args = {**args, "text": literal}
            if skill == "send_whatsapp_message":
                whatsapp_literals = _extract_whatsapp_literals(original_goal)
                if whatsapp_literals:
                    contact, message = whatsapp_literals
                    if args.get("contact") != contact or args.get("message") != message:
                        log.info(
                            "Preserving explicit WhatsApp recipient '%s' and %d message characters.",
                            contact, len(message),
                        )
                        args = {**args, "contact": contact, "message": message}
            memory.track_skill(skill, args)

            if memory.is_looping():
                log.warning("3-Strike Rule Triggered! Forcing agent to stop.")
                loop_msg = (
                    f"SYSTEM OVERRIDE: You have tried the skill '{skill}' 3 times in a row and it is NOT working. "
                    f"You MUST stop, use the 'done' skill, and tell the user you failed and why."
                )
                observations.append(loop_msg)
                # Inject it into history so the next LLM turn is forced to use 'done'
                memory.add_message("user", loop_msg)
                prompt_str = get_system_prompt()
                response2 = await asyncio.to_thread(generate_response, prompt_str, list(memory.get_history()), expert_override=use_expert)
                check_cancelled()
                text2 = response2.get("text", "I'm stuck and cannot complete this task.") if isinstance(response2, dict) else "I'm stuck and cannot complete this task."
                audio_b64 = await generate_audio(text2)
                check_cancelled()
                if on_response:
                    on_response(text2, "confused", audio_b64)
                is_done = True
                break

            obs = await asyncio.to_thread(execute_skill, skill, args)
            check_cancelled()
            observations.append(obs)
            log.info("Skill result [%s]: %s", skill, str(obs)[:2000])
            
            # HALT ON ERROR: If a skill fails, do not blindly execute the rest of the chain.
            if isinstance(obs, str) and obs.startswith("Error"):
                log.warning(f"Skill '{skill}' returned an Error. Halting action chain.")
                break

            # Results must be read by the next model turn before later actions
            # can depend on them. This prevents observe -> type/send from being
            # executed blindly inside one precomputed action batch.
            if skill in RESULT_REQUIRED_SKILLS and action_index < len(actions) - 1:
                observations.append(
                    "SYSTEM: Remaining actions were deferred at the observation barrier. "
                    "Review this result before choosing the next action."
                )
                log.info(
                    "Observation barrier after '%s'; deferred %d action(s).",
                    skill, len(actions) - action_index - 1,
                )
                break

        if is_done:
            break
            
        # Skip the standard verification format if we just handed off
        if use_expert and observations and "Handed off to expert" in observations[-1]:
            continue

        # 4. Verify (Feed back)
        obs_text = "\n".join(str(observation) for observation in observations)
        current_input = (
            f"Reminder of Original Goal: '{original_goal}'\n"
            f"Observation Results:\n{obs_text}\n"
            "SYSTEM: Base your next response only on these results. Do not claim success without evidence."
        )

        # Anti-Staring Nudge
        if len(memory.skill_history) >= 2 and memory.skill_history[-1] == "observe" and memory.skill_history[-2] == "observe":
            current_input += "\nSYSTEM WARNING: You are staring at the screen. You MUST execute a physical action now OR output the 'done' skill!"
    else:
        if on_response:
            on_response("I couldn't complete the task within my reasoning limit. Please try a smaller request.", "confused", "")

