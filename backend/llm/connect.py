"""Conexión y diagnóstico de proveedores LLM.

Backing de `nex providers` y `nex connect <provider>`: detecta reachability y
modelos de los providers locales (FreeLLM, Ollama), persiste API keys y base
URLs, y deja el provider/modelo activos en `backend/.nex_settings.json`.
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

PROVIDERS: dict[str, dict] = {
    "freellm": {
        "label": "FreeLLM (agregador multi-proveedor local)",
        "kind": "local",
        "env_var": "FREELM_API_KEY",
        "base_url_env": "FREELM_BASE_URL",
        "default_base_url": "http://127.0.0.1:3000/v1",
        "default_model": "auto",
        "health_path": "/models",
    },
    "ollama": {
        "label": "Ollama (modelos locales)",
        "kind": "local",
        "env_var": None,
        "base_url_env": "OLLAMA_BASE_URL",
        "default_base_url": "http://127.0.0.1:11434",
        "default_model": None,
        "health_path": "/api/tags",
    },
    "gemini": {
        "label": "Google Gemini",
        "kind": "cloud",
        "env_var": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
    },
    "openai": {
        "label": "OpenAI",
        "kind": "cloud",
        "env_var": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "kind": "cloud",
        "env_var": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
    },
    "deepseek": {
        "label": "DeepSeek",
        "kind": "cloud",
        "env_var": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
}


def list_providers() -> list[str]:
    return list(PROVIDERS.keys())


def _get_json(url: str, headers: dict[str, str] | None = None, timeout: float = 3.0) -> dict | None:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def _reachable(url: str, timeout: float = 3.0) -> bool:
    """True si el servidor responde en `url`, aunque devuelva 401/400 (p.ej. pide auth)."""
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout):  # noqa: S310
            return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError):
        return False


def _resolve_base_url(name: str) -> str:
    info = PROVIDERS[name]
    env = os.getenv(info["base_url_env"], "").strip() if info.get("base_url_env") else ""
    return env.rstrip("/") or info.get("default_base_url", "")


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-2:]}"


def _freellm_models(base_url: str) -> list[str]:
    key = os.getenv("FREELM_API_KEY", "")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    data = _get_json(f"{base_url}/models", headers=headers)
    if not data:
        return []
    return sorted(m.get("id", "") for m in data.get("data", []) if m.get("id"))


def _ollama_models(base_url: str) -> list[str]:
    data = _get_json(f"{base_url}/api/tags")
    if not data:
        return []
    return sorted(m.get("name", "") for m in data.get("models", []) if m.get("name"))


def _detect_models(name: str, base_url: str) -> list[str]:
    if name == "freellm":
        return _freellm_models(base_url)
    if name == "ollama":
        return _ollama_models(base_url)
    return []


def provider_status(name: str) -> dict:
    if name not in PROVIDERS:
        raise ValueError(
            f"Provider '{name}' desconocido. Disponibles: {', '.join(list_providers())}"
        )
    info = PROVIDERS[name]
    from storage.settings import get_settings

    key = os.getenv(info["env_var"], "") if info["env_var"] else ""
    configured = bool(key) if info.get("env_var") else True
    reachable: bool | None = None
    base_url = ""
    models: list[str] = []

    if info["kind"] == "local":
        base_url = _resolve_base_url(name)
        reachable = _reachable(f"{base_url}{info['health_path']}")
        if reachable:
            models = _detect_models(name, base_url)
    else:
        if configured:
            try:
                from llm.factory import build_provider

                models = build_provider(name).list_models()
            except Exception:
                models = []

    return {
        "name": name,
        "label": info["label"],
        "kind": info["kind"],
        "configured": configured,
        "key_masked": _mask_key(key) if (key and info.get("env_var")) else None,
        "base_url": base_url,
        "reachable": reachable,
        "models": models,
        "default_model": info["default_model"],
        "active": get_settings().get("provider") == name,
    }


def all_providers_status() -> list[dict]:
    return [provider_status(name) for name in list_providers()]


def start_freellm(port: int = 3000) -> tuple[subprocess.Popen | None, str]:
    """Arranca FreeLLM (npx freellm) desacoplado y espera a que responda."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    frontend_dir = os.path.join(root, "frontend")
    cmd = [
        "npx", "--prefix", frontend_dir,
        "freellm", "--port", str(port), "--no-open",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        return None, f"No se pudo lanzar FreeLLM: {e}"

    base_url = f"http://127.0.0.1:{port}/v1"
    for _ in range(30):
        if _reachable(f"{base_url}/models", timeout=1.0):
            return proc, f"FreeLLM listo en {base_url}"
        if proc.poll() is not None:
            return None, "FreeLLM terminó inesperadamente al arrancar"
        time.sleep(0.5)
    return proc, "FreeLLM no respondió a tiempo"


def connect_provider(
    name: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    set_active: bool = True,
) -> dict:
    """Conecta un provider: persiste credenciales/URL y lo deja como activo."""
    if name not in PROVIDERS:
        raise ValueError(
            f"Provider '{name}' desconocido. Disponibles: {', '.join(list_providers())}"
        )
    from storage.settings import get_settings, save_api_keys, save_env_var, update_settings

    info = PROVIDERS[name]
    steps: list[str] = []

    if api_key and info.get("env_var"):
        saved = save_api_keys({name: api_key})
        if saved.get(name):
            steps.append(f"API key guardada en .env ({info['env_var']})")
        else:
            steps.append(f"⚠️ No se pudo guardar la API key ({info['env_var']})")

    resolved_url = _resolve_base_url(name)
    if base_url:
        if info.get("base_url_env"):
            resolved_url = base_url.rstrip("/")
            save_env_var(info["base_url_env"], resolved_url)
            steps.append(f"Base URL guardada en .env ({info['base_url_env']}={resolved_url})")
        else:
            steps.append(f"⚠️ {name} no usa base URL personalizada; se ignora")
    elif name == "freellm" and not resolved_url:
        resolved_url = info["default_base_url"].rstrip("/")

    if name == "freellm":
        reachable = _reachable(f"{resolved_url}{info['health_path']}")
        if not reachable:
            raise RuntimeError(
                f"FreeLLM no responde en {resolved_url}. Arranca el agregador con:\n"
                "  nex connect freellm --start\n  o  ./start-freellm.sh"
            )
        steps.append(f"FreeLLM accesible en {resolved_url}")
    elif name == "ollama":
        reachable = _reachable(f"{resolved_url}{info['health_path']}")
        if not reachable:
            raise RuntimeError(f"Ollama no responde en {resolved_url}")
        steps.append(f"Ollama accesible en {resolved_url}")
    elif not (api_key or os.getenv(info["env_var"], "")):
        raise RuntimeError(
            f"{name} requiere API key: pasa --key <valor> o configúrala en .env ({info['env_var']})"
        )

    if model is None:
        if name == "freellm":
            model = info["default_model"]
        elif name == "ollama":
            models = _ollama_models(resolved_url)
            model = models[0] if models else get_settings().get("model", "")
        else:
            model = info["default_model"]

    if set_active:
        update_settings({"provider": name, "model": model})
        active_label = model or "auto"
        steps.append(f"Proveedor activo: {name} (modelo: {active_label})")

    return {
        "provider": name,
        "ok": True,
        "steps": steps,
        "status": provider_status(name),
    }
