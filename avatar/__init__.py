from .bridge import AvatarBridge
from .process_manager import avatar_process_manager
import asyncio
import threading
from utils.logger import log

_bridge = None
_loop = None

def start_avatar_system():
    global _bridge, _loop
    if _bridge is None:
        _bridge = AvatarBridge()
        
        def run_bridge():
            global _loop
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
            _loop.run_until_complete(_bridge.start())
            _loop.run_forever()
            
        threading.Thread(target=run_bridge, daemon=True).start()
        log.info("AvatarBridge started in background thread.")
        
    avatar_process_manager.start()

def stop_avatar_system():
    avatar_process_manager.stop()
    if _bridge and _loop:
        asyncio.run_coroutine_threadsafe(_bridge.stop(), _loop)

__all__ = ["AvatarBridge", "avatar_process_manager", "start_avatar_system", "stop_avatar_system"]
