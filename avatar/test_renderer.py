import sys
import os
import asyncio
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.embodiment.events import event_bus
from backend.embodiment.models import OmnixEvent, EventTypes
from avatar import start_avatar_system, stop_avatar_system

def test():
    start_avatar_system()
    print("Started avatar system.")
    time.sleep(3)
    
    print("Setting awake/idle...")
    event_bus.publish(OmnixEvent(EventTypes.WOKE))
    event_bus.publish(OmnixEvent(EventTypes.OMNIX_READY))
    time.sleep(2)
    
    print("Setting listening...")
    event_bus.publish(OmnixEvent(EventTypes.USER_SPEECH_STARTED))
    time.sleep(2)
    
    print("Setting thinking...")
    event_bus.publish(OmnixEvent(EventTypes.THINKING_STARTED))
    time.sleep(2)
    
    print("Setting speaking with happy emotion...")
    event_bus.publish(OmnixEvent(EventTypes.EMOTION_CHANGED, payload={"emotion": "happy"}))
    event_bus.publish(OmnixEvent(EventTypes.TTS_PLAYBACK_STARTED))
    time.sleep(4)
    
    print("Setting silent and sleeping...")
    event_bus.publish(OmnixEvent(EventTypes.TTS_PLAYBACK_FINISHED))
    event_bus.publish(OmnixEvent(EventTypes.SLEPT))
    time.sleep(2)
    
    stop_avatar_system()
    print("Done")

if __name__ == "__main__":
    test()
