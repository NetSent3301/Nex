import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("nex.llm")


def convert_content_to_openai_messages(
    contents: list | None,
    system_instruction: str | None = None,
) -> list[dict]:
    messages: list[dict] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    for content in (contents or []):
        if content is None:
            continue
        role = getattr(content, "role", "user")
        role = "assistant" if role == "model" else role
        text_parts: list[str] = []
        tool_calls = []
        is_tool_response = False
        for part in (getattr(content, "parts", None) or []):
            if part is None:
                continue
            try:
                if hasattr(part, "text") and part.text is not None:
                    text_parts.append(str(part.text))
            except Exception:
                pass
            try:
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    args = dict(fc.args) if hasattr(fc, "args") and fc.args else {}
                    tool_calls.append({
                        "id": f"call_{fc.name}",
                        "type": "function",
                        "function": {
                            "name": str(fc.name) if hasattr(fc, "name") else "",
                            "arguments": json.dumps(args, ensure_ascii=False),
                        },
                    })
            except Exception:
                pass
            try:
                fr = getattr(part, "function_response", None)
                if fr is not None:
                    is_tool_response = True
                    resp = (
                        dict(fr.response)
                        if hasattr(fr, "response") and fr.response
                        else {}
                    )
                    text_parts.append(json.dumps(resp, ensure_ascii=False))
            except Exception:
                pass
        if is_tool_response:
            messages.append(
                {"role": "tool", "content": "\n".join(text_parts) if text_parts else ""}
            )
        elif tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": "\n".join(text_parts) if text_parts else "",
                    "tool_calls": tool_calls,
                }
            )
        else:
            messages.append(
                {"role": role, "content": "\n".join(text_parts) if text_parts else ""}
            )

    if not messages or all(
        not m.get("content", "").strip() and "tool_calls" not in m
        for m in messages
    ):
        messages = [{"role": "user", "content": "Hello"}]

    return messages


def convert_content_to_anthropic_messages(
    contents: list | None,
    system_instruction: str | None = None,
) -> tuple[str | None, list[dict]]:
    system = system_instruction
    messages: list[dict] = []
    for content in (contents or []):
        if content is None:
            continue
        role = getattr(content, "role", "user")
        role = "assistant" if role == "model" else role
        text_parts: list[str] = []
        tool_uses = []
        is_tool_response = False
        for part in (getattr(content, "parts", None) or []):
            if part is None:
                continue
            try:
                if hasattr(part, "text") and part.text is not None:
                    text_parts.append(str(part.text))
            except Exception:
                pass
            try:
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    args = dict(fc.args) if hasattr(fc, "args") and fc.args else {}
                    tool_uses.append({
                        "type": "tool_use",
                        "id": f"toolu_{fc.name}",
                        "name": str(fc.name) if hasattr(fc, "name") else "",
                        "input": args,
                    })
            except Exception:
                pass
            try:
                fr = getattr(part, "function_response", None)
                if fr is not None:
                    is_tool_response = True
                    resp = (
                        dict(fr.response)
                        if hasattr(fr, "response") and fr.response
                        else {}
                    )
                    text_parts.append(json.dumps(resp, ensure_ascii=False))
            except Exception:
                pass
        if is_tool_response:
            messages.append(
                {"role": "user", "content": "\n".join(text_parts) if text_parts else ""}
            )
        elif tool_uses:
            content_block: list[dict] = []
            if text_parts:
                content_block.append({"type": "text", "text": "\n".join(text_parts)})
            content_block.extend(tool_uses)
            messages.append({"role": "assistant", "content": content_block})
        else:
            messages.append(
                {"role": role, "content": "\n".join(text_parts) if text_parts else ""}
            )

    if not messages or all(
        isinstance(m.get("content"), str) and not m["content"].strip()
        for m in messages
        if isinstance(m.get("content"), str)
    ):
        messages = [{"role": "user", "content": "Hello"}]

    return system, messages


def get_temperature(config=None) -> float:
    if config and hasattr(config, "temperature") and config.temperature is not None:
        return config.temperature
    try:
        from storage.settings import get_settings

        return get_settings().get("temperature", 0.7)
    except Exception:
        return 0.7


async def async_post_json(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: int = 120,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response.json()


def convert_tools_to_openai(tools: list) -> list[dict]:
    def _fn(fd) -> dict:
        return {
            "type": "function",
            "function": {
                "name": fd.get("name", ""),
                "description": fd.get("description", ""),
                "parameters": schema_to_dict(fd.get("parameters", {})),
            },
        }

    result = []
    for tool in tools:
        if isinstance(tool, dict):
            for fd in tool.get("function_declarations", []):
                result.append(_fn(fd))
        else:
            try:
                fds = getattr(tool, "function_declarations", None) or []
                for fd in fds:
                    name = getattr(fd, "name", "") or ""
                    description = getattr(fd, "description", "") or ""
                    params = getattr(fd, "parameters", None)
                    result.append({
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": description,
                            "parameters": schema_to_dict(params),
                        },
                    })
            except Exception:
                pass
    return result


def convert_tools_to_anthropic(tools: list) -> list[dict]:
    anthropic_tools = []
    for t in tools:
        if isinstance(t, dict):
            fds = t.get("function_declarations", [{}])
            for fd in fds:
                anthropic_tools.append({
                    "name": fd.get("name", ""),
                    "description": fd.get("description", ""),
                    "input_schema": schema_to_dict(fd.get("parameters", {})),
                })
            continue
        for fd in getattr(t, "function_declarations", None) or [{}]:
            anthropic_tools.append({
                "name": getattr(fd, "name", "") or "",
                "description": getattr(fd, "description", "") or "",
                "input_schema": schema_to_dict(getattr(fd, "parameters", None)),
            })
    return anthropic_tools


def schema_to_dict(schema) -> dict:
    """Normaliza un esquema de parámetros (dict o Schema de google.genai.types)
    a JSON puro, para poder serializarlo en requests a OpenAI/Anthropic/FreeLLM."""
    if schema is None:
        return {}
    if isinstance(schema, dict):
        result: dict = {}
        for k, v in schema.items():
            if k == "properties" and isinstance(v, dict):
                result[k] = {sk: schema_to_dict(sv) for sk, sv in v.items()}
            elif k == "items":
                result[k] = schema_to_dict(v)
            elif k in ("required", "enum") and isinstance(v, (list, tuple)):
                result[k] = list(v)
            elif k == "type" and isinstance(v, str):
                result[k] = v
            else:
                result[k] = v
        return result

    result: dict = {}
    try:
        t = getattr(schema, "type", None)
        if t is not None:
            result["type"] = t.name.lower() if hasattr(t, "name") else str(t)
    except Exception:
        result["type"] = "object"
    try:
        props = getattr(schema, "properties", None)
        if props:
            result["properties"] = {k: schema_to_dict(v) for k, v in props.items()}
            reqs = getattr(schema, "required", None)
            if reqs:
                result["required"] = list(reqs)
    except Exception:
        pass
    try:
        items = getattr(schema, "items", None)
        if items is not None:
            result["items"] = schema_to_dict(items)
    except Exception:
        pass
    try:
        description = getattr(schema, "description", None)
        if description:
            result["description"] = description
    except Exception:
        pass
    try:
        enum = getattr(schema, "enum", None)
        if enum:
            result["enum"] = list(enum)
    except Exception:
        pass
    return result
