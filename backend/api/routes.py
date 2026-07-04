import base64
import json
import os

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from api.schemas import (
    ChatRequest, ChatResponse, MetricsResponse, WorkspaceResponse,
    SettingsResponse, SettingsUpdateRequest, ProviderInfo, OllamaModelsResponse,
)
from config.loader import load_system_prompt
from storage.memory import MAX_HISTORY_MESSAGES, load_chat_history, save_chat_history, trim_messages
from storage.settings import get_workspace_path, get_settings, update_settings, save_api_keys
from tools.registry import create_default_registry

app = FastAPI(title="Nex", version="0.1.0-dev")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_INDEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "index.html")


def _get_provider(provider_name: str | None = None, model_name: str | None = None):
    from llm.manager import create_default_manager
    manager = create_default_manager()

    name = provider_name or get_settings().get("provider", "gemini")

    if name == "ollama" or name.startswith("ollama/"):
        from llm.ollama_provider import OllamaProvider, detect_ollama_models
        models = detect_ollama_models()
        selected = model_name or get_settings().get("model", "")
        if not selected and models:
            selected = models[0]
        return OllamaProvider(model=selected) if selected else OllamaProvider()

    if name in ("openai",):
        from llm.openai_provider import OpenAIProvider
        model = model_name or get_settings().get("model", "gpt-4o")
        return OpenAIProvider(model=model)

    if name in ("anthropic",):
        from llm.anthropic_provider import AnthropicProvider
        model = model_name or get_settings().get("model", "claude-sonnet-4-20250514")
        return AnthropicProvider(model=model)

    if name in ("deepseek",):
        from llm.deepseek_provider import DeepSeekProvider
        model = model_name or get_settings().get("model", "deepseek-chat")
        return DeepSeekProvider(model=model)

    from llm.gemini import GeminiProvider
    model = model_name or get_settings().get("model", "gemini-2.5-flash")
    return GeminiProvider(model=model)


@app.get("/")
async def web_ui() -> FileResponse:
    return FileResponse(WEB_INDEX)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "agent": "Nex"}


@app.get("/api/v1/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    memory_pct = 0.0
    cpu_pct = 0.0

    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
            mem_total = int(lines[0].split()[1])
            mem_avail = int(lines[2].split()[1])
            memory_pct = round((1 - mem_avail / mem_total) * 100, 1)
    except Exception:
        memory_pct = 0.0

    try:
        import time
        prev_idle = prev_total = 0
        with open("/proc/stat") as f:
            fields = f.readline().split()
            prev_idle = int(fields[4])
            prev_total = sum(int(v) for v in fields[1:])
        time.sleep(0.1)
        with open("/proc/stat") as f:
            fields = f.readline().split()
            idle = int(fields[4])
            total = sum(int(v) for v in fields[1:])
        delta_idle = idle - prev_idle
        delta_total = total - prev_total
        cpu_pct = round((1 - delta_idle / delta_total) * 100, 1) if delta_total else 0.0
    except Exception:
        cpu_pct = 0.0

    return MetricsResponse(
        memory=memory_pct,
        context_buffer=max(0, min(100, memory_pct * 0.6)),
        agent_status="online",
        cpu=cpu_pct,
    )


@app.get("/api/v1/workspace", response_model=WorkspaceResponse)
async def get_workspace() -> WorkspaceResponse:
    path = get_workspace_path()
    return WorkspaceResponse(path=path or "No configurado")


@app.get("/api/v1/settings", response_model=SettingsResponse)
async def get_settings_endpoint() -> SettingsResponse:
    from llm.manager import create_default_manager
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
        send_mode=settings.get("send_mode", "enter"),
        auto_scroll=settings.get("auto_scroll", True),
        show_timestamps=settings.get("show_timestamps", False),
        syntax_highlighting=settings.get("syntax_highlighting", True),
        custom_api_urls=settings.get("custom_api_urls", {}),
        system_prompt=settings.get("system_prompt", ""),
        max_tool_calls=settings.get("max_tool_calls", 10),
        auto_save_interval=settings.get("auto_save_interval", 60),
    )


