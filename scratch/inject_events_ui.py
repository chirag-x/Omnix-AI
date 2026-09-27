with open(r'e:\Coding\Omnix\ui\app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Booting
c = c.replace(
    'self._set_orb_state(OrbState.LOADING)',
    'event_bus.publish(OmnixEvent(event_type=EventTypes.OMNIX_BOOTING))\n        self._set_orb_state(OrbState.LOADING)'
)

# Ready
c = c.replace(
    'self._set_orb_state(OrbState.SLEEPING)\n        self._add_system_message',
    'event_bus.publish(OmnixEvent(event_type=EventTypes.OMNIX_READY))\n        self._set_orb_state(OrbState.SLEEPING)\n        self._add_system_message'
)

# Wake
c = c.replace(
    'self.is_awake = True',
    'self.is_awake = True\n        event_bus.publish(OmnixEvent(event_type=EventTypes.WAKE_STARTED))\n        event_bus.publish(OmnixEvent(event_type=EventTypes.WOKE))'
)

# Sleep
c = c.replace(
    'def _on_sleep(self):\n        if not self.is_awake:\n            return',
    'def _on_sleep(self):\n        if not self.is_awake:\n            return\n        event_bus.publish(OmnixEvent(event_type=EventTypes.SLEEP_STARTED))\n        event_bus.publish(OmnixEvent(event_type=EventTypes.SLEPT))'
)

# Speech started
c = c.replace(
    'def _on_voice_speech_start(self):',
    'def _on_voice_speech_start(self):\n        event_bus.publish(OmnixEvent(event_type=EventTypes.USER_SPEECH_STARTED))'
)

# Speech ended
c = c.replace(
    'def _on_voice_speech_end(self):',
    'def _on_voice_speech_end(self):\n        event_bus.publish(OmnixEvent(event_type=EventTypes.USER_SPEECH_ENDED))'
)

open(r'e:\Coding\Omnix\ui\app.py', 'w', encoding='utf-8').write(c)
