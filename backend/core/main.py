import asyncio
import websockets
import json
import socket
import subprocess
import time
from core.config import Config
from utils.logger import log
from brain.orchestrator import process_command
from senses.hearing import transcribe_audio

def ensure_omniroute_running():
    omni_host = "127.0.0.1"
    omni_port = 20128
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        result = s.connect_ex((omni_host, omni_port))
        
    if result != 0:
        log.warning("OmniRoute is NOT running on port 20128. Auto-starting it in a new terminal...")
        # Open a new cmd window and run omniroute
        subprocess.Popen("start cmd /k omniroute", shell=True)
        log.info("Waiting 3 seconds for OmniRoute to initialize...")
        time.sleep(3)
    else:
        log.info("OmniRoute is already running. Brain connection is healthy.")

class OmnixServer:
    def __init__(self):
        Config.ensure_dirs()
        ensure_omniroute_running()
        self.host = Config.WS_HOST
        self.port = Config.WS_PORT
        self.active_websocket = None
        log.info(f"Initialized Omnix 2.0 Core on ws://{self.host}:{self.port}")

    async def handle_connection(self, websocket):
        log.info("Frontend connected to Omnix 2.0")
        self.active_websocket = websocket
        try:
            async for message in websocket:
                if isinstance(message, str):
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "text":
                            command = data.get("command", "")
                            log.info(f"Received Text Command: {command}")
                            await process_command(command, websocket)
                            
                        elif msg_type == "audio":
                            import base64
                            audio_b64 = data.get("data", "")
                            if audio_b64:
                                log.info("Received Audio Blob, decoding...")
                                audio_bytes = base64.b64decode(audio_b64)
                                text = await asyncio.to_thread(transcribe_audio, audio_bytes)
                                if text:
                                    await process_command(text, websocket)
                        else:
                            log.warning(f"Unknown message type: {msg_type}")
                    except json.JSONDecodeError:
                        # Fallback for plain text
                        log.info(f"Received raw text: {message}")
                        await process_command(message, websocket)
                else:
                    log.info(f"Received raw binary message.")
                    text = await asyncio.to_thread(transcribe_audio, message)
                    if text:
                        await process_command(text, websocket)
                    
        except websockets.exceptions.ConnectionClosed:
            log.info("Frontend disconnected.")
            self.active_websocket = None
        except Exception as e:
            log.error(f"WebSocket Error: {e}")
            self.active_websocket = None

    async def start(self):
        async with websockets.serve(self.handle_connection, self.host, self.port):
            log.info("WebSocket Server is running. Waiting for commands...")
            await asyncio.Future()

if __name__ == "__main__":
    server = OmnixServer()
    asyncio.run(server.start())
