import requests
import json
import time
import concurrent.futures
from perception.vision_engine import capture_screen_b64
from core.settings import SettingsManager
from utils.logger import log

ACTIVE_MODEL = None
ACTIVE_URL = None
ACTIVE_KEY = None

def get_activation_config():
    """Parses settings to return the correct URL, KEY, and MODELS list based on Activation Mode."""
    mode = SettingsManager.get("activation_mode", "Free Local Activation (Ollama)")
    
    if mode == "Developer Mode":
        dev_prov = SettingsManager.get("developer_provider", "OmniRouter")
        if dev_prov == "Google AI Studio":
            url = SettingsManager.get("google_ai_url", "https://generativelanguage.googleapis.com/v1beta/openai/")
            key = SettingsManager.get("google_ai_key", "")
            models_str = SettingsManager.get("google_ai_models", "gemini-2.0-flash-exp, gemini-1.5-pro")
            force_model = SettingsManager.get("force_specific_model_google", "")
        else:
            url = SettingsManager.get("omniroute_dev_url", "http://localhost:20128/v1")
            key = SettingsManager.get("omniroute_dev_key", "")
            models_str = SettingsManager.get("omniroute_dev_models", "")
            force_model = SettingsManager.get("force_specific_model", "")
            
        models = [m.strip() for m in models_str.split(",") if m.strip()]
        if not models:
            models = ["gemini-1.5-flash"]
            
        # Handle Force Specific Model override
        if force_model and force_model != "🤖 Auto  (let Omnix choose)":
            return url, key, [force_model], True # True = force selection
        return url, key, models, False
        
    elif mode == "Premium Activation (Paid AI)":
        # For simplicity, pick the first provided endpoint that has a key.
        openai_key = SettingsManager.get("openai_key", "")
        if openai_key:
            url = SettingsManager.get("openai_url", "https://api.openai.com/v1")
            models = [m.strip() for m in SettingsManager.get("openai_models", "gpt-4o").split(",")]
            return url, openai_key, models, False
            
        claude_key = SettingsManager.get("claude_key", "")
        if claude_key:
            url = SettingsManager.get("claude_url", "https://api.anthropic.com/v1")
            models = [m.strip() for m in SettingsManager.get("claude_models", "claude-3-sonnet").split(",")]
            return url, claude_key, models, False
            
        gemini_key = SettingsManager.get("gemini_key", "")
        if gemini_key:
            url = SettingsManager.get("gemini_url", "https://generativelanguage.googleapis.com/v1beta/openai")
            models = [m.strip() for m in SettingsManager.get("gemini_models", "gemini-1.5-flash").split(",")]
            return url, gemini_key, models, False
            
        return "http://localhost:20128/v1", "", ["gpt-4o"], False
        
    elif mode == "Basic Activation (Free AI)":
        url = SettingsManager.get("omniroute_basic_url", "http://localhost:20128/v1")
        key = SettingsManager.get("omniroute_basic_key", "")
        models_str = SettingsManager.get("omniroute_basic_models", "")
        models = [m.strip() for m in models_str.split(",") if m.strip()]
        if not models:
            models = ["antigravity/gemini-2.5-flash"]
        return url, key, models, False
        
    else: # Free Local Activation (Ollama)
        url = "http://localhost:11434/v1"
        key = "ollama"
        chat_model = SettingsManager.get("ollama_chat_model", "qwen2.5:7b")
        return url, key, [chat_model], True


FAST_MODEL = None
EXPERT_MODEL = None
ACTIVE_URL = None
ACTIVE_KEY = None

def get_best_model():
    """Returns (fast_model, expert_model, url, key)"""
    url_base, key, models, is_forced = get_activation_config()
    
    if not models:
        return None, None, url_base, key
        
    if is_forced:
        log.info(f"Activation mode forced model: {models[0]}")
        return models[0], models[0], url_base, key

    # Phase 5: Multi-Model Routing ("Bouncer Logic")
    # First model is Fast, last model is Expert.
    fast_m = models[0]
    expert_m = models[-1]
    
    # We still ping to ensure they are online, but we don't sort by speed to choose the active one anymore.
    # The user dictates the roles by order in the list.
    url = f"{url_base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    
    def ping(m):
        try:
            resp = requests.post(url, headers=headers, json={"model": m, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}, timeout=10)
            return m if resp.status_code == 200 else None
        except:
            return None

    log.info(f"Checking model availability across {len(models)} models: {models}")
    online_models = []
    
    # Ping all models concurrently to find which ones actually exist and are online
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(models))) as executor:
        for m, result in zip(models, executor.map(ping, models)):
            if result:
                online_models.append(result)

    if not online_models:
        log.error("All models are completely offline or invalid names!")
        return None, None, url_base, key
        
    fast_m = online_models[0]
    expert_m = online_models[-1]

    log.info(f"Routing Setup -> Fast Model: {fast_m} | Expert Model: {expert_m}")
    return fast_m, expert_m, url_base, key

