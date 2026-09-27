with open(r'e:\Coding\Omnix\ui\tts_player.py', 'r', encoding='utf-8') as f:
    c = f.read()

imports = """
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.embodiment.events import event_bus
from backend.embodiment.models import OmnixEvent, EventTypes
"""
c = c.replace('from utils.logger import log', 'from utils.logger import log' + imports)

c = c.replace(
    'pygame.mixer.music.play()',
    'pygame.mixer.music.play()\n                event_bus.publish(OmnixEvent(event_type=EventTypes.TTS_PLAYBACK_STARTED))'
)

c = c.replace(
    'LAST_TTS_END_TIME = time.time()',
    'LAST_TTS_END_TIME = time.time()\n            event_bus.publish(OmnixEvent(event_type=EventTypes.TTS_PLAYBACK_FINISHED))'
)

open(r'e:\Coding\Omnix\ui\tts_player.py', 'w', encoding='utf-8').write(c)
