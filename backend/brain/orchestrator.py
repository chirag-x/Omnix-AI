import asyncio
import json
import keyboard
from brain.llm_provider import generate_response
from brain.prompts import SYSTEM_PROMPT
from skills.registry import execute_skill
from memory.short_term import ShortTermMemory
from senses.speech import generate_audio
from utils.logger import log

memory = ShortTermMemory()
ABORT_FLAG = False

def trigger_abort():
    global ABORT_FLAG
    ABORT_FLAG = True
    log.warning("USER TRIGGERED MANUAL ABORT (CTRL+X)")

keyboard.add_hotkey('ctrl+x', trigger_abort)

async def process_command(user_text: str, on_response):
    """
    Process a voice/text command from the user.
    
    Args:
        user_text: The transcribed user command
        on_response: Callable(text, emotion, audio_b64) — updates the UI
    """
    global ABORT_FLAG
    ABORT_FLAG = False

    original_goal = user_text
    current_input = f"User Request: {original_goal}"

    # Reset the step counter for this new command (each command gets a fresh 20-step budget)
    # Keep conversation history intact for context, only clear the action tracking
    memory.skill_history = []

    while True:
        if ABORT_FLAG:
            log.warning("Aborting loop immediately due to user interruption.")
            if on_response:
                on_response("Task aborted by user.", "sad", "")
            break

        # ── Hard cap: never exceed 20 steps on a single task ──────────────────
        if memory.total_steps() > 20:
            log.warning("Hard step cap (20) reached — forcing task completion.")
            audio_b64 = await generate_audio("I couldn't complete that task after many attempts. Please try again with a different approach.")
            if on_response:
                on_response("I reached my action limit without completing the task. Please try again.", "confused", audio_b64)
            break

        memory.add_message("user", current_input)

        # 1. Think
        response = generate_response(SYSTEM_PROMPT, memory.get_history())
        log.info(f"Brain reasoning: {response.get('thought')}")
        log.info(f"Brain Raw JSON Output: {json.dumps(response, indent=2)}")
        memory.add_message("assistant", json.dumps(response))

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

        log.info(f"Extracted text_to_speak: {text_to_speak}")
        if text_to_speak and isinstance(text_to_speak, str):
            forbidden_words = ["type", "typing", "press", "pressing", "click", "clicking", "wait", "waiting"]
            if any(word in text_to_speak.lower() for word in forbidden_words):
                log.info(f"TTS Silenced (Technical/Chatty): {text_to_speak}")
                # Still update UI text, just no audio
                if on_response:
                    on_response(text_to_speak, response.get("emotion", "neutral"), "")
            else:
                audio_b64 = await generate_audio(text_to_speak)
                if on_response:
                    on_response(text_to_speak, response.get("emotion", "neutral"), audio_b64)

        # 3. Act
        actions = response.get("actions", [])
        
        # Robustness: LLM might return a single dict instead of a list
        if isinstance(actions, dict):
            actions = [actions]
        # LLM might return a stringified JSON
        elif isinstance(actions, str):
            try:
                parsed = json.loads(actions)
                actions = [parsed] if isinstance(parsed, dict) else parsed
            except:
                actions = []
                
        if not isinstance(actions, list):
            actions = []
            
        if not actions:
            old_skill = response.get("skill")
            if old_skill:
                actions = [{"skill": old_skill, "args": response.get("args", {})}]

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

        for action in actions:
            if not isinstance(action, dict):
                log.warning(f"LLM hallucinated action format: {action}")
                observations.append(f"SYSTEM WARNING: Malformed action '{action}'. You MUST provide a valid dictionary with 'skill' and 'args'.")
                continue
                
            skill = action.get("skill")
            args = action.get("args", {})

            if skill == "done":
                log.info("Task completed by agent.")
                is_done = True
                break

            if skill == "ask_user":
                question = args.get("question", "")
                log.info(f"Asking user for clarification: {question}")
                is_done = True
                break
                
            if skill == "reply":
                log.info("Agent used reply skill. Treating as task complete.")
                is_done = True
                break

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
                response2 = generate_response(SYSTEM_PROMPT, memory.get_history())
                text2 = response2.get("text", "I'm stuck and cannot complete this task.")
                audio_b64 = await generate_audio(text2)
                if on_response:
                    on_response(text2, "confused", audio_b64)
                is_done = True
                break

            obs = await asyncio.to_thread(execute_skill, skill, args)
            observations.append(obs)

        if is_done:
            break

        # 4. Verify (Feed back)
        obs_text = "\n".join(observations)
        current_input = f"Reminder of Original Goal: '{original_goal}'\nObservation Results:\n{obs_text}"

        # Anti-Staring Nudge
        if len(memory.skill_history) >= 2 and memory.skill_history[-1] == "observe" and memory.skill_history[-2] == "observe":
            current_input += "\nSYSTEM WARNING: You are staring at the screen. You MUST execute a physical action now OR output the 'done' skill!"