def initialize_models() -> int:
    global FAST_MODEL, EXPERT_MODEL, ACTIVE_URL, ACTIVE_KEY
    FAST_MODEL, EXPERT_MODEL, ACTIVE_URL, ACTIVE_KEY = get_best_model()
    return 1 if FAST_MODEL else 0

def generate_response(prompt: str, history: list, retries=1, expert_override=False) -> dict:
    global FAST_MODEL, EXPERT_MODEL, ACTIVE_URL, ACTIVE_KEY
    
    if not FAST_MODEL:
        FAST_MODEL, EXPERT_MODEL, ACTIVE_URL, ACTIVE_KEY = get_best_model()
        
    if not FAST_MODEL:
        return {
            "skill": "done",
            "text": "My connection to the LLM backend is completely offline. I cannot reach any models. Check your API settings.",
            "thought": "All models offline during generate_response."
        }
    
    active_m = EXPERT_MODEL if expert_override and EXPERT_MODEL else FAST_MODEL
    url = f"{ACTIVE_URL.rstrip('/')}/chat/completions"
    b64_image = capture_screen_b64()
    
    messages = [{"role": "system", "content": prompt}]
    formatted_history = []
    for msg in history:
        formatted_history.append({"role": msg["role"], "content": msg["content"]})
        
    # Only append vision if the model is known to support it (most local models reject image_url with 400 Bad Request)
    is_vision_model = any(x in active_m.lower() for x in ["gpt-4", "claude", "gemini", "llava", "vision", "pixtral"])
    
    if formatted_history and formatted_history[-1]["role"] == "user":
        last_text = formatted_history[-1]["content"]
        if is_vision_model:
            formatted_history[-1]["content"] = [
                {"type": "text", "text": last_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
            ]
        else:
            formatted_history[-1]["content"] = last_text
        
    messages.extend(formatted_history)
    
    headers = {
        "Authorization": f"Bearer {ACTIVE_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": active_m,
        "messages": messages,
        "temperature": 0.0,
        "stream": False
    }
    
    log.info(f"Querying brain using active model: {active_m} via {ACTIVE_URL}")
    try:
        timeout = float(SettingsManager.get("backend_timeout", 30.0))
        if timeout < 25.0:
            timeout = 25.0
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        result = data["choices"][0]["message"]["content"].strip()
        
        import re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            clean_json = match.group(0)
            parsed_result = json.loads(clean_json)
            return parsed_result
        else:
            raw_t = result.replace("SPOKEN WORDS", "").strip()
            # Prevent the AI from audibly narrating screen coordinates or raw logs if it hallucinates them
            if "coordinates" in raw_t.lower() or "clicked the" in raw_t.lower() or "action performed" in raw_t.lower():
                log.warning(f"Model hallucinated system log. Suppressing robotic speech: {raw_t}")
                raw_t = "Action complete."
            else:
                log.warning(f"Model ignored JSON format. Wrapping raw text: {raw_t[:100]}...")
                
            return {
                "text": raw_t,
                "emotion": "happy",
                "thought": "Model returned raw text, synthesizing JSON wrapper.",
                "actions": [{"skill": "reply", "args": {}}]
            }
        
    except Exception as e:
        log.warning(f"Active model {active_m} failed: {e}.")
        if retries > 0:
            log.info("Finding a new best model to retry...")
            FAST_MODEL, EXPERT_MODEL, ACTIVE_URL, ACTIVE_KEY = get_best_model()
            return generate_response(prompt, history, retries=retries-1, expert_override=expert_override)
        else:
            log.error("Failed to get response after retrying with new model.")
            return {
                "text": "My brain encountered a critical error processing your request. The model endpoint failed.",
                "emotion": "sad",
                "thought": f"Failed with {active_m}.",
                "actions": [{"skill": "done", "args": {}}]
            }
