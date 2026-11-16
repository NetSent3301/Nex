"""Rutas de configuración: workspace y ajustes de Nex.

Se exponen como CRUD sobre `storage.settings` (backend/.nex_settings.json),
incluyendo importación/exportación/reset y guardado de API keys.
"""

from fastapi import APIRouter, HTTPException

from api.schemas import (
    ProviderInfo,
    SettingsResponse,
    SettingsUpdateRequest,
    WorkspaceResponse,
)
from llm.manager import create_default_manager
from storage.settings import (
    get_settings,
    get_workspace_path,
    save_api_keys,
    update_settings,
)

router = APIRouter()

_SETTINGS_FIELDS = [
    "provider", "model", "temperature", "max_tokens", "top_p",
    "interface_radius", "theme", "language", "font_size",
    "animations_enabled", "compact_mode", "orb_animation",
    "send_mode", "auto_scroll",
    "show_timestamps", "syntax_highlighting",
    "custom_api_urls", "system_prompt", "max_tool_calls",
    "max_sessions", "context_size", "timeout",
    "auto_save_interval",
    "accent_color", "font_family", "sidebar_visible",
    "auto_title", "confirm_delete", "sidebar_width",
]

_IMPORT_ALLOWED_KEYS = {
    "provider", "model", "temperature", "max_tokens", "top_p",
    "interface_radius", "theme", "language", "font_size",
    "animations_enabled", "compact_mode", "orb_animation",
    "send_mode", "auto_scroll", "show_timestamps", "syntax_highlighting",
    "custom_api_urls", "system_prompt", "max_tool_calls",
    "max_sessions", "context_size", "timeout", "auto_save_interval",
    "accent_color", "font_family", "sidebar_visible", "auto_title",
    "confirm_delete", "sidebar_width",
}


@router.get("/api/v1/workspace", response_model=WorkspaceResponse)
async def get_workspace() -> WorkspaceResponse:
    path = get_workspace_path()
    return WorkspaceResponse(path=path or "No configurado")


@router.get("/api/v1/settings", response_model=SettingsResponse)
async def get_settings_endpoint() -> SettingsResponse:
    manager = create_default_manager()
    providers = manager.get_provider_info()

    from llm.ollama_provider import detect_ollama_models, is_ollama_running

    ollama_models = detect_ollama_models()
    if ollama_models or is_ollama_running():
        providers.append({
            "name": "ollama",
            "models": ollama_models,
            "configured": True,
        })

    settings = get_settings()
    return SettingsResponse(
        provider=settings.get("provider", "gemini"),
        model=settings.get("model", "gemini-2.5-flash"),
        temperature=settings.get("temperature", 0.7),
        max_tokens=settings.get("max_tokens", 8192),
        top_p=settings.get("top_p", 0.95),
        providers=[ProviderInfo(**p) for p in providers],
        workspace_path=settings.get("workspace_path", ""),
        interface_radius=settings.get("interface_radius", 12),
        theme=settings.get("theme", "dark"),
        language=settings.get("language", "es"),
        font_size=settings.get("font_size", 14),
        animations_enabled=settings.get("animations_enabled", True),
        compact_mode=settings.get("compact_mode", False),
        orb_animation=settings.get("orb_animation", True),
        send_mode=settings.get("send_mode", "enter"),
        auto_scroll=settings.get("auto_scroll", True),
        show_timestamps=settings.get("show_timestamps", False),
        syntax_highlighting=settings.get("syntax_highlighting", True),
        custom_api_urls=settings.get("custom_api_urls", {}),
        system_prompt=settings.get("system_prompt", ""),
        max_tool_calls=settings.get("max_tool_calls", 10),
        max_sessions=settings.get("max_sessions", 50),
        context_size=settings.get("context_size", 32),
        timeout=settings.get("timeout", 60),
        auto_save_interval=settings.get("auto_save_interval", 60),
    )


@router.post("/api/v1/settings")
async def update_settings_endpoint(req: SettingsUpdateRequest) -> SettingsResponse:
    updates = {}
    for field in _SETTINGS_FIELDS:
        val = getattr(req, field, None)
        if val is not None:
            updates[field] = val

    update_settings(updates)

    if req.api_keys:
        save_api_keys(req.api_keys)

    return await get_settings_endpoint()


@router.get("/api/v1/settings/export")
async def export_settings() -> dict:
    return get_settings()


@router.post("/api/v1/settings/import")
async def import_settings(data: dict) -> SettingsResponse:
    sanitized = {
        k: v for k, v in data.items() if k in _IMPORT_ALLOWED_KEYS
    }
    if not sanitized:
        raise HTTPException(status_code=400, detail="No valid settings keys found")
    if (
        isinstance(sanitized.get("system_prompt"), str)
        and len(sanitized["system_prompt"]) > 10000
    ):
        raise HTTPException(
            status_code=400, detail="System prompt too long (max 10,000 characters)"
        )
    update_settings(sanitized)
    return await get_settings_endpoint()


@router.post("/api/v1/settings/reset")
async def reset_settings() -> SettingsResponse:
    import storage.settings as s
    from dotenv import load_dotenv

    s._save_all({})
    # Reload env
    load_dotenv(s.ENV_FILE, override=True)
    return await get_settings_endpoint()