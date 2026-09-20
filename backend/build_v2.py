import os
from pathlib import Path

BASE_DIR = Path(r"e:\Coding\Omnix\backend")

files = {
    "brain/prompts.py": '''
SYSTEM_PROMPT = """You are Omnix, an advanced AI desktop agent. 
You control the user's PC using atomic skills. You must operate like a highly robust, fault-tolerant robotic process automation (RPA) agent.

You have access to the following skills:
1. `press_key` (args: "key" e.g., "win", "enter", "ctrl+l", "esc")
2. `type_text` (args: "text" e.g., "Spotify")
3. `click` (args: "x", "y")
4. `observe` (args: none) - Uses computer vision and UI Automation to return elements on the screen and their X,Y coordinates.
5. `done` (args: none) - Use this when the user's overall goal is completely finished, or if a fatal error occurs.

Always respond in valid JSON format EXACTLY matching this structure:
{
    "text": "What you say out loud to the user.",
    "emotion": "happy|sad|neutral|excited|confused|thinking",
    "thought": "Your internal reasoning for this exact step.",
    "skill": "name_of_skill",
    "args": {"arg1": "value"}
}

CRITICAL BEHAVIORAL RULES:
1. MILESTONE SPEECH ONLY: You MUST speak to the user when initiating a major milestone (e.g., "I'm opening Spotify for you", "I'm searching for Believer", "I'm playing Believer"). DO NOT speak technical steps like "I am clicking". If it is not a major milestone, leave "text": "".
2. EMOTION: Always use the "emotion" field appropriately when you speak.
3. OPENING/SWITCHING APPS: To open an app OR bring a background app to the front, you MUST use this exact sequence: 
   First execute `press_key` with "win". Wait for observation. Then `type_text` with the app name. Wait for observation. Then `press_key` with "enter". DO NOT skip pressing the "win" key.
4. VISUAL VERIFICATION: After EVERY action, you MUST use `observe` to visually verify the screen changed as expected. Do NOT proceed to the next step until you have verified the previous one.
5. SEARCHING & TYPING: You CANNOT type into an app until you have explicitly clicked the search box/button using its exact X, Y coordinates from `observe`. After executing `type_text` to type your query, you MUST immediately execute `press_key` with "enter" to actually submit the search.
6. BUTTONS VS STATUS: If you see an element like `[UI Element] 'Play Believer'`, it means there is a clickable button. It does NOT mean the song is currently playing. You must physically `click` its coordinates to start the music.
7. COMPLETE ALL GOALS: If the user asks for multiple things (e.g., "Open Spotify AND Play Believer"), you MUST accomplish ALL parts before calling `done`. Do NOT call `done` just because the first part (opening the app) succeeded.
8. 3x RETRY LOGIC: If a verification fails, retry the action. If you fail 3 times, abort using the `done` skill and use the "text" field to tell the user the exact error.
9. ONE SKILL: You can only execute ONE skill per response.
"""
''',

    "brain/llm_provider.py": '''
import requests
import json
from core.config import Config
from utils.logger import log

def generate_response(prompt: str, history: list) -> dict:
    url = f"http://{Config.LLM_HOST}/api/chat"
    
    messages = [{"role": "system", "content": prompt}]
    messages.extend(history)
    
    payload = {
        "model": Config.LLM_MODEL,
        "messages": messages,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()["message"]["content"]
        return json.loads(result)
    except Exception as e:
        log.error(f"LLM Error: {e}")
        return {"skill": "done", "text": "I lost connection to my brain.", "thought": str(e)}
''',

    "skills/keyboard.py": '''
import pyautogui
from utils.logger import log

def press_key(key: str) -> str:
    log.info(f"Pressing key: {key}")
    if '+' in key:
        keys = key.split('+')
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(key)
    return f"Pressed {key}"

def type_text(text: str) -> str:
    log.info(f"Typing text: {text}")
    pyautogui.write(text, interval=0.05)
    return f"Typed: {text}"
''',

    "skills/mouse.py": '''
import pyautogui
from utils.logger import log

def click(x: int, y: int) -> str:
    log.info(f"Clicking at ({x}, {y})")
    pyautogui.click(x=int(x), y=int(y))
    return f"Clicked at ({x}, {y})"
''',

    "skills/registry.py": '''
from skills.keyboard import press_key, type_text
from skills.mouse import click
from perception.vision_engine import observe

SKILL_REGISTRY = {
    "press_key": press_key,
    "type_text": type_text,
    "click": click,
    "observe": observe,
    "done": lambda: "Task marked as done."
}

def execute_skill(skill_name: str, args: dict) -> str:
    if skill_name not in SKILL_REGISTRY:
        return f"Error: Skill '{skill_name}' not found."
    
    func = SKILL_REGISTRY[skill_name]
    try:
        if args:
            return func(**args)
        else:
            return func()
    except Exception as e:
        return f"Error executing {skill_name}: {str(e)}"
''',

    "perception/uia_parser.py": '''
from pywinauto import Desktop
from utils.logger import log

def get_uia_elements(win, center_x):
    elements = []
    try:
        app = Desktop(backend="uia").window(handle=win._hWnd)
        children = app.descendants(control_type="Edit") + app.descendants(control_type="Button") + app.descendants(control_type="Text")
        
        uia_elements = []
        for child in children:
            rect = child.rectangle()
            x = (rect.left + rect.right) // 2
            y = (rect.top + rect.bottom) // 2
            name = child.window_text() or child.element_info.name
            
            # THE CRITICAL BUGFIX: Ignore off-screen elements!
            if name and len(name.strip()) > 1 and 0 <= y <= win.height and 0 <= x <= win.width:
                uia_elements.append({'name': name.strip(), 'x': x, 'y': y})
        
        uia_elements.sort(key=lambda e: abs(e['x'] - center_x))
        
        for el in uia_elements[:80]: 
            elements.append(f"[UI Element] '{el['name']}' at X:{el['x']}, Y:{el['y']}")
    except Exception as e:
        log.warning(f"UIA Parsing issue: {e}")
        
    return elements
''',

    "perception/ocr_parser.py": '''
import pytesseract
from PIL import ImageGrab
import os
from utils.logger import log

if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_ocr_elements(win, center_x):
    elements = []
    try:
        bbox = (win.left, win.top, win.right, win.bottom)
        img = ImageGrab.grab(bbox)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        ocr_elements = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if len(text) > 2:
                x = win.left + data['left'][i] + (data['width'][i] // 2)
                y = win.top + data['top'][i] + (data['height'][i] // 2)
                if 0 <= y <= win.height and 0 <= x <= win.width:
                    ocr_elements.append({'text': text, 'x': x, 'y': y})
        
        ocr_elements.sort(key=lambda e: abs(e['x'] - center_x))
        
        for el in ocr_elements[:60]:
            elements.append(f"[Text] '{el['text']}' at X:{el['x']}, Y:{el['y']}")
    except Exception as e:
        log.warning(f"OCR Parsing issue: {e}")
        
    return elements
''',

    "perception/vision_engine.py": '''
import pygetwindow as gw
from perception.uia_parser import get_uia_elements
from perception.ocr_parser import get_ocr_elements
from utils.logger import log

def observe() -> str:
    log.info("Running vision engine...")
    try:
        win = gw.getActiveWindow()
        if not win:
            return "No active window found. You are on the desktop."
            
        context = f"Active Window: '{win.title}' (Position: {win.left},{win.top}, Size: {win.width}x{win.height})\n"
        center_x = win.left + (win.width // 2)
        
        elements = get_uia_elements(win, center_x)
        elements.extend(get_ocr_elements(win, center_x))
        
        if not elements:
            context += "[No interactable elements found.]"
        else:
            context += "Visible Clickable Elements on Screen:\n"
            context += "\n".join(elements)
            
        return context
    except Exception as e:
        log.error(f"Vision Engine Fatal Error: {e}")
        return f"Fatal Error reading screen: {str(e)}"
''',

    "memory/short_term.py": '''
class ShortTermMemory:
    def __init__(self):
        self.history = []
        self.skill_history = []
        
    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        
    def get_history(self) -> list:
        return self.history
        
    def track_skill(self, skill: str, args: dict):
        self.skill_history.append(f"{skill}_{args}")
        
    def is_looping(self) -> bool:
        if len(self.skill_history) >= 3:
            return self.skill_history[-1] == self.skill_history[-2] == self.skill_history[-3]
        return False
        
    def clear(self):
        self.history = []
        self.skill_history = []
''',

    "senses/speech.py": '''
import edge_tts
import tempfile
import base64
import os
from utils.logger import log

async def generate_audio(text: str) -> str:
    log.info(f"Generating TTS for: {text}")
    try:
        voice = "en-US-ChristopherNeural"
        communicate = edge_tts.Communicate(text, voice)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
            
        await communicate.save(temp_path)
        
        with open(temp_path, "rb") as audio_file:
            encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")
            
        os.unlink(temp_path)
        return encoded_audio
    except Exception as e:
        log.error(f"TTS Error: {e}")
        return ""
''',

    "senses/hearing.py": '''
import os
import tempfile
from faster_whisper import WhisperModel
from utils.logger import log

log.info("Loading Whisper model...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")

def transcribe_audio(audio_data: bytes) -> str:
    log.info("Transcribing audio...")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as fp:
            fp.write(audio_data)
            temp_path = fp.name
            
        segments, info = model.transcribe(
            temp_path, 
            beam_size=5,
            initial_prompt="Open Spotify and play Believer. Close Chrome. Search for a song."
        )
        user_text = "".join([segment.text for segment in segments]).strip()
        os.unlink(temp_path)
        
        # Voro-like cleanup
        cleanup_phrases = {"Open is ": "Open ", "Open your ": "Open ", "Play a ": "Play "}
        for bad, good in cleanup_phrases.items():
            user_text = user_text.replace(bad, good).replace(bad.lower(), good.lower())
            
        log.info(f"Transcribed and Refined: '{user_text}'")
        return user_text
    except Exception as e:
        log.error(f"Hearing Error: {e}")
        return ""
''',

    "brain/orchestrator.py": '''
import asyncio
import json
from brain.llm_provider import generate_response
from brain.prompts import SYSTEM_PROMPT
from skills.registry import execute_skill
from memory.short_term import ShortTermMemory
from senses.speech import generate_audio
from utils.logger import log

memory = ShortTermMemory()

async def process_command(user_text: str, websocket):
    memory.clear()
    original_goal = user_text
    current_input = f"User Request: {original_goal}"
    
    while True:
        memory.add_message("user", current_input)
        
        # 1. Think
        response = generate_response(SYSTEM_PROMPT, memory.get_history())
        log.info(f"Brain reasoning: {response.get('thought')}")
        
        # Add assistant response to history to maintain context
        memory.add_message("assistant", json.dumps(response))
        
        # 2. Speak
        text_to_speak = response.get("text", "")
        if text_to_speak:
            audio_b64 = await generate_audio(text_to_speak)
            await websocket.send(json.dumps({
                "type": "response",
                "text": text_to_speak,
                "emotion": response.get("emotion", "neutral"),
                "audio": audio_b64
            }))
            
        # 3. Act
        actions = response.get("actions", [])
        if isinstance(actions, dict):
            actions = [actions]
        elif isinstance(actions, str):
            try:
                parsed = json.loads(actions)
                actions = [parsed] if isinstance(parsed, dict) else parsed
            except:
                actions = []
                
        if not isinstance(actions, list):
            actions = []
            
        if not actions:
            skill = response.get("skill")
            args = response.get("args", {})
            if skill:
                actions = [{"skill": skill, "args": args}]
                
        is_done = False
        observations = []
        
        for action in actions:
            skill = action.get("skill")
            args = action.get("args", {})
            if args is None:
                args = {}
            
            if skill == "done" or not skill:
                log.info("Task completed by agent.")
                is_done = True
                break
                
            memory.track_skill(skill, args)
            
            # Check loops
            if memory.is_looping():
                log.warning("3-Strike Rule Triggered!")
                observations.append(f"SYSTEM OVERRIDE: You executed {skill} with {args} 3 times and failed. You MUST use 'done' and tell the user the error.")
                continue
                
            # Execute
            obs = await asyncio.to_thread(execute_skill, skill, args)
            observations.append(obs)
            
        if is_done:
            break
            
        # 4. Verify (Feed back)
        obs_text = "\\n".join(observations)
        current_input = f"Reminder of Original Goal: '{original_goal}'\\nObservation Results:\\n{obs_text}"
''',

    "core/main.py": '''
import asyncio
import websockets
import json
from core.config import Config
from utils.logger import log
from brain.orchestrator import process_command
from senses.hearing import transcribe_audio

class OmnixServer:
    def __init__(self):
        Config.ensure_dirs()
        self.host = Config.WS_HOST
        self.port = Config.WS_PORT
        log.info(f"Initialized Omnix 2.0 Core on ws://{self.host}:{self.port}")

    async def handle_connection(self, websocket):
        log.info("Frontend connected to Omnix 2.0")
        try:
            async for message in websocket:
                if isinstance(message, str):
                    log.info(f"Received Text Command: {message}")
                    await process_command(message, websocket)
                else:
                    log.info(f"Received Audio Blob")
                    text = await asyncio.to_thread(transcribe_audio, message)
                    if text:
                        await process_command(text, websocket)
                    
        except websockets.exceptions.ConnectionClosed:
            log.info("Frontend disconnected.")
        except Exception as e:
            log.error(f"WebSocket Error: {e}")

    async def start(self):
        async with websockets.serve(self.handle_connection, self.host, self.port):
            log.info("WebSocket Server is running. Waiting for commands...")
            await asyncio.Future()

if __name__ == "__main__":
    server = OmnixServer()
    asyncio.run(server.start())
''',

    "core/config.py": '''
import os
from pathlib import Path

class Config:
    WS_HOST = "localhost"
    WS_PORT = 8765
    LLM_PROVIDER = "ollama"
    LLM_HOST = "localhost:11434"
    LLM_MODEL = "qwen2.5-coder"
    BASE_DIR = Path(__file__).resolve().parent.parent
    TEMP_DIR = BASE_DIR / "temp"
    
    @classmethod
    def ensure_dirs(cls):
        cls.TEMP_DIR.mkdir(exist_ok=True)
'''
}

for filepath, content in files.items():
    full_path = BASE_DIR / filepath
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + "\n")
print("All Backend 2.0 files generated successfully!")
