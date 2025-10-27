import requests
import os
import json
# Ollama default local server (override via OLLAMA_BASE env) e.g. http://localhost:11434
# If OLLAMA_BASE is provided, build URLs from it; else use localhost default
_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434").rstrip("/")
OLLAMA_URL = f"{_BASE}/api/generate"
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

_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "30"))

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

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.Timeout:
        try:
            print("OLLAMA DEBUG: Timeout on generate (first path)")
        except Exception:
            pass
        return ""
    except requests.RequestException as e:
        try:
            print(f"OLLAMA DEBUG: RequestException on generate: {type(e).__name__}: {str(e).splitlines()[0]}")
        except Exception:
            pass
        return ""
    except Exception as e:
        try:
            print(f"OLLAMA DEBUG: Unexpected error on generate: {type(e).__name__}: {str(e).splitlines()[0]}")
        except Exception:
            pass
        return ""
    except Exception:
        return ""


def _query_ollama_with_options(prompt: str, *, temperature: float | None = None, max_tokens: int | None = None, model: str | None = None) -> str:
    """Query Ollama with per-call overrides without mutating global settings."""
    payload = {
        "model": model or MODEL_NAME,
        "prompt": prompt,
        "options": {
            "temperature": _settings["temperature"] if temperature is None else temperature,
            "num_predict": _settings["max_tokens"] if max_tokens is None else max_tokens,
        },
        "stream": False,
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.Timeout:
        try:
            print("OLLAMA DEBUG: Timeout on generate_with_options")
        except Exception:
            pass
        return ""
    except requests.RequestException as e:
        try:
            print(f"OLLAMA DEBUG: RequestException on generate_with_options: {type(e).__name__}: {str(e).splitlines()[0]}")
        except Exception:
            pass
        return ""
    except Exception as e:
        try:
            print(f"OLLAMA DEBUG: Unexpected error on generate_with_options: {type(e).__name__}: {str(e).splitlines()[0]}")
        except Exception:
            pass
        return ""
    except Exception:
        return ""


def generate_response(prompt: str) -> str:
    return _query_ollama(prompt)


def generate_response_with_options(prompt: str, *, temperature: float | None = None, max_tokens: int | None = None, model: str | None = None) -> str:
    return _query_ollama_with_options(prompt, temperature=temperature, max_tokens=max_tokens, model=model)


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
