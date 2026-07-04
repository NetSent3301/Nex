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

    def supports_tools(self) -> bool:
        return True
