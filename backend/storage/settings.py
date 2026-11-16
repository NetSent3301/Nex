import json
import os

from dotenv import load_dotenv

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".nex_settings.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

# Autoritativo: cualquier proceso que use settings carga las API keys de .env
# (load_dotenv no sobreescribe variables ya presentes en el entorno).
load_dotenv(ENV_FILE)


def _load_all() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_all(data: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_workspace_path(path: str) -> str:
    absolute_path = os.path.abspath(path)
    data = _load_all()
    data["workspace_path"] = absolute_path
    _save_all(data)
    return absolute_path


def get_workspace_path() -> str | None:
    env_path = os.environ.get("NEX_WORKSPACE")
    if env_path:
        return os.path.abspath(env_path)
    data = _load_all()
    return data.get("workspace_path")


def get_settings() -> dict:
    data = _load_all()
    return {
        "provider": data.get("provider", "gemini"),
        "model": data.get("model", "gemini-2.5-flash"),
        "temperature": data.get("temperature", 0.7),
        "max_tokens": data.get("max_tokens", 8192),
        "top_p": data.get("top_p", 0.95),
        "workspace_path": data.get("workspace_path", ""),
        "interface_radius": data.get("interface_radius", 12),
        "theme": data.get("theme", "dark"),
        "language": data.get("language", "es"),
        "font_size": data.get("font_size", 14),
        "animations_enabled": data.get("animations_enabled", True),
        "compact_mode": data.get("compact_mode", False),
        "orb_animation": data.get("orb_animation", True),
        "send_mode": data.get("send_mode", "enter"),
        "auto_scroll": data.get("auto_scroll", True),
        "show_timestamps": data.get("show_timestamps", False),
        "syntax_highlighting": data.get("syntax_highlighting", True),
        "custom_api_urls": data.get("custom_api_urls", {}),
        "system_prompt": data.get("system_prompt", ""),
        "max_tool_calls": data.get("max_tool_calls", 10),
        "max_sessions": data.get("max_sessions", 50),
        "context_size": data.get("context_size", 32),
        "timeout": data.get("timeout", 60),
        "auto_save_interval": data.get("auto_save_interval", 60),
        "sidebar_width": data.get("sidebar_width", 270),
        "accent_color": data.get("accent_color", "#6366f1"),
        "font_family": data.get("font_family", "'Inter', system-ui, -apple-system, sans-serif"),
        "sidebar_visible": data.get("sidebar_visible", True),
        "auto_title": data.get("auto_title", True),
        "confirm_delete": data.get("confirm_delete", True),
        "explain_mode": data.get("explain_mode", True),
        "scan_allowlist": data.get("scan_allowlist", "127.0.0.1"),
    }


def update_settings(updates: dict) -> dict:
    data = _load_all()
    allowed = {
        "provider", "model", "temperature", "max_tokens", "top_p",
        "interface_radius", "theme", "language", "font_size",
        "animations_enabled", "compact_mode", "orb_animation",
        "send_mode", "auto_scroll",
        "show_timestamps", "syntax_highlighting",
        "custom_api_urls", "system_prompt", "max_tool_calls",
        "max_sessions", "context_size", "timeout",
        "auto_save_interval",
        "sidebar_width",
        "accent_color",
        "font_family",
        "sidebar_visible",
        "auto_title",
        "confirm_delete",
        "explain_mode", "scan_allowlist",
    }
    for key, value in updates.items():
        if key in allowed and value is not None:
            data[key] = value
    _save_all(data)
    return get_settings()


def save_env_var(key: str, value: str) -> str:
    """Persiste una variable de entorno en backend/.env y la inyecta en el proceso."""
    existing: dict[str, str] = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()
    existing[key] = value
    os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    os.environ[key] = value
    return value


def save_api_keys(keys: dict[str, str]) -> dict[str, bool]:
    results = {}
    lines = []
    env_providers = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "freellm": "FREELM_API_KEY",
    }

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = []

    existing = {}
    for line in lines:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            existing[k.strip()] = v.strip()

    for provider, key in keys.items():
        if not key:
            continue
        env_var = env_providers.get(provider)
        if env_var:
            existing[env_var] = key
            results[provider] = True
        else:
            results[provider] = False

    new_lines = []
    for k, v in existing.items():
        new_lines.append(f"{k}={v}\n")

    os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    os.environ.update({k: v for k, v in existing.items()})
    return results


def get_provider_api_key(provider: str) -> str:
    env_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "freellm": "FREELM_API_KEY",
    }
    env_var = env_map.get(provider)
    if not env_var:
        return ""
    return os.getenv(env_var, "")
