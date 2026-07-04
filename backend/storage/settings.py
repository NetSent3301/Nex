import os
import json

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".nex_settings.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


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
        "send_mode": data.get("send_mode", "enter"),
        "auto_scroll": data.get("auto_scroll", True),
        "show_timestamps": data.get("show_timestamps", False),
        "syntax_highlighting": data.get("syntax_highlighting", True),
        "custom_api_urls": data.get("custom_api_urls", {}),
        "system_prompt": data.get("system_prompt", ""),
        "max_tool_calls": data.get("max_tool_calls", 10),
        "auto_save_interval": data.get("auto_save_interval", 60),
    }


def update_settings(updates: dict) -> dict:
    data = _load_all()
    allowed = {
        "provider", "model", "temperature", "max_tokens", "top_p",
        "interface_radius", "theme", "language", "font_size",
        "animations_enabled", "send_mode", "auto_scroll",
        "show_timestamps", "syntax_highlighting",
        "custom_api_urls", "system_prompt", "max_tool_calls",
        "auto_save_interval",
    }
    for key, value in updates.items():
        if key in allowed and value is not None:
            data[key] = value
    _save_all(data)
    return get_settings()


def save_api_keys(keys: dict[str, str]) -> dict[str, bool]:
    results = {}
    lines = []
    env_providers = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
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
    }
    env_var = env_map.get(provider)
    if not env_var:
        return ""
    return os.getenv(env_var, "")
