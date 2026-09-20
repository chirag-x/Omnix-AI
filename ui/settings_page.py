"""
Omnix — Voro-Style Settings Page (Final Polish)
"""
import os
import shutil
import asyncio
import threading
import flet as ft
from core.settings import SettingsManager
from faster_whisper import download_model

_DEFAULT_ACCENT = "#7C4DFF"

_ACCENT_PRESETS = [
    ("#7C4DFF", "Purple"),
    ("#2196F3", "Blue"),
    ("#4CAF50", "Green"),
    ("#FF5722", "Orange"),
    ("#E91E63", "Pink"),
]

# Readable TTS Voices
_VOICES = {
    "en-US-ChristopherNeural": "Christopher (US Male)",
    "en-US-AriaNeural": "Aria (US Female)",
    "en-US-GuyNeural": "Guy (US Male)",
    "en-US-JennyNeural": "Jenny (US Female)",
    "en-GB-SoniaNeural": "Sonia (UK Female)",
    "en-GB-RyanNeural": "Ryan (UK Male)",
    "hi-IN-SwaraNeural": "Swara (Hindi Female)",
    "hi-IN-MadhurNeural": "Madhur (Hindi Male)",
}

def get_audio_devices():
    inputs, outputs = ["Default System Microphone"], ["Default System Speaker"]
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        in_names = [d['name'] for d in devices if d['max_input_channels'] > 0 and d['hostapi'] == 0 and "mapper" not in d['name'].lower()]
        if in_names: inputs.extend(list(dict.fromkeys(in_names)))
    except: pass
    
    try:
        import pygame
        pygame.mixer.init()
        # Ensure pygame 2.0+ sdl2 module is loaded
        import pygame._sdl2.audio as sdl2_audio
        out_names = sdl2_audio.get_audio_device_names(False)
        if out_names: outputs.extend(list(dict.fromkeys(out_names)))
    except: pass
    
    return inputs, outputs

