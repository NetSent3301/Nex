"""Rutas de chat: chat autónomo multi-paso (POST /api/chat) y streaming SSE.

Ambos comparten el mismo bucle: historial persistente + tools + llamadas al
proveedor LLM configurado hasta obtener una respuesta final.
"""
import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.genai import types

from api.schemas import ChatRequest, ChatResponse
from config.loader import build_system_prompt
from storage.memory import (
    MAX_HISTORY_MESSAGES,
    load_chat_history,
    save_chat_history,
    trim_messages,
)
from storage.settings import get_settings, get_workspace_path
from tools.registry import create_default_registry

logger = logging.getLogger("nex.api.chat")

router = APIRouter()

MAX_ITERATIONS = 10


def _get_provider(provider_name: str | None = None, model_name: str | None = None):
    from llm.factory import build_provider

    return build_provider(provider_name, model_name)


def _build_history(request: ChatRequest) -> list[Any]:
    historial_previo = trim_messages(
        load_chat_history(request.session_id), MAX_HISTORY_MESSAGES
    )

    user_parts = [types.Part.from_text(text=request.message)]
    if request.image_data and request.image_mime:
        try:
            img_bytes = base64.b64decode(request.image_data)
            user_parts.append(
                types.Part.from_bytes(data=img_bytes, mime_type=request.image_mime)
            )
        except Exception as e:
            logger.error(f"Failed to decode image: {e}")

    return historial_previo + [types.Content(role="user", parts=user_parts)]


def _build_config(system_instruction: str, tools_metadata: list[dict]) -> Any:
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools_metadata,
        temperature=0.2,
    )


def _execute_tool(registry, tool_name: str, tool_args: dict) -> dict:
    try:
        tool = registry.get(tool_name)
        return tool.execute(**tool_args)
    except Exception as e:
        return {"success": False, "error": str(e)}


def _load_system_instruction(workspace_root: str, lang: str) -> str:
    try:
        return build_system_prompt(workspace_root=workspace_root, language=lang)
    except Exception as e:
        logger.error(f"Failed to load system prompt: {e}")
        from llm.gemini import system_prompt as fallback_prompt

        return fallback_prompt


def _require_workspace() -> str:
    workspace_root = get_workspace_path()
    if not workspace_root:
        raise HTTPException(
            status_code=400,
            detail="No hay un Workspace activo. Configúralo con: set-workspace <ruta>",
        )
    return workspace_root


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if len(request.message) > 50000:
        raise HTTPException(status_code=400, detail="Message too long (max 50,000 characters)")
    if request.image_data and len(request.image_data) > 20 * 1024 * 1024 * 4 // 3:
        raise HTTPException(status_code=400, detail="Image data too large (max 20 MB)")

    workspace_root = _require_workspace()
    lang = request.language or get_settings().get("language", "es")
    system_instruction = _load_system_instruction(workspace_root, lang)

    provider = _get_provider(request.provider, request.model)
    registry = create_default_registry()
    tools_metadata = registry.get_all_tools_metadata()

    chat_history = _build_history(request)
    config = _build_config(system_instruction, tools_metadata)

    try:
        response = provider.generate_content(contents=chat_history, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del proveedor LLM: {e}")

    for iteration in range(MAX_ITERATIONS):
        if not response.function_calls:
            try:
                chat_history.append(response.candidates[0].content)
            except Exception as e:
                logger.error(f"Failed to append assistant response to history: {e}")
            final_reply = response.text or ""
            save_chat_history(chat_history, request.session_id)
            return ChatResponse(response=final_reply)

        try:
            chat_history.append(response.candidates[0].content)
        except Exception as e:
            logger.error(f"Failed to append function call response to history: {e}")

        for call in response.function_calls:
            tool_args = dict(call.args)
            tool_args["workspace_root"] = workspace_root
            tool_result = _execute_tool(registry, call.name, tool_args)

            chat_history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=call.name, response=tool_result
                        )
                    ],
                )
            )

        try:
            response = provider.generate_content(contents=chat_history, config=config)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error del proveedor LLM en iteración {iteration + 1}: {e}",
            )

    final_reply = "Lo siento, la operación tomó demasiadas iteraciones. Intenta de nuevo con una instrucción más simple."
    save_chat_history(chat_history, request.session_id)
    return ChatResponse(response=final_reply)


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    workspace_root = _require_workspace()
    lang = request.language or get_settings().get("language", "es")
    explain_hint = ""
    if get_settings().get("explain_mode", True):
        explain_hint = (
            "\n\n[MODO EXPLICADOR ACTIVADO]\n"
            "Antes de ejecutar cada herramienta, escribe UNA frase breve (1 línea) en el idioma del usuario "
            "explicando POR QUÉ la usas, por ejemplo: 'Voy a consultar el DNS para ver dónde apunta el dominio.' "
            "Después ejecuta la herramienta y continúa normalmente."
        )
    system_instruction = (
        _load_system_instruction(workspace_root, lang) + f"\n\n{explain_hint}"
    )

    provider = _get_provider(request.provider, request.model)
    registry = create_default_registry()
    tools_metadata = registry.get_all_tools_metadata()

    chat_history = _build_history(request)
    config = _build_config(system_instruction, tools_metadata)

    def event_stream():
        nonlocal chat_history
        try:
            response = provider.generate_content(contents=chat_history, config=config)
        except Exception as e:
            yield f"event: text\ndata: {json.dumps(f'⚠️ Error del proveedor: {e}')}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        for iteration in range(MAX_ITERATIONS):
            if not response.function_calls:
                try:
                    chat_history.append(response.candidates[0].content)
                except Exception as e:
                    logger.error(f"Failed to append response to stream history: {e}")
                final_reply = response.text or ""
                chunk_size = 40
                for i in range(0, len(final_reply), chunk_size):
                    chunk = final_reply[i:i + chunk_size]
                    yield f"event: text\ndata: {json.dumps(chunk)}\n\n"
                try:
                    save_chat_history(chat_history, request.session_id)
                except Exception as e:
                    logger.error(f"Failed to save stream chat history: {e}")
                yield "event: done\ndata: {}\n\n"
                return

            try:
                chat_history.append(response.candidates[0].content)
            except Exception as e:
                logger.error(f"Failed to append function call to stream history: {e}")

            for call in response.function_calls:
                tool_name = call.name
                tool_args = dict(call.args)
                tool_args["workspace_root"] = workspace_root

                tool = None
                tool_description = ""
                try:
                    tool = registry.get(tool_name)
                    tool_description = tool.description
                except Exception:
                    tool_description = ""

                yield f"event: tool_start\ndata: {json.dumps({'tool': tool_name, 'args': tool_args, 'description': tool_description})}\n\n"

                try:
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
                response = provider.generate_content(contents=chat_history, config=config)
            except Exception as e:
                yield f"event: text\ndata: {json.dumps(f'⚠️ Error del proveedor en iteración {iteration+1}: {e}')}\n\n"
                yield "event: done\ndata: {}\n\n"
                return

        yield f"event: text\ndata: {json.dumps('⚠️ La operación tomó demasiadas iteraciones.')}\n\n"
        try:
            save_chat_history(chat_history, request.session_id)
        except Exception as e:
            logger.error(f"Failed to save final stream chat history: {e}")
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
