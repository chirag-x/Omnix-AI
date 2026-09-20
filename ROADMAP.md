# Omnix Project Roadmap & Architecture

Omnix is a highly advanced, voice-controlled, autonomous AI agent designed to interact with your Windows PC natively. Rather than being restricted to a simple chat interface, Omnix acts as a true digital companion—it hears you, sees your screen, and uses your mouse and keyboard just like a human would.

---

## 🟢 WHAT WE HAVE BUILT SO FAR (Current State)

We have successfully completed Phases 1 through 5. Omnix is currently fully operational as an intelligent screen-clicking assistant with memory.

### The Foundation & Senses
* **Phase 1 (The Ear & UI):** Built a gorgeous Flet-based UI with a fully integrated `openWakeWord` engine. Omnix listens completely offline for the "Hey Jarvis" wake word without sending constant data to the cloud.
* **Phase 2 (The Voice):** Implemented high-quality Text-to-Speech (TTS). Omnix currently defaults to Kokoro AI for fast, emotional, natural offline voices, with Edge-TTS online fallbacks.
* **Phase 3 (The Hands):** Gave Omnix control over the mouse and keyboard using `pyautogui` and `pywinauto`. It can type, press hotkeys, and interact with the UI accessibility tree (`click_element`).
* **Phase 4 (The Eyes):** Integrated Computer Vision (Tesseract OCR). When standard UI clicking fails (like in web browsers or games), Omnix can literally "see" the text on the screen and calculate the coordinates to click it (`click_text`).

### The Brain & Memory Upgrade (Phase 5 - Just Completed)
* **Instant Hearing (Groq API):** We swapped the slow local STT model for the lightning-fast Groq Cloud API, allowing Omnix to hear and transcribe your voice instantly with zero PC lag.
* **Multi-Model Routing (The Bouncer System):** Omnix now dynamically routes tasks. Simple, fast OS actions are handled by a lightweight model (like Gemini Flash), but complex logic is automatically handed off to massive genius models (like Nemotron 550B via OpenRouter).
* **The Memory Core:** Omnix now has long-term persistent memory (`memory.json`). You can tell it facts (like your name or favorite song), and it will inject those facts into its system prompt on every future reboot so it never forgets who you are.
* **Echo Loop Prevention:** Implemented hardware-level microphone selection and software TTS buffering to ensure Omnix never accidentally "hears" its own voice and talks to itself.

---

## 🚀 THE FUTURE: PHASES 6 TO 9

Now that Omnix has a physical presence (Hands, Eyes, Voice) and a stable memory, we are moving into deep system automation.

### Phase 6: Deep System Integrations (The "God Mode" Upgrade)
**Goal:** Give Omnix software-level permissions to manage your PC without needing to visually click the screen.
* **Terminal Mastery (`run_terminal_command`):** Omnix will be able to silently open PowerShell. If you ask it to "Install the Python requests library", it will execute `pip install requests` directly instead of trying to click through a browser.
* **File System Search (`read_file` & `search_files`):** Omnix will index and read local files. You can ask "Summarize the PDF on my desktop" and it will read the data programmatically.
* **Web Search API:** Give Omnix a silent web search tool (e.g., DuckDuckGo) so it can answer real-world questions (weather, news, coding docs) instantly without opening Chrome.

### Phase 7: Autonomous Background Agents
**Goal:** Allow Omnix to work in the background silently while you use your PC.
* **Asynchronous Threading:** Run tasks in the background without freezing the voice UI. You can talk to Omnix while it is simultaneously doing a long task.
* **Scheduled Watchers:** You can say: *"omnix, monitor my downloads folder and organize files by extension every hour."* Omnix will spawn a silent watcher agent.
* **Long-Running Processing:** Allow Omnix to handle massive tasks (like analyzing a massive codebase) silently, chiming in over the speakers only when it has finished.

### Phase 8: Vocal Polish & True Multilingual Support
**Goal:** Perfect the AI's pronunciation, language capabilities, and interruption mechanics.
* **Custom Pronunciation Dictionary:** Implement a local phonetic mapping (e.g., forcing "Kirag" to be pronounced "Chirag") to correct English TTS phonemizers for regional names and slang.
* **Multilingual TTS Engine:** Upgrade the Kokoro/Edge engine to support real-time language detection, switching to native Hindi (or other language) voice models automatically when necessary.
* **Barge-In (Interruption):** Add the ability for you to interrupt Omnix while it is speaking. If it is rambling, saying "omnix, stop" will instantly kill the TTS audio output.

### Phase 9: Final Packaging & Stealth Mode
**Goal:** Turn the Python script into a polished, shareable, invisible Windows application.
* **The PyInstaller Compiler:** Compile the entire Omnix Python environment into a single standalone `Omnix.exe` executable.
* **System Tray Integration:** Create a silent background mode where Omnix lives in the Windows System Tray (near the clock).
* **Auto-Start on Boot:** Allow Omnix to launch invisibly the moment you turn on your PC, always listening for the wake word without taking up space on your taskbar.
