import requests
import os
import json
# Ollama default local server (override via OLLAMA_BASE env) e.g. http://localhost:11434
OLLAMA_URL = "http://localhost:11434/api/generate"
# Persist selected model to disk so it survives restarts
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'ollama_settings.json')

def _load_model_from_disk(default_model: str) -> str:
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                m = (data or {}).get('model')
                if isinstance(m, str) and m.strip():
                    return m.strip()
    except Exception:
        # fall back to default
        pass
    return default_model

MODEL_NAME = _load_model_from_disk("qwen3:8b")

_settings = {"temperature": 0.7, "max_tokens": 2048}


def _query_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "options": {
            "temperature": _settings["temperature"],
            "num_predict": _settings["max_tokens"]
        },
        "stream": False,  # we want a blocking full response
    }

    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def generate_response(prompt: str) -> str:
    return _query_ollama(prompt)


def summarize_text(text: str) -> str:
    prompt = f"Summarize this: {text}"
    return generate_response(prompt)


def answer_question(question: str, context: str) -> str:
    prompt = f"Context: {context}\nQuestion: {question}\nAnswer:"
    return generate_response(prompt)


def analyze_pdf(file) -> str:
    # TODO: Implement PDF analysis using Ollama
    return "[PDF analysis not implemented]"


def get_settings():
    return _settings


def set_settings(new_settings):
    _settings.update(new_settings)

# New helpers to manage model from the backend API
def get_model_name() -> str:
    return MODEL_NAME

def set_model_name(name: str):
    global MODEL_NAME
    if not name:
        raise ValueError("Model name cannot be empty")
    MODEL_NAME = name
    # persist to disk
    try:
        with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump({'model': MODEL_NAME}, f)
    except Exception:
        # If persistence fails, continue using in-memory setting
        pass
