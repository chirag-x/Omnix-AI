# DEPRECATED: Use the root main.py instead. (python main.py)
import sys
import os

# Add ui dir itself to path so siblings like wake_engine, audio_recorder etc. are importable
sys.path.insert(0, os.path.dirname(__file__))
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import flet as ft
from app import OmnixApp

def main(page: ft.Page):
    OmnixApp(page)

if __name__ == "__main__":
    ft.run(main)