def build_settings_page(page: ft.Page, on_back):
    settings = SettingsManager.all()
    accent = SettingsManager.get("accent_color") or _DEFAULT_ACCENT
    is_dark = settings.get("dark_mode", True)
    
    # Theme colors fixed for light mode contrast
    c_bg = "#0a0a18" if is_dark else "#eef1f5"
    c_surface = "#111127" if is_dark else "#ffffff"
    c_border = "#333355" if is_dark else "#cfd4db"
    c_text = "white" if is_dark else "#1a1a2e"
    c_sub = "#8888aa" if is_dark else "#555577"
    c_sidebar = "#0b0b18" if is_dark else "#f4f6f9"
    c_bottom = "#0f0f1c" if is_dark else "#ffffff"
    
    # Button colors for contrast
    c_btn_bg = c_border if is_dark else "#505465"
    
    current_tab = "Activation"
    activation_mode = settings.get("activation_mode", "Free Local Activation (Ollama)")
    
    _settings_map = {}
    
    def _pick_3d(e):
        def run_pick():
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.attributes("-topmost", True)
            root.withdraw()
            initial_dir = os.path.join(settings.get("default_download_location", "E:/Coding/Omnix/Omnix/Default_Downloads"), "model")
            p = filedialog.askopenfilename(title="Select 3D Model", initialdir=initial_dir, filetypes=[("3D Models", "*.obj *.gltf *.glb")])
            root.destroy()
            if p:
                SettingsManager.set("model_3d_path", p)
                e.control.text = f"Selected: {os.path.basename(p)}"
                e.control.icon = ft.Icons.CHECK_CIRCLE
                e.control.bgcolor = ft.Colors.GREEN_700
                page.overlay.append(ft.SnackBar(ft.Text(f"Saved: {os.path.basename(p)}"), open=True))
                page.update()
        threading.Thread(target=run_pick, daemon=True).start()
    
    def bind(key, control, default=None):
        val = settings.get(key, default)
        if hasattr(control, "value"):
            control.value = val
        _settings_map[key] = control
        return control

    content_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=24)
    tabs_column = ft.Column(spacing=4)
    
    def make_field(label, key, default="", password=False, hint="", multiline=False):
        return bind(key, ft.TextField(
            label=label, hint_text=hint, password=password, can_reveal_password=password,
            expand=True, bgcolor=c_surface, border_color=c_border, color=c_text,
            focused_border_color=accent, border_radius=8, text_size=13, multiline=multiline
        ), default)

    def section_header(title, subtitle=None):
        cols = [ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=c_text)]
        if subtitle:
            cols.append(ft.Text(subtitle, size=12, color=c_sub, italic=True))
        cols.append(ft.Divider(color=c_border, height=1))
        return ft.Column(cols, spacing=4)

    def on_activation_change(e):
        nonlocal activation_mode
        activation_mode = e.control.value
        render_content()

    def set_accent_color(e, hex_code):
        nonlocal accent
        accent = hex_code
        SettingsManager.set("accent_color", accent)
        render_content()


    def test_whisper_models(e):
        import os
        wake = settings.get("wakeword_model", "None selected")
        stt = settings.get("stt_model", "None selected")
        
        base_dir = settings.get("default_download_location", "E:/Coding/Omnix/Omnix/Default_Downloads")
        wake_path = os.path.join(base_dir, "model", wake) if wake != "None selected" else ""
        stt_path = os.path.join(base_dir, "model", stt) if stt != "None selected" else ""
        
        w_status = "✅ WORKING (Ready to listen)" if os.path.exists(wake_path) else "❌ NOT WORKING (Model missing)"
        s_status = "✅ WORKING (Ready to transcribe)" if os.path.exists(stt_path) else "❌ NOT WORKING (Model missing)"
        
        msg = f"🎤 Whisper Voice AI Status:\n\nWake Word Engine [ {wake} ]: {w_status}\nSpeech-to-Text Engine [ {stt} ]: {s_status}"
        color = ft.Colors.GREEN_800 if ("✅" in w_status and "✅" in s_status) else ft.Colors.RED_800
        
        page.overlay.append(ft.SnackBar(
            ft.Text(msg, color="white", weight="bold"),
            bgcolor=color,
            duration=5000,
            open=True
        ))
        page.update()


    def test_llm_models(e):
        e.control.text = "Testing..."
        e.control.disabled = True
        page.update()
        
        def run_test():
            import requests, time, concurrent.futures
            
            # Read current values from the UI fields based on active mode
            if activation_mode == "Basic Activation (Free AI)":
                k_field, m_field, u_field = "omniroute_basic_key", "omniroute_basic_models", "omniroute_basic_url"
            else:
                dev_provider = settings.get("developer_provider", "OmniRouter")
                if dev_provider == "Google AI Studio":
                    k_field, m_field, u_field = "google_ai_key", "google_ai_models", "google_ai_url"
                else:
                    k_field, m_field, u_field = "omniroute_dev_key", "omniroute_dev_models", "omniroute_dev_url"

            key = _settings_map[k_field].value if k_field in _settings_map else settings.get(k_field, "")
            models_str = _settings_map[m_field].value if m_field in _settings_map else settings.get(m_field, "")
            url_base = _settings_map[u_field].value if u_field in _settings_map else settings.get(u_field, "")
            
            models = [m.strip() for m in models_str.split(",") if m.strip()]
            
            if not url_base or not models:
                msg = "❌ Missing Endpoint URL or Models to test."
                page.overlay.append(ft.SnackBar(ft.Text(msg, color="white", weight="bold"), bgcolor=ft.Colors.RED_800, open=True))
                e.control.text = "Test LLM Models"
                e.control.disabled = False
                page.update()
                return
                
            url = f"{url_base.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            
            def test_single(model):
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "hello"}],
                    "max_tokens": 1
                }
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=10)
                    if resp.status_code == 200:
                        return f"✅ {model} (Online)"
                    else:
                        err_text = resp.text
                        import json
                        try:
                            # Try to extract a clean message from OpenRouter/OpenAI JSON format
                            j = json.loads(err_text)
                            if "error" in j and "message" in j["error"]:
                                err_text = j["error"]["message"]
                        except:
                            pass
                        return f"❌ {model} (Failed: {resp.status_code} - {err_text})"
                except Exception as ex:
                    return f"❌ {model} (Offline/Timeout: {str(ex)})"
                    
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as executor:
                results = list(executor.map(test_single, models))
            
            dlg = ft.AlertDialog(
                title=ft.Text("LLM Connection Test Results"),
                content=ft.Column([ft.Text(r) for r in results], scroll=ft.ScrollMode.AUTO, height=200, width=400),
            )
            
            def close_dlg(e_dlg):
                dlg.open = False
                page.update()
                
            dlg.actions = [ft.TextButton("Close", on_click=close_dlg)]
                
            page.overlay.append(dlg)
            dlg.open = True
            
            e.control.text = "Test LLM Models"
            e.control.disabled = False
            page.update()
            
        threading.Thread(target=run_test, daemon=True).start()

    def render_content():
        content_area.controls.clear()
        
        if current_tab == "Activation":
            content_area.controls.append(section_header("Activation Mode"))
            mode_dropdown = ft.Dropdown(
                label="Activation Mode", value=activation_mode,
                options=[ft.dropdown.Option(m) for m in ["Developer Mode", "Premium Activation (Paid AI)", "Basic Activation (Free AI)", "Free Local Activation (Ollama)"]],
                on_select=on_activation_change, bgcolor=c_surface, color=c_text, border_color=c_border, focused_border_color=accent, border_radius=8
            )
            content_area.controls.append(mode_dropdown)
            
            card_col = ft.Column(spacing=16)
            hint_url = ft.Text("Hint: Format as 'http://localhost:20128/v1' or 'https://api.openai.com/v1'", size=11, color=c_sub)
            hint_models = ft.Text("Hint: Comma separated, e.g., 'gpt-4o, claude-3-sonnet'", size=11, color=c_sub)
            
            if activation_mode == "Developer Mode":
                dev_provider = settings.get("developer_provider", "OmniRouter")
                
                def on_dev_provider_change(e):
                    settings["developer_provider"] = e.control.value
                    SettingsManager.set("developer_provider", e.control.value)
                    render_content()
                    page.update()

                content_area.controls.insert(1, bind("developer_provider", ft.Dropdown(
                    label="Developer Provider", value=dev_provider,
                    options=[ft.dropdown.Option("OmniRouter"), ft.dropdown.Option("Google AI Studio")],
                    on_select=on_dev_provider_change, bgcolor=c_surface, color=c_text, border_color=c_border, focused_border_color=accent, border_radius=8
                ), "OmniRouter"))

                if dev_provider == "OmniRouter":
                    dev_mods = settings.get("omniroute_dev_models", "")
                    available = [m.strip() for m in dev_mods.split(",") if m.strip()]
                    force_opts = [ft.dropdown.Option("", "🤖 Auto  (let Omnix choose)")] + [ft.dropdown.Option(m) for m in available]
                    card_col.controls.extend([
                        section_header("OmniRouter Settings"),
                        make_field("OmniRoute API Key", "omniroute_dev_key", password=True),
                        make_field("Models", "omniroute_dev_models", multiline=True), hint_models,
                        make_field("Endpoint URL", "omniroute_dev_url"), hint_url,
                        ft.Divider(color=c_border),
                        bind("force_specific_model", ft.Dropdown(
                            label="Force Specific Model (Override auto-selection)",
                            options=force_opts,
                            bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8
                        ), ""),
                        ft.Row([
                            ft.FilledButton("Test Whisper Models", on_click=test_whisper_models, bgcolor="#1a73e8", color="white"),
                            ft.FilledButton("Test LLM Models", on_click=test_llm_models, bgcolor="#1a73e8", color="white")
                        ], spacing=10),
                        ft.Divider(color=c_border),
                        bind("omniroute_autostart", ft.Switch(label="Auto-start OmniRoute server", value=True, active_color=accent, label_position=ft.LabelPosition.RIGHT), True)
                    ])
                else:
                    google_mods = settings.get("google_ai_models", "gemini-2.0-flash-exp, gemini-1.5-pro")
                    available = [m.strip() for m in google_mods.split(",") if m.strip()]
                    force_opts = [ft.dropdown.Option("", "🤖 Auto  (let Omnix choose)")] + [ft.dropdown.Option(m) for m in available]
                    card_col.controls.extend([
                        section_header("Google AI Studio Settings"),
                        make_field("Google AI API Key", "google_ai_key", password=True),
                        make_field("Models", "google_ai_models", multiline=True, default="gemini-2.0-flash-exp, gemini-1.5-pro"), hint_models,
                        make_field("Endpoint URL", "google_ai_url", default="https://generativelanguage.googleapis.com/v1beta/openai/"), hint_url,
                        ft.Divider(color=c_border),
                        bind("force_specific_model_google", ft.Dropdown(
                            label="Force Specific Model (Override auto-selection)",
                            options=force_opts,
                            bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8
                        ), ""),
                        ft.Row([
                            ft.FilledButton("Test Whisper Models", on_click=test_whisper_models, bgcolor="#1a73e8", color="white"),
                            ft.FilledButton("Test LLM Models", on_click=test_llm_models, bgcolor="#1a73e8", color="white")
                        ], spacing=10)
                    ])
            elif activation_mode == "Premium Activation (Paid AI)":
                card_col.controls.extend([
                    section_header("OpenAI"), make_field("API Key", "openai_key", password=True), make_field("Models", "openai_models", multiline=True), hint_models, make_field("Endpoint URL", "openai_url"), hint_url,
                    section_header("Claude"), make_field("API Key", "claude_key", password=True), make_field("Models", "claude_models", multiline=True), hint_models, make_field("Endpoint URL", "claude_url"), hint_url,
                    section_header("Gemini"), make_field("API Key", "gemini_key", password=True), make_field("Models", "gemini_models", multiline=True), hint_models, make_field("Endpoint URL", "gemini_url"), hint_url,
                ])
            elif activation_mode == "Basic Activation (Free AI)":
                card_col.controls.extend([
                    make_field("OmniRoute API Key", "omniroute_basic_key", password=True), make_field("Models", "omniroute_basic_models", multiline=True), hint_models, make_field("Endpoint URL", "omniroute_basic_url"), hint_url,
                    ft.Divider(color=c_border),
                    ft.Row([
                        ft.FilledButton("Test LLM Models", on_click=test_llm_models, bgcolor="#1a73e8", color="white")
                    ])
                ])
            elif activation_mode == "Free Local Activation (Ollama)":
                card_col.controls.extend([
                    make_field("Ollama Chat Model", "ollama_chat_model", default="qwen2.5:7b"),
                    ft.Text("Hint: Exactly as it appears in Ollama (e.g., 'llama3.1', 'qwen2.5:7b')", size=11, color=c_sub),
                    make_field("Ollama Coding Model", "ollama_coding_model"),
                    ft.Container(content=ft.Text("Fetch Validate Local Models", color="white", text_align=ft.TextAlign.CENTER), bgcolor=c_btn_bg, padding=10, border_radius=8, ink=True)
                ])
                
            content_area.controls.append(ft.Container(content=card_col, padding=20, border=ft.Border.all(1, c_border), border_radius=10, bgcolor=c_surface))

        elif current_tab == "Appearance":
            content_area.controls.append(section_header("Theme & Colors"))
            swatches = ft.Row(spacing=15)
            for hex_code, name in _ACCENT_PRESETS:
                swatches.controls.append(ft.Container(width=36, height=36, border_radius=18, bgcolor=hex_code, tooltip=name, border=ft.Border.all(2, c_text) if accent == hex_code else None, on_click=lambda e, h=hex_code: set_accent_color(e, h), ink=True))
            
            content_area.controls.extend([
                ft.Text("Accent Color", size=14, color=c_sub), swatches,
                ft.Divider(color=c_border),
                bind("dark_mode", ft.Switch(label="Dark Mode", active_color=accent), True),
                ft.Text("Window Opacity (0.1 to 1.0)", size=14, color=c_sub),
                bind("window_opacity", ft.Slider(min=0.1, max=1.0, divisions=9, label="{value}", active_color=accent), 1.0),
                ft.Divider(color=c_border),
                section_header("3D Visualizer Assets"),
                ft.Row([ft.FilledButton("Upload Custom 3D Model (.obj, .glb, .gltf)", icon=ft.Icons.UPLOAD_FILE_ROUNDED, color="white", bgcolor=c_btn_bg, on_click=_pick_3d)])
            ])

        elif current_tab == "Interface":
            content_area.controls.extend([
                section_header("General Interface"),
                ft.Text("Chat History Length (Messages to remember)", size=14, color=c_sub),
                bind("chat_history_length", ft.Slider(min=10, max=100, divisions=9, label="{value}", active_color=accent), 50),
                bind("show_wakeword_overlay", ft.Switch(label="Show Wake Word Overlay Text", active_color=accent), True),
                ft.Divider(color=c_border),
                section_header("Downloads & Models"),
                bind("default_download_location", ft.TextField(label="Default Download Location", read_only=True, bgcolor=c_surface, border_color=c_border, color=c_text, border_radius=8), "E:/Coding/Omnix/Omnix/Default_Downloads"),
                ft.Text("Note: Downloaded AI models will be placed inside a 'model' subfolder here automatically.", size=11, color=c_sub, italic=True),
                ft.Divider(color=c_border),
                section_header("STT Model Downloader", "Download offline Whisper models"),
            ])
            
            def get_model_path(m):
                base = _settings_map.get("default_download_location").value if "default_download_location" in _settings_map else settings.get("default_download_location", "E:/Coding/Omnix/Omnix/Default_Downloads")
                return os.path.join(base, "model", m)

            def is_downloaded(m):
                p = get_model_path(m)
                if not os.path.exists(p): return False
                return any(f.endswith('.bin') or f.endswith('.safetensors') or f.endswith('.pt') for f in os.listdir(p))
                
            def trigger_download(e, model_name, row):
                btn = row.controls[1]
                del_btn = row.controls[2]
                btn.text = "Loading..."
                btn.disabled = True
                page.update()
                
                def _do_download():
                    try:
                        btn.text = "Downloading..."
                        page.update()
                        target_dir = get_model_path(model_name)
                        os.makedirs(target_dir, exist_ok=True)
                        download_model(model_name, output_dir=target_dir)
                        btn.text = "Already Downloaded"
                        btn.icon = ft.Icons.CHECK_CIRCLE
                        del_btn.visible = True
                    except Exception as ex:
                        btn.text = "Failed"
                        btn.disabled = False
                    page.update()
                threading.Thread(target=_do_download, daemon=True).start()

            def trigger_delete(e, model_name, row):
                try: shutil.rmtree(get_model_path(model_name))
                except: pass
                row.controls[1].text = "Download"
                row.controls[1].icon = ft.Icons.DOWNLOAD_ROUNDED
                row.controls[1].disabled = False
                row.controls[2].visible = False
                page.update()

            models = ["tiny", "tiny.en", "base", "base.en", "medium", "medium.en", "large"]
            model_grid = ft.Column(spacing=10)
            for m in models:
                downloaded = is_downloaded(m)
                row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                txt = ft.Text(m.ljust(10), size=14, weight=ft.FontWeight.W_500, color=c_text, width=80)
                btn = ft.FilledButton("Already Downloaded" if downloaded else "Download", icon=ft.Icons.CHECK_CIRCLE if downloaded else ft.Icons.DOWNLOAD_ROUNDED, color="white", bgcolor=c_btn_bg, disabled=downloaded)
                del_btn = ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400, tooltip="Remove Model", visible=downloaded)
                btn.on_click = lambda e, mn=m, r=row: trigger_download(e, mn, r)
                del_btn.on_click = lambda e, mn=m, r=row: trigger_delete(e, mn, r)
                row.controls.extend([txt, btn, del_btn])
                model_grid.controls.append(row)
                
            content_area.controls.append(ft.Container(content=model_grid, padding=16, border=ft.Border.all(1, c_border), border_radius=8))

        elif current_tab == "Audio":
            inputs, outputs = get_audio_devices()
            
            def get_stt_opts():
                base = settings.get("default_download_location", "E:/Coding/Omnix/Omnix/Default_Downloads")
                mdir = os.path.join(base, "model")
                opts = []
                if os.path.exists(mdir):
                    for d in os.listdir(mdir):
                        p = os.path.join(mdir, d)
                        if os.path.isdir(p) and any(f.endswith('.bin') or f.endswith('.safetensors') for f in os.listdir(p)):
                            opts.append(ft.dropdown.Option(d))
                if not opts:
                    opts = [ft.dropdown.Option("medium.en")]
                return opts

            def test_tts_voice(e):
                voice_id = _settings_map["voice_selection"].value
                page.snack_bar = ft.SnackBar(ft.Text(f"Testing voice: {voice_id}..."), open=True)
                page.update()
                
                def _run_tts():
                    try:
                        from senses.speech import generate_audio
                        from tts_player import play_audio_b64
                        b64 = asyncio.run(generate_audio("Hello, this is a test of my voice.", voice_pref=voice_id))
                        if b64:
                            play_audio_b64(b64)
                    except Exception as ex:
                        print("TTS Test error:", ex)
                threading.Thread(target=_run_tts, daemon=True).start()

            content_area.controls.extend([
                section_header("Input / Output Devices"),
                bind("audio_output_enabled", ft.Switch(label="Enable Audio Output", active_color=accent), True),
                bind("audio_output_device", ft.Dropdown(label="Speaker (Output)", options=[ft.dropdown.Option(o) for o in outputs], bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8), outputs[0] if outputs else None),
                bind("audio_input_enabled", ft.Switch(label="Enable Microphone Input", active_color=accent), True),
                bind("audio_input_device", ft.Dropdown(label="Microphone (Input)", options=[ft.dropdown.Option(i) for i in inputs], bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8), inputs[0] if inputs else None),
                ft.Divider(color=c_border),
                section_header("Wake Word Recognition"),
                bind("wakeword_model", ft.Dropdown(label="Wake Word Model (from Downloads/model)", options=get_stt_opts(), bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8), "medium.en"),
                bind("wakeword_phrase", ft.Dropdown(
                    label="Wake Word Phrase",
                    options=[
                        ft.dropdown.Option("Any Wake Word"),
                        ft.dropdown.Option("Hey Omnix"),
                        ft.dropdown.Option("Omnix"),
                        ft.dropdown.Option("Hello Omnix"),
                        ft.dropdown.Option("Omnix Wake Up"),
                        ft.dropdown.Option("Wake Up"),
                        ft.dropdown.Option("Wake Up Omnix")
                    ],
                    bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8
                ), "Any Wake Word"),
                ft.Divider(color=c_border),
                section_header("Speech-to-Text (STT)"),
                bind("wakeword_model", ft.Dropdown(label="Wake Word Whisper Model", options=get_stt_opts(), bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8), "tiny.en"),
                bind("stt_model", ft.Dropdown(label="Speech-to-Text Whisper Model", options=get_stt_opts(), bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8), "medium"),
                bind("stt_device", ft.Dropdown(
                    label="STT Compute Device",
                    options=[
                        ft.dropdown.Option("auto", "Auto (GPU Preferred)"),
                        ft.dropdown.Option("cuda", "CUDA (GPU Only)"),
                        ft.dropdown.Option("cpu", "CPU Only"),
                        ft.dropdown.Option("cloud_groq", "Cloud (Groq API - Instant)")
                    ],
                    bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8
                ), "auto"),
                make_field("Groq API Key", "groq_api_key", password=True),
                make_field("Groq STT Model (e.g. whisper-large-v3-turbo)", "groq_stt_model", default="whisper-large-v3-turbo"),
                ft.Divider(color=c_border),
                section_header("Audio Mode for Omnix", "Controls which voice engine Omnix uses to speak"),
                bind("audio_mode", ft.Dropdown(
                    label="Voice Mode",
                    options=[
                        ft.dropdown.Option("Natural", "Natural  —  Offline neural voice (Kokoro AI, recommended)"),
                        ft.dropdown.Option("Script",  "Script   —  Online Microsoft voices (Edge-TTS, needs internet)"),
                    ],
                    bgcolor=c_surface, color=c_text, border_color=c_border, focused_border_color=accent, border_radius=8
                ), "Natural"),
                ft.Text("Natural: Fast, offline, emotional. Script: Online only, more voice choices.", size=11, color=c_sub, italic=True),
                ft.Divider(color=c_border),
                section_header("Text-to-Speech (TTS)", "Applies only in Script (Edge-TTS) mode"),
                ft.Row([
                    bind("voice_selection", ft.Dropdown(label="Voice Selection", options=[ft.dropdown.Option(k, v) for k,v in _VOICES.items()], expand=True, bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8), "en-US-ChristopherNeural"),
                    ft.IconButton(ft.Icons.PLAY_CIRCLE_FILL_ROUNDED, icon_color=accent, icon_size=32, tooltip="Test Voice", on_click=test_tts_voice)
                ])
            ])

        elif current_tab == "Vision":
            content_area.controls.extend([
                section_header("Vision Engine (OCR & Image Processing)"),
                ft.Text("Select the hardware device to process visual operations (EasyOCR).", size=14, color=c_sub),
                bind("vision_device", ft.Dropdown(
                    label="Compute Device",
                    options=[
                        ft.dropdown.Option("auto", "Auto (GPU Preferred)"),
                        ft.dropdown.Option("cuda", "CUDA (GPU Only)"),
                        ft.dropdown.Option("cpu", "CPU Only")
                    ],
                    bgcolor=c_surface, color=c_text, border_color=c_border, focused_border_color=accent, border_radius=8
                ), "auto"),
                ft.Text("Note: CUDA (GPU) is much faster but requires an NVIDIA graphics card. If you get 'pin_memory' errors, switch to CPU.", size=11, color=c_sub, italic=True),
            ])

        elif current_tab == "Help":
            def build_shortcut_row(label_text, key_name, default_val):
                tf = ft.TextField(value=settings.get(key_name, default_val), read_only=True, expand=True, bgcolor=c_surface, color=c_text, border_color=c_border, border_radius=8)
                _settings_map[key_name] = tf
                
                def enter_edit(e):
                    tf.value = "Press keys..."
                    tf.bgcolor = accent
                    tf.color = "white"
                    page.update()
                    old_kb = page.on_keyboard_event
                    
                    def capture_keys(ke: ft.KeyboardEvent):
                        parts = []
                        if ke.ctrl: parts.append("Ctrl")
                        if ke.shift: parts.append("Shift")
                        if ke.alt: parts.append("Alt")
                        if ke.meta: parts.append("Meta")
                        
                        key_name_str = ke.key
                        if key_name_str not in ["Control", "Shift", "Alt", "Meta"]:
                            parts.append(key_name_str.upper())
                            tf.value = "+".join(parts)
                            tf.bgcolor = c_surface
                            tf.color = c_text
                            page.on_keyboard_event = old_kb
                            page.update()
                            
                    page.on_keyboard_event = capture_keys

                def save_hk(e):
                    SettingsManager.set(key_name, tf.value)
                    page.snack_bar = ft.SnackBar(ft.Text(f"Shortcut saved!"), open=True)
                    page.update()
                    
                def cancel_hk(e):
                    tf.value = settings.get(key_name, default_val)
                    tf.bgcolor = c_surface
                    tf.color = c_text
                    page.update()
                    
                return ft.Row([
                    ft.Text(label_text, width=160, color=c_text), tf,
                    ft.FilledButton("Edit", color="white", bgcolor=c_btn_bg, on_click=enter_edit),
                    ft.FilledButton("Save", color="white", bgcolor=accent, on_click=save_hk),
                    ft.FilledButton("Cancel", color="white", bgcolor=c_btn_bg, on_click=cancel_hk)
                ])

            def reset_all_hk(e):
                SettingsManager.set("hotkey_cycle_activation", "Ctrl+Shift+V")
                SettingsManager.set("hotkey_stop_generation", "Ctrl+X")
                render_content()
                page.snack_bar = ft.SnackBar(ft.Text("Shortcuts reset to defaults!"), open=True)
                page.update()

            content_area.controls.extend([
                section_header("Global Keyboard Shortcuts"),
                ft.Text("Click 'Edit', press your desired key combination, then save.", size=13, color=c_sub),
                build_shortcut_row("Cycle Activation Mode", "hotkey_cycle_activation", "Ctrl+Shift+V"),
                build_shortcut_row("Stop Generation", "hotkey_stop_generation", "Ctrl+X"),
                ft.Row([ft.FilledButton("Reset All Shortcuts to Default", icon=ft.Icons.RESTORE, color="white", bgcolor=c_btn_bg, on_click=reset_all_hk)]),
                ft.Divider(color=c_border),
                section_header("Hands-Free Instructions"),
                ft.Markdown("- **Wake Word**: Say 'Hey Omnix' to wake the AI.\n- **Silence Timer**: The AI automatically stops listening after 30 seconds of silence.\n- **Speech Interrupt**: Audio playback automatically mutes when you speak.", selectable=True)
            ])

        elif current_tab == "Updates":
            content_area.controls.extend([
                section_header("Software Updates"), ft.Text("Current Version: 1.0.0", size=14, color=c_text), ft.FilledButton("Check for Updates", icon=ft.Icons.SYSTEM_UPDATE_ALT_ROUNDED, color="white", bgcolor=accent)
            ])

        elif current_tab == "Other":
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            content_area.controls.extend([
                section_header("Developer & Misc"), ft.Text("Backend Timeout (Seconds)", size=14, color=c_sub),
                bind("backend_timeout", ft.Slider(min=5, max=120, divisions=115, label="{value}s", active_color=accent), 30),
                bind("developer_logs", ft.Switch(label="Enable Developer Logs", active_color=accent), False),
                ft.Row([ft.FilledButton("Open Logs Folder", icon=ft.Icons.FOLDER_OPEN, on_click=lambda e: os.startfile(log_dir) if os.path.exists(log_dir) else None, bgcolor=c_btn_bg, color="white")])
            ])

        page.update()

    def select_tab(e, tab_name):
        nonlocal current_tab
        current_tab = tab_name
        for c in tabs_column.controls:
            if c.data == tab_name:
                c.bgcolor = accent
                c.content.color = "white"
            else:
                c.bgcolor = ft.Colors.TRANSPARENT
                c.content.color = c_sub
        render_content()

    def build_tab_btn(name, is_active=False):
        return ft.Container(
            content=ft.Text(name, color="white" if is_active else c_sub, size=14, weight=ft.FontWeight.W_500),
            padding=ft.Padding(16, 12, 16, 12), border_radius=8, bgcolor=accent if is_active else ft.Colors.TRANSPARENT,
            data=name, on_click=lambda e, n=name: select_tab(e, n), ink=True
        )

    tabs = ["Activation", "Interface", "Appearance", "Audio", "Vision", "Help", "Updates", "Other"]
    for t in tabs:
        tabs_column.controls.append(build_tab_btn(t, t == current_tab))

    sidebar = ft.Container(content=tabs_column, width=240, padding=16, bgcolor=c_sidebar, border=ft.Border(right=ft.BorderSide(1, c_border)))
    
    main_row = ft.Container(
        content=ft.Row([sidebar, ft.Container(content=content_area, expand=True, padding=30)], expand=True, spacing=0),
        bgcolor=c_bg, expand=True
    )

    def save_and_restart(e):
        SettingsManager.set("activation_mode", activation_mode)
        for k, ctrl in _settings_map.items():
            if k not in ["hotkey_cycle_activation", "hotkey_stop_generation"]: 
                SettingsManager.set(k, ctrl.value)
        e.control.text = "Restarting..."
        e.control.disabled = True
        page.update()
        def do_restart():
            import time, sys, os, subprocess
            # 1. Spawn new instance
            subprocess.Popen([sys.executable] + sys.argv)
            time.sleep(0.5)
            # 2. Ask the Flet window to gracefully destroy itself
            # This cleanly kills the Flet UI and lets ft.run() exit naturally.
            try:
                page.window.prevent_close = False
                page.run_task(page.window.destroy)
            except:
                pass
            
        threading.Thread(target=do_restart, daemon=True).start()

    bottom_bar = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.FilledButton("Save Restart", color="white", bgcolor="#1a73e8", on_click=save_and_restart, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding(40, 16, 40, 16))),
                ft.FilledButton("Cancel", color="white", bgcolor=c_btn_bg, on_click=lambda e: on_back(), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding(40, 16, 40, 16))),
            ], spacing=10),
            ft.Text("Designed and Developed by Chirag Sharma", size=12, color=c_sub, italic=True)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(20, 16, 20, 16), bgcolor=c_bottom, border=ft.Border(top=ft.BorderSide(1, c_border))
    )

    layout = ft.Column([main_row, bottom_bar], expand=True, spacing=0)
    render_content()
    return layout