@app.post("/api/v1/settings")
async def update_settings_endpoint(req: SettingsUpdateRequest) -> SettingsResponse:
    updates = {}
    fields = [
        "provider", "model", "temperature", "max_tokens", "top_p",
        "interface_radius", "theme", "language", "font_size",
        "animations_enabled", "send_mode", "auto_scroll",
        "show_timestamps", "syntax_highlighting",
        "custom_api_urls", "system_prompt", "max_tool_calls",
        "auto_save_interval",
    ]
    for field in fields:
        val = getattr(req, field, None)
        if val is not None:
            updates[field] = val

    update_settings(updates)

    if req.api_keys:
        save_api_keys(req.api_keys)

    return await get_settings_endpoint()


@app.get("/api/v1/ollama/models", response_model=OllamaModelsResponse)
async def get_ollama_models() -> OllamaModelsResponse:
    from llm.ollama_provider import detect_ollama_models, is_ollama_running
    return OllamaModelsResponse(
        models=detect_ollama_models(),
        running=is_ollama_running(),
    )


@app.get("/api/v1/settings/export")
async def export_settings() -> dict:
    return get_settings()


@app.post("/api/v1/settings/import")
async def import_settings(data: dict) -> SettingsResponse:
    update_settings(data)
    return await get_settings_endpoint()


@app.post("/api/v1/settings/reset")
async def reset_settings() -> SettingsResponse:
    import storage.settings as s
    s._save_all({})
    # Reload env
    from dotenv import load_dotenv
    load_dotenv(s.ENV_FILE, override=True)
    return await get_settings_endpoint()


@app.post("/api/v1/clear-history")
async def clear_all_history() -> dict:
    import shutil, glob as g
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    pattern = os.path.join(data_dir, "*.json")
    deleted = 0
    for f in g.glob(pattern):
        if "settings" not in f:
            os.remove(f)
            deleted += 1
    return {"success": True, "deleted": deleted}


