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
        url = SettingsManager.get("omniroute_dev_url", "http://localhost:20128/v1")
        key = SettingsManager.get("omniroute_dev_key", "")
        models_str = SettingsManager.get("omniroute_dev_models", "")
        models = [m.strip() for m in models_str.split(",") if m.strip()]
        if not models:
            models = ["antigravity/gemini-3.6-flash-high"]
        # Handle Force Specific Model override
        force_model = SettingsManager.get("force_specific_model", "")
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

def get_best_model():
    """
    Tests all fallback models concurrently. 
    Returns the fastest model that returns a 200 OK.
    """
    url_base, key, models, is_forced = get_activation_config()
    url = f"{url_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    if is_forced and models:
        log.info(f"Activation mode forced model: {models[0]}")
        return models[0], url_base, key

    log.info("Checking all available models to find the fastest online model...")
    results = []
    
    def test_model(model):
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0.0,
            "stream": False
        }
        start = time.time()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=float(SettingsManager.get("backend_timeout", 30)))
            if response.status_code == 200:
                return (model, time.time() - start)
        except Exception:
            pass
        return (model, float('inf'))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(models))) as executor:
        futures = [executor.submit(test_model, m) for m in models]
        for future in concurrent.futures.as_completed(futures):
            model, elapsed = future.result()
            if elapsed != float('inf'):
                results.append((model, elapsed))
                
    if not results:
        log.error("All models are completely offline!")
        return None, url_base, key
        
    results.sort(key=lambda x: x[1])
    best_model = results[0][0]
    log.info(f"Selected fastest model: {best_model} ({results[0][1]:.2f}s)")
    return best_model, url_base, key

def initialize_models() -> int:
    """Test all models and activate the fastest. Returns count of online models."""
    global ACTIVE_MODEL, ACTIVE_URL, ACTIVE_KEY
    ACTIVE_MODEL, ACTIVE_URL, ACTIVE_KEY = get_best_model()
    return 1 if ACTIVE_MODEL else 0

def generate_response(prompt: str, history: list, retries=1) -> dict:
    global ACTIVE_MODEL, ACTIVE_URL, ACTIVE_KEY
    
    if not ACTIVE_MODEL:
        ACTIVE_MODEL, ACTIVE_URL, ACTIVE_KEY = get_best_model()
        
    if not ACTIVE_MODEL:
        return {
            "skill": "done",
            "text": "My connection to the LLM backend is completely offline. I cannot reach any models. Check your API settings.",
            "thought": "All models offline during generate_response."
        }

    url = f"{ACTIVE_URL.rstrip('/')}/chat/completions"
    b64_image = capture_screen_b64()
    
    messages = [{"role": "system", "content": prompt}]
    formatted_history = []
    for msg in history:
        formatted_history.append({"role": msg["role"], "content": msg["content"]})
        
    # Only append vision if the model is known to support it (most local models reject image_url with 400 Bad Request)
    is_vision_model = any(x in ACTIVE_MODEL.lower() for x in ["gpt-4", "claude", "gemini", "llava", "vision", "pixtral"])
    
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
        "model": ACTIVE_MODEL,
        "messages": messages,
        "temperature": 0.0,
        "stream": False
    }
    
    log.info(f"Querying brain using active model: {ACTIVE_MODEL} via {ACTIVE_URL}")
    try:
        timeout = float(SettingsManager.get("backend_timeout", 30))
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        result = data["choices"][0]["message"]["content"].strip()
        
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
            
        parsed_result = json.loads(result.strip())
        return parsed_result
        
    except Exception as e:
        log.warning(f"Active model {ACTIVE_MODEL} failed: {e}.")
        if retries > 0:
            log.info("Finding a new best model to retry...")
            ACTIVE_MODEL, ACTIVE_URL, ACTIVE_KEY = get_best_model()
            return generate_response(prompt, history, retries=retries-1)
        else:
            log.error("Failed to get response after retrying with new model.")
            return {
                "skill": "done",
                "text": "My brain encountered a critical error processing your request. The model endpoint failed.",
                "thought": f"Failed with {ACTIVE_MODEL}."
            }
