import subprocess
import os
import sys
from utils.logger import log
from core.settings import SettingsManager

class AvatarProcessManager:
    def __init__(self):
        self.process = None

    def is_running(self):
        if self.process is None:
            return False
        return self.process.poll() is None

    def start(self):
        if self.is_running():
            log.info("Avatar renderer is already running.")
            return

        if not SettingsManager.get("avatar_enabled", True):
            log.info("Avatar renderer is disabled in settings.")
            return

        log.info("Starting Avatar renderer process...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        host_script = os.path.join(current_dir, "host.py")
        
        args = [sys.executable, host_script]
        
        if SettingsManager.get("avatar_click_through", False):
            args.append("--click-through")
            
        scale = SettingsManager.get("avatar_scale", 1.0)
        args.extend(["--scale", str(scale)])

        # CREATE_NO_WINDOW = 0x08000000
        creationflags = 0x08000000 if os.name == 'nt' else 0

        self.process = subprocess.Popen(
            args, 
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        log.info(f"Avatar renderer started with PID {self.process.pid}")

    def stop(self):
        if self.is_running():
            log.info("Stopping Avatar renderer process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            log.info("Avatar renderer stopped.")

avatar_process_manager = AvatarProcessManager()

import atexit
atexit.register(avatar_process_manager.stop)
