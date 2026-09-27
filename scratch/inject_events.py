import json

with open(r'e:\Coding\Omnix\backend\brain\orchestrator.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Add TASK_STARTED and SUCCEEDED
c = c.replace(
    'reset()\n        await _process_command(user_text, on_response)',
    'reset()\n        event_bus.publish(OmnixEvent(event_type=EventTypes.TASK_STARTED, payload={"command": user_text}))\n        await _process_command(user_text, on_response)\n        event_bus.publish(OmnixEvent(event_type=EventTypes.TASK_SUCCEEDED, payload={"command": user_text}))'
)

# Add TASK_INTERRUPTED
c = c.replace(
    'except TaskCancelled:\n        log.info("Task stopped by user',
    'except TaskCancelled:\n        event_bus.publish(OmnixEvent(event_type=EventTypes.TASK_INTERRUPTED))\n        log.info("Task stopped by user'
)

# Emit THINKING_STARTED
c = c.replace(
    'memory.add_message("user", current_input)\n\n        # 1. Think',
    'memory.add_message("user", current_input)\n\n        event_bus.publish(OmnixEvent(event_type=EventTypes.THINKING_STARTED))\n        # 1. Think'
)

# Emit THINKING_ENDED and EMOTION_CHANGED
c = c.replace(
    'log.info(f"Brain Raw JSON Output: {json.dumps(response, indent=2)}")',
    'log.info(f"Brain Raw JSON Output: {json.dumps(response, indent=2)}")\n        event_bus.publish(OmnixEvent(event_type=EventTypes.THINKING_ENDED))\n        emotion = response.get("emotion", "neutral")\n        event_bus.publish(OmnixEvent(event_type=EventTypes.EMOTION_CHANGED, payload={"emotion": emotion}))'
)

open(r'e:\Coding\Omnix\backend\brain\orchestrator.py', 'w', encoding='utf-8').write(c)
