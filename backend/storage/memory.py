# backend/storage/memory.py
import json
import os
from datetime import datetime, timezone

from google.genai import types

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".nex_history.json")
MAX_HISTORY_MESSAGES = 20


def _get_history_file(session_id: str = "default") -> str:
    s_id = session_id or "default"
    if s_id == "default":
        return HISTORY_FILE
    import re
    s_id = re.sub(r'[^a-zA-Z0-9_\-]', '', s_id)
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f".nex_history_{s_id}.json"
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_parts(parts: list[types.Part]) -> list[dict]:
    serialized = []
    for p in parts:
        if p.text is not None:
            serialized.append({"type": "text", "text": p.text})
        elif p.function_call is not None:
            serialized.append({
                "type": "function_call",
                "name": p.function_call.name,
                "args": dict(p.function_call.args),
            })
        elif p.function_response is not None:
            serialized.append({
                "type": "function_response",
                "name": p.function_response.name,
                "response": dict(p.function_response.response),
            })
    return serialized


def _deserialize_parts(data: list[dict]) -> list[types.Part]:
    parts = []
    for item in data:
        t = item["type"]
        if t == "text":
            parts.append(types.Part.from_text(text=item["text"]))
        elif t == "function_call":
            parts.append(types.Part.from_function_call(
                name=item["name"], args=dict(item["args"])
            ))
        elif t == "function_response":
            parts.append(types.Part.from_function_response(
                name=item["name"], response=dict(item["response"])
            ))
    return parts


def save_chat_history(messages: list, session_id: str = "default") -> None:
    serialized = []
    for m in messages:
        if isinstance(m, str):
            serialized.append({
                "type": "text",
                "role": "user",
                "content": m,
            })
        elif isinstance(m, types.Content):
            serialized.append({
                "type": "content",
                "role": m.role,
                "parts": _serialize_parts(m.parts),
            })

    data = {"updated_at": _now(), "messages": serialized}
    history_file = _get_history_file(session_id)

    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
            data["created_at"] = existing.get("created_at", _now())
        except (json.JSONDecodeError, FileNotFoundError):
            data["created_at"] = _now()
    else:
        data["created_at"] = _now()

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_chat_history(session_id: str = "default") -> list:
    history_file = _get_history_file(session_id)
    if not os.path.exists(history_file):
        return []

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    messages = []
    for item in data.get("messages", []):
        if item["type"] == "text":
            messages.append(item["content"])
        elif item["type"] == "content":
            messages.append(types.Content(
                role=item["role"],
                parts=_deserialize_parts(item["parts"]),
            ))
    return messages


def trim_messages(messages: list, max_messages: int = MAX_HISTORY_MESSAGES) -> list:
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


def clear_history(session_id: str = "default") -> None:
    history_file = _get_history_file(session_id)
    if os.path.exists(history_file):
        os.remove(history_file)
