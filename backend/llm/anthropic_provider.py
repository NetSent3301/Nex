import json
import os
from typing import Any

from llm.provider import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY in .env"
            )
        self.model = model

    async def generate(
        self, messages: list[dict] | str, tools: list[dict] | None = None
    ) -> Any:
        import urllib.request
        import urllib.error

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": messages,
        }

        if tools:
            anthropic_tools = []
            for t in tools:
                fn = t.get("function_declarations", [{}])[0] if "function_declarations" in t else t
                anthropic_tools.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {}),
                })
            if anthropic_tools:
                body["tools"] = anthropic_tools

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode())
                return self._parse_response(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Anthropic API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Anthropic request failed: {e}")

    def generate_sync(self, message: str) -> str:
        import urllib.request
        import urllib.error

        body = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": message}],
        }

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode())
                content = result.get("content", [])
                text_parts = [c["text"] for c in content if c["type"] == "text"]
                return " ".join(text_parts) if text_parts else ""
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Anthropic API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Anthropic request failed: {e}")

    def _parse_response(self, result: dict) -> Any:
        class ResponseWrapper:
            def __init__(self, data: dict):
                self._data = data
                content_blocks = data.get("content", [])

                text_parts = [c["text"] for c in content_blocks if c["type"] == "text"]
                self.text = " ".join(text_parts) if text_parts else ""

                tool_uses = [c for c in content_blocks if c["type"] == "tool_use"]
                self.function_calls = []
                for tu in tool_uses:
                    fc = type('FunctionCall', (), {
                        'name': tu.get("name", ""),
                        'args': tu.get("input", {}),
                    })()
                    self.function_calls.append(fc)

                self.candidates = [type('Candidate', (), {
                    'content': type('Content', (), {
                        'role': 'assistant',
                        'parts': [],
                    })(),
                })()]

        return ResponseWrapper(result)

    def generate_content(self, contents: list = None, config=None):
        from google.genai import types as genai_types

        system_instruction = None
        if config and hasattr(config, 'system_instruction') and config.system_instruction:
            system_instruction = config.system_instruction
        temperature = None
        if config and hasattr(config, 'temperature') and config.temperature is not None:
            temperature = config.temperature
        if temperature is None:
            try:
                from storage.settings import get_settings
                temperature = get_settings().get("temperature", 0.7)
            except Exception:
                temperature = 0.7
        tools = None
        if config and hasattr(config, 'tools') and config.tools:
            tools = config.tools

        messages = []
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
                        args = dict(fc.args) if hasattr(fc, 'args') and fc.args else {}
                        tool_uses.append({
                            "type": "tool_use",
                            "id": f"toolu_{fc.name}",
                            "name": str(fc.name) if hasattr(fc, 'name') else "",
                            "input": args,
                        })
                except Exception:
                    pass
                try:
                    fr = getattr(part, "function_response", None)
                    if fr is not None:
                        is_tool_response = True
                        resp = dict(fr.response) if hasattr(fr, 'response') and fr.response else {}
                        text_parts.append(json.dumps(resp, ensure_ascii=False))
                except Exception:
                    pass
            if is_tool_response:
                messages.append({"role": "user", "content": "\n".join(text_parts) if text_parts else ""})
            elif tool_uses:
                content_block: list[dict] = []
                if text_parts:
                    content_block.append({"type": "text", "text": "\n".join(text_parts)})
                content_block.extend(tool_uses)
                messages.append({"role": "assistant", "content": content_block})
            else:
                messages.append({"role": role, "content": "\n".join(text_parts) if text_parts else ""})

        if not messages or all(
            isinstance(m.get("content"), str) and not m["content"].strip()
            for m in messages if isinstance(m.get("content"), str)
        ):
            messages = [{"role": "user", "content": "Hello"}]

        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": messages,
        }
        if system_instruction:
            body["system"] = system_instruction
        if tools:
            anthropic_tools = []
            for t in tools:
                fn = t.get("function_declarations", [{}])[0] if isinstance(t, dict) and "function_declarations" in t else t
                anthropic_tools.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {}),
                })
            if anthropic_tools:
                body["tools"] = anthropic_tools

        import urllib.request, urllib.error
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                return self._parse_response(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Anthropic API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Anthropic request failed: {e}")

    def list_models(self) -> list[str]:
        return [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    def supports_tools(self) -> bool:
        return True
