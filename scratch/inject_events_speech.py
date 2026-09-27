with open(r'e:\Coding\Omnix\backend\senses\speech.py', 'r', encoding='utf-8') as f:
    c = f.read()

imports = """
from backend.embodiment.events import event_bus
from backend.embodiment.models import OmnixEvent, EventTypes
"""
c = c.replace('from utils.logger import log', 'from utils.logger import log' + imports)

c = c.replace(
    'if not text or not text.strip():\n        return ""',
    'if not text or not text.strip():\n        return ""\n    event_bus.publish(OmnixEvent(event_type=EventTypes.TTS_GENERATION_STARTED))'
)

c = c.replace(
    'if audio_mode == "Natural":\n        return await asyncio.to_thread(_generate_kokoro_sync, text, emotion)',
    'if audio_mode == "Natural":\n        res = await asyncio.to_thread(_generate_kokoro_sync, text, emotion)\n        event_bus.publish(OmnixEvent(event_type=EventTypes.TTS_GENERATION_COMPLETED))\n        return res'
)

c = c.replace(
    'return await _generate_edge_tts(text, voice)',
    'res = await _generate_edge_tts(text, voice)\n        event_bus.publish(OmnixEvent(event_type=EventTypes.TTS_GENERATION_COMPLETED))\n        return res'
)

open(r'e:\Coding\Omnix\backend\senses\speech.py', 'w', encoding='utf-8').write(c)
