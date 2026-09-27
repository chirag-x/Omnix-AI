import sys
import os

# Add root, backend, and ui directories to Python path
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))
sys.path.insert(0, os.path.join(project_root, 'ui'))

from backend.core.runtime import omnix_runtime

def main():
    # Initialize Core Backend Services (Brain, Voice, Avatar, Tray, EventBus)
    omnix_runtime.initialize()
    
    # We optionally start the Flet UI in the main thread 
    # (Flet requires main thread on MacOS/Windows sometimes)
    import flet as ft
    from ui.app import OmnixApp
    
    def start_ui(page: ft.Page):
        OmnixApp(page)
    
    try:
        # Flet blocks the main thread here
        ft.run(start_ui)
    except KeyboardInterrupt:
        pass
    finally:
        # Flet window closed (i.e. 'Quit' via Tray, or forced shutdown)
        omnix_runtime.shutdown()

if __name__ == "__main__":
    main()
