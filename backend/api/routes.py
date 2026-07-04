import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from api.schemas import ChatRequest, ChatResponse, MetricsResponse, WorkspaceResponse
from config.loader import load_system_prompt
from llm.gemini import GeminiProvider
from storage.memory import MAX_HISTORY_MESSAGES, load_chat_history, save_chat_history, trim_messages
from storage.settings import get_workspace_path
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

    from google.genai import types

    provider = GeminiProvider()
    registry = create_default_registry()
    tools_metadata = registry.get_all_tools_metadata()

    historial_previo = load_chat_history(request.session_id)
    historial_previo = trim_messages(historial_previo, MAX_HISTORY_MESSAGES)
    chat_history = historial_previo + [
        types.Content(role="user", parts=[types.Part.from_text(text=request.message)])
    ]

    MAX_ITERATIONS = 10

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools_metadata,
        temperature=0.2,
    )

    response = provider.generate_content(
        contents=chat_history,
        config=config,
    )

    for iteration in range(MAX_ITERATIONS):

        if not response.function_calls:
            chat_history.append(response.candidates[0].content)
            final_reply = response.text
            save_chat_history(chat_history, request.session_id)
            return ChatResponse(response=final_reply)

        chat_history.append(response.candidates[0].content)

        for call in response.function_calls:
            tool_name = call.name
            tool_args = dict(call.args)
            tool_args["workspace_root"] = workspace_root

            tool = registry.get(tool_name)
            try:
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

        response = provider.generate_content(
            contents=chat_history,
            config=config,
        )

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

    from google.genai import types

    provider = GeminiProvider()
    registry = create_default_registry()
    tools_metadata = registry.get_all_tools_metadata()

    historial_previo = load_chat_history(request.session_id)
    historial_previo = trim_messages(historial_previo, MAX_HISTORY_MESSAGES)
    chat_history = historial_previo + [
        types.Content(role="user", parts=[types.Part.from_text(text=request.message)])
    ]

    MAX_ITERATIONS = 10

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools_metadata,
        temperature=0.2,
    )

    def event_stream():
        nonlocal chat_history
        response = provider.generate_content(
            contents=chat_history,
            config=config,
        )

        for iteration in range(MAX_ITERATIONS):
            if not response.function_calls:
                chat_history.append(response.candidates[0].content)
                final_reply = response.text or ""
                # Stream final text in chunks
                chunk_size = 40
                for i in range(0, len(final_reply), chunk_size):
                    chunk = final_reply[i:i + chunk_size]
                    yield f"event: text\ndata: {json.dumps(chunk)}\n\n"
                save_chat_history(chat_history, request.session_id)
                yield "event: done\ndata: {}\n\n"
                return

            chat_history.append(response.candidates[0].content)

            for call in response.function_calls:
                tool_name = call.name
                tool_args = dict(call.args)
                tool_args["workspace_root"] = workspace_root

                yield f"event: tool_start\ndata: {json.dumps({'tool': tool_name, 'args': tool_args})}\n\n"

                tool = registry.get(tool_name)
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

            response = provider.generate_content(
                contents=chat_history,
                config=config,
            )

        yield f"event: text\ndata: {json.dumps('La operación tomó demasiadas iteraciones.')}\n\n"
        save_chat_history(chat_history, request.session_id)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