@app.post("/api/v1/upload/image")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    contents = await file.read()

    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 20 MB)")

    b64 = base64.b64encode(contents).decode("utf-8")

    return {
        "success": True,
        "filename": file.filename,
        "mime_type": file.content_type,
        "size_kb": round(len(contents) / 1024, 1),
        "image_data": b64,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    workspace_root = get_workspace_path()
    if not workspace_root:
        raise HTTPException(
            status_code=400,
            detail="No hay un Workspace activo. Configúralo con: set-workspace <ruta>",
        )

    try:
        system_instruction = load_system_prompt()
    except Exception:
        from llm.gemini import system_prompt as fallback_prompt
        system_instruction = fallback_prompt

    provider = _get_provider(request.provider, request.model)

    from google.genai import types

    registry = create_default_registry()
    tools_metadata = registry.get_all_tools_metadata()

    historial_previo = load_chat_history(request.session_id)
    historial_previo = trim_messages(historial_previo, MAX_HISTORY_MESSAGES)

    user_parts = [types.Part.from_text(text=request.message)]

    if request.image_data and request.image_mime:
        try:
            img_bytes = base64.b64decode(request.image_data)
            user_parts.append(types.Part.from_bytes(data=img_bytes, mime_type=request.image_mime))
        except Exception:
            pass

    chat_history = historial_previo + [
        types.Content(role="user", parts=user_parts)
    ]

    MAX_ITERATIONS = 10

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools_metadata,
        temperature=0.2,
    )

    try:
        response = provider.generate_content(
            contents=chat_history,
            config=config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del proveedor LLM: {e}")

    for iteration in range(MAX_ITERATIONS):

        if not response.function_calls:
            try:
                chat_history.append(response.candidates[0].content)
            except Exception:
                pass
            final_reply = response.text or ""
            save_chat_history(chat_history, request.session_id)
            return ChatResponse(response=final_reply)

        try:
            chat_history.append(response.candidates[0].content)
        except Exception:
            pass

        for call in response.function_calls:
            tool_name = call.name
            tool_args = dict(call.args)
            tool_args["workspace_root"] = workspace_root

            try:
                tool = registry.get(tool_name)
                tool_result = tool.execute(**tool_args)
            except Exception as e:
                tool_result = {"success": False, "error": str(e)}

            chat_history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=tool_name, response=tool_result
                        )
                    ],
                )
            )

        try:
            response = provider.generate_content(
                contents=chat_history,
                config=config,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error del proveedor LLM en iteración {iteration+1}: {e}")

    final_reply = "Lo siento, la operación tomó demasiadas iteraciones. Intenta de nuevo con una instrucción más simple."
    save_chat_history(chat_history, request.session_id)
    return ChatResponse(response=final_reply)


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    workspace_root = get_workspace_path()
    if not workspace_root:
        raise HTTPException(
            status_code=400,
            detail="No hay un Workspace activo. Configúralo con: set-workspace <ruta>",
        )

    try:
        system_instruction = load_system_prompt()
    except Exception:
        from llm.gemini import system_prompt as fallback_prompt
        system_instruction = fallback_prompt

    provider = _get_provider(request.provider, request.model)

    from google.genai import types

    registry = create_default_registry()
    tools_metadata = registry.get_all_tools_metadata()

    historial_previo = load_chat_history(request.session_id)
    historial_previo = trim_messages(historial_previo, MAX_HISTORY_MESSAGES)

    user_parts = [types.Part.from_text(text=request.message)]

    if request.image_data and request.image_mime:
        try:
            img_bytes = base64.b64decode(request.image_data)
            user_parts.append(types.Part.from_bytes(data=img_bytes, mime_type=request.image_mime))
        except Exception:
            pass

    chat_history = historial_previo + [
        types.Content(role="user", parts=user_parts)
    ]

    MAX_ITERATIONS = 10

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools_metadata,
        temperature=0.2,
    )

    def event_stream():
        nonlocal chat_history
        try:
            response = provider.generate_content(
                contents=chat_history,
                config=config,
            )
        except Exception as e:
            yield f"event: text\ndata: {json.dumps(f'⚠️ Error del proveedor: {e}')}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        for iteration in range(MAX_ITERATIONS):
            if not response.function_calls:
                try:
                    chat_history.append(response.candidates[0].content)
                except Exception:
                    pass
                final_reply = response.text or ""
                chunk_size = 40
                for i in range(0, len(final_reply), chunk_size):
                    chunk = final_reply[i:i + chunk_size]
                    yield f"event: text\ndata: {json.dumps(chunk)}\n\n"
                try:
                    save_chat_history(chat_history, request.session_id)
                except Exception:
                    pass
                yield "event: done\ndata: {}\n\n"
                return

            try:
                chat_history.append(response.candidates[0].content)
            except Exception:
                pass

            for call in response.function_calls:
                tool_name = call.name
                tool_args = dict(call.args)
                tool_args["workspace_root"] = workspace_root

                yield f"event: tool_start\ndata: {json.dumps({'tool': tool_name, 'args': tool_args})}\n\n"

                try:
                    tool = registry.get(tool_name)
                    tool_result = tool.execute(**tool_args)
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}

                yield f"event: tool_end\ndata: {json.dumps({'tool': tool_name, 'result': tool_result})}\n\n"

                chat_history.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=tool_name, response=tool_result
                            )
                        ],
                    )
                )

            try:
                response = provider.generate_content(
                    contents=chat_history,
                    config=config,
                )
            except Exception as e:
                yield f"event: text\ndata: {json.dumps(f'⚠️ Error del proveedor en iteración {iteration+1}: {e}')}\n\n"
                yield "event: done\ndata: {}\n\n"
                return

        yield f"event: text\ndata: {json.dumps('⚠️ La operación tomó demasiadas iteraciones.')}\n\n"
        try:
            save_chat_history(chat_history, request.session_id)
        except Exception:
            pass
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
