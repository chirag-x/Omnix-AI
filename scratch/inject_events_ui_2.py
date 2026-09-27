with open(r'e:\Coding\Omnix\ui\app.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    'def _on_voice_command(self, text: str):',
    'def _on_voice_command(self, text: str):\n        event_bus.publish(OmnixEvent(event_type=EventTypes.USER_SPEECH_RECOGNIZED, payload={"text": text}))'
)
open(r'e:\Coding\Omnix\ui\app.py', 'w', encoding='utf-8').write(c)
