import json
import os
from typing import Any

import httpx

from llm.provider import LLMProvider
from llm.utils import (
    convert_content_to_anthropic_messages,
    convert_tools_to_anthropic,
    get_temperature,
    async_post_json,
)


class AnthropicProvider(LLMProvider):
    BASE_URL = "https://api.anthropic.com/v1/messages"

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

    async def _post(
        self, body: dict[str, Any], timeout: int = 120
    ) -> dict[str, Any]:
        return await async_post_json(
            self.BASE_URL,
            {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            body,
            timeout=timeout,
        )

    async def generate(
        self, messages: list[dict] | str, tools: list[dict] | None = None
    ) -> Any:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": messages,
        }

        if tools:
            anthropic_tools = convert_tools_to_anthropic(tools)
            if anthropic_tools:
                body["tools"] = anthropic_tools

        result = await self._post(body)
        return self._parse_response(result)

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
            self.BASE_URL,
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
        system_instruction = None
        if (
            config
            and hasattr(config, "system_instruction")
            and config.system_instruction
        ):
            system_instruction = config.system_instruction
        temperature = get_temperature(config)
        tools = None
        if config and hasattr(config, "tools") and config.tools:
            tools = config.tools

        system, messages = convert_content_to_anthropic_messages(
            contents, system_instruction
        )

        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 8192,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            body["system"] = system
        if tools:
            anthropic_tools = convert_tools_to_anthropic(tools)
            if anthropic_tools:
                body["tools"] = anthropic_tools

        try:
            resp = httpx.post(
                self.BASE_URL,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()
            return self._parse_response(result)
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Anthropic API error {e.response.status_code}: {e.response.text}"
            )
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
