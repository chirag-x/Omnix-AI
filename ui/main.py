import sys
import os

# Add ui dir itself to path so siblings like wake_engine, audio_recorder etc. are importable
sys.path.insert(0, os.path.dirname(__file__))

import flet as ft
from app import OmnixApp

def main(page: ft.Page):
    OmnixApp(page)

if __name__ == "__main__":
    ft.run(main)
