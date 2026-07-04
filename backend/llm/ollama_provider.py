import json
import os
import subprocess
import urllib.request
import urllib.error
from typing import Any

from google.genai import types as genai_types
from llm.provider import LLMProvider


def detect_ollama_models() -> list[str]:
    """Detecta modelos de Ollama instalados localmente."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().split("\n")
        models = []
        for line in lines[1:]:
            parts = line.strip().split()
            if parts:
                name = parts[0]
                if ":" not in name:
                    name += ":latest"
                models.append(name)
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return []


def is_ollama_running() -> bool:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        model: str | None = None,
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.base_url = base_url
        self.model = model or self._get_default_model()

    def _get_default_model(self) -> str:
        models = detect_ollama_models()
        if models:
            return models[0]
        return "llama3.2:latest"

    def list_models(self) -> list[str]:
        return detect_ollama_models()

    async def generate(
        self, messages: list[dict] | str, tools: list[dict] | None = None
    ) -> Any:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        if tools:
            body["tools"] = tools

        try:
            result = self._call_ollama(body)
            return self._parse_response(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Ollama API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def generate_sync(self, message: str) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "stream": False,
        }

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode())
                return result.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Ollama API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def generate_with_image(self, prompt: str, image_base64: str) -> str:
        body = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [image_base64],
            }],
            "stream": False,
        }

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode())
                return result.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Ollama API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def _history_to_messages(self, contents: list, system_instruction: str | None = None) -> list[dict]:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        for content in contents:
            if content is None:
                continue
            role = getattr(content, "role", "user")
            role = "assistant" if role == "model" else role

            text_parts: list[str] = []
            image_parts: list[str] = []
            tool_calls: list[dict] = []
            is_function_response = False

            parts = getattr(content, "parts", None) or []
            for part in parts:
                if part is None:
                    continue
                try:
                    if hasattr(part, "text") and part.text is not None:
                        text_parts.append(str(part.text))
                except Exception:
                    pass
                try:
                    if hasattr(part, "inline_data") and part.inline_data is not None:
                        import base64
                        b64 = base64.b64encode(part.inline_data.data).decode()
                        image_parts.append(b64)
                except Exception:
                    pass
                try:
                    fc = getattr(part, "function_call", None)
                    if fc is not None:
                        try:
                            args = dict(fc.args) if hasattr(fc, 'args') and fc.args else {}
                        except Exception:
                            args = {}
                        tool_calls.append({
                            "function": {
                                "name": str(fc.name) if hasattr(fc, 'name') else "",
                                "arguments": args,
                            }
                        })
                except Exception:
                    pass
                try:
                    fr = getattr(part, "function_response", None)
                    if fr is not None:
                        is_function_response = True
                        try:
                            resp = dict(fr.response) if hasattr(fr, 'response') and fr.response else {}
                        except Exception:
                            resp = {}
                        text_parts.append(json.dumps(resp, ensure_ascii=False))
                except Exception:
                    pass

            if is_function_response:
                messages.append({
                    "role": "tool",
                    "content": "\n".join(text_parts) if text_parts else "",
                })
            elif tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": "\n".join(text_parts) if text_parts else "",
                    "tool_calls": tool_calls,
                })
            else:
                msg: dict = {"role": role, "content": "\n".join(text_parts) if text_parts else ""}
                if image_parts:
                    msg["images"] = image_parts
                messages.append(msg)
        return messages

    def _tools_to_ollama(self, tools: list) -> list[dict]:
        result = []
        if not tools:
            return result
        for tool in tools:
            if tool is None:
                continue
            # Support both dict format (from registry) and object format (from genai SDK)
            if isinstance(tool, dict):
                fds = tool.get("function_declarations") or []
            else:
                fds = list(getattr(tool, 'function_declarations', []) or [])
            for fd in fds:
                if fd is None:
                    continue
                if isinstance(fd, dict):
                    params = fd.get("parameters") or {}
                    result.append({
                        "type": "function",
                        "function": {
                            "name": fd.get("name", ""),
                            "description": fd.get("description", ""),
                            "parameters": self._schema_to_dict(params),
                        },
                    })
                else:
                    params = getattr(fd, 'parameters', None) or {}
                    result.append({
                        "type": "function",
                        "function": {
                            "name": getattr(fd, 'name', ''),
                            "description": getattr(fd, 'description', ''),
                            "parameters": self._schema_to_dict(params),
                        },
                    })
        return result

    def _schema_to_dict(self, schema) -> dict:
        if schema is None:
            return {}
        # Handle plain dict
        if isinstance(schema, dict):
            result: dict = {}
            for k, v in schema.items():
                if k == "properties" and isinstance(v, dict):
                    result[k] = {sk: self._schema_to_dict(sv) for sk, sv in v.items()}
                elif k == "items" and v is not None:
                    result[k] = self._schema_to_dict(v)
                elif k == "required" and isinstance(v, list):
                    result[k] = list(v)
                elif k == "enum" and isinstance(v, list):
                    result[k] = list(v)
                elif k == "type":
                    result[k] = str(v).lower() if isinstance(v, str) else str(v)
                else:
                    result[k] = v
            return result
        # Handle Gemini SDK Schema object
        result = {}
        try:
            if hasattr(schema, 'type') and schema.type is not None:
                result["type"] = schema.type.name.lower() if hasattr(schema.type, 'name') else str(schema.type)
            elif hasattr(schema, 'type_') and schema.type_ is not None:
                result["type"] = schema.type_.name.lower() if hasattr(schema.type_, 'name') else str(schema.type_)
        except Exception:
            result["type"] = "object"
        try:
            if hasattr(schema, 'properties') and schema.properties:
                result["properties"] = {
                    k: self._schema_to_dict(v) for k, v in schema.properties.items()
                }
                if hasattr(schema, 'required') and schema.required:
                    result["required"] = list(schema.required)
        except Exception:
            pass
        try:
            if hasattr(schema, 'items') and schema.items:
                result["items"] = self._schema_to_dict(schema.items)
        except Exception:
            pass
        try:
            if hasattr(schema, 'description') and schema.description:
                result["description"] = schema.description
        except Exception:
            pass
        try:
            if hasattr(schema, 'enum') and schema.enum:
                result["enum"] = list(schema.enum)
        except Exception:
            pass
        return result

    def _call_ollama(self, body: dict) -> dict:
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as response:
            return json.loads(response.read().decode())

    def generate_content(
        self,
        model: str | None = None,
        contents=None,
        config=None,
        max_retries: int = 3,
    ):
        model_name = model or self.model
        system_instruction = None
        tools = None
        temperature = None

        if config:
            try:
                if hasattr(config, "system_instruction") and config.system_instruction:
                    system_instruction = config.system_instruction
            except Exception:
                pass
            try:
                if hasattr(config, "tools") and config.tools:
                    tools = config.tools
            except Exception:
                pass
            try:
                if hasattr(config, "temperature") and config.temperature is not None:
                    temperature = config.temperature
            except Exception:
                pass

        # Use settings temperature as fallback
        if temperature is None:
            try:
                from storage.settings import get_settings
                temperature = get_settings().get("temperature", 0.7)
            except Exception:
                temperature = 0.7

        messages = self._history_to_messages(contents or [], system_instruction)
        ollama_tools = self._tools_to_ollama(tools) if tools else None

        body: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            body.setdefault("options", {})["temperature"] = temperature

        # Validate messages
        if not messages or all(
            not m.get("content", "").strip() and "tool_calls" not in m
            for m in messages
        ):
            body["messages"] = [{"role": "user", "content": "Hello"}]

        # First attempt: with tools
        if ollama_tools:
            body["tools"] = ollama_tools
            try:
                result = self._call_ollama(body)
                return self._parse_response(result)
            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                if e.code == 400:
                    body.pop("tools", None)
                else:
                    raise RuntimeError(f"Ollama API error {e.code}: {error_body}")
            except Exception as e:
                raise RuntimeError(f"Ollama request failed: {e}")

        # Second attempt (or first if no tools): without tools
        try:
            result = self._call_ollama(body)
            return self._parse_response(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Ollama API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def _parse_response(self, result: dict) -> Any:
        class ResponseWrapper:
            def __init__(self, data: dict):
                self._data = data
                message = data.get("message") or {}
                self.text = message.get("content") or ""

                tool_calls_raw = data.get("tool_calls") or message.get("tool_calls") or []
                if isinstance(tool_calls_raw, dict):
                    tool_calls_raw = [tool_calls_raw]
                self.function_calls = []
                parts = []

                if self.text:
                    parts.append(genai_types.Part.from_text(text=self.text))

                for tc in tool_calls_raw:
                    if tc is None:
                        continue
                    fn = tc.get("function") if isinstance(tc, dict) else {}
                    if not fn:
                        continue
                    name = fn.get("name", "")
                    raw_args = fn.get("arguments", {})
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except Exception:
                            raw_args = {}
                    if not isinstance(raw_args, dict):
                        raw_args = {}

                    fc = type('FunctionCall', (), {
                        'name': name,
                        'args': raw_args,
                    })()
                    self.function_calls.append(fc)
                    try:
                        parts.append(genai_types.Part(
                            function_call=genai_types.FunctionCall(
                                name=name,
                                args=raw_args,
                            )
                        ))
                    except Exception:
                        pass

                try:
                    self.candidates = [type('Candidate', (), {
                        'content': type('Content', (), {
                            'role': 'assistant',
                            'parts': parts,
                        })(),
                    })()]
                except Exception:
                    self.candidates = []

        return ResponseWrapper(result)

    def supports_tools(self) -> bool:
        return True

    def supports_images(self) -> bool:
        vision_keywords = ["vision", "llava", "moondream", "gemma3", "llama3.2-vision"]
        model_lower = self.model.lower()
        return any(kw in model_lower for kw in vision_keywords)
