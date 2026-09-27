with open(r'e:\Coding\Omnix\backend\core\main.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    'class OmnixServer:',
    '# DEPRECATED: This WebSocket server is a stale/legacy path. The canonical UI is Flet (ui/main.py) with the new Embodiment Event Architecture.\n# This remains here for backwards compatibility.\nclass OmnixServer:'
)

c = c.replace(
    'async def handle_connection(self, websocket):',
    'def make_on_response(websocket):\n    def on_response(text, emotion, audio_b64):\n        # Deprecated adapter for websocket clients\n        asyncio.create_task(websocket.send(json.dumps({"type": "response", "text": text, "emotion": emotion, "audio": audio_b64})))\n    return on_response\n\n    async def handle_connection(self, websocket):'
)

c = c.replace(
    'await process_command(command, websocket)',
    'await process_command(command, make_on_response(websocket))'
)

c = c.replace(
    'await process_command(text, websocket)',
    'await process_command(text, make_on_response(websocket))'
)

c = c.replace(
    'await process_command(message, websocket)',
    'await process_command(message, make_on_response(websocket))'
)

open(r'e:\Coding\Omnix\backend\core\main.py', 'w', encoding='utf-8').write(c)
