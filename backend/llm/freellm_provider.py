import json
import os
from typing import Any

import httpx

from llm.provider import LLMProvider
from llm.utils import (
    async_post_json,
    convert_content_to_openai_messages,
    convert_tools_to_openai,
    get_temperature,
)

FREELM_DEFAULT_BASE_URL = "http://localhost:3000/v1"


class FreeLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "auto",
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("FREELM_API_KEY", "")
        self.model = model
        self.base_url = (
            base_url or os.getenv("FREELM_BASE_URL", FREELM_DEFAULT_BASE_URL)
        ).rstrip("/")

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    async def _post(
        self, body: dict[str, Any], timeout: int = 120
    ) -> dict[str, Any]:
        return await async_post_json(
            self._build_url("chat/completions"),
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            body,
            timeout=timeout,
        )

    async def generate(
        self, messages: list[dict] | str, tools: list[dict] | None = None
    ) -> Any:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages
            if isinstance(messages, list)
            else [{"role": "user", "content": messages}],
        }

        if tools:
            body["tools"] = convert_tools_to_openai(tools)
            body["tool_choice"] = "auto"

        result = await self._post(body)
        return self._parse_response(result)

    def generate_sync(self, message: str) -> str:
        import urllib.error
        import urllib.request

        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
        }

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            self._build_url("chat/completions"),
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode())
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"FreeLLM API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"FreeLLM request failed: {e}")

    def _parse_response(self, result: dict) -> Any:
        class ResponseWrapper:
            def __init__(self, data: dict):
                self._data = data
                self.text = data["choices"][0]["message"]["content"] or ""
                message = data["choices"][0]["message"]

                tool_calls_raw = message.get("tool_calls", []) or []
                self.function_calls = []
                for tc in tool_calls_raw:
                    fn = tc.get("function", {})
                    fc = type('FunctionCall', (), {
                        'name': fn.get("name", ""),
                        'args': json.loads(fn.get("arguments", "{}")),
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

        messages = convert_content_to_openai_messages(contents, system_instruction)

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = convert_tools_to_openai(tools)
            body["tool_choice"] = "auto"

        try:
            resp = httpx.post(
                self._build_url("chat/completions"),
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()
            return self._parse_response(result)
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"FreeLLM API error {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            raise RuntimeError(f"FreeLLM request failed: {e}")

    def list_models(self) -> list[str]:
        return [
            "auto",
            "auto-fast",
            "auto-smart",
        ]

    def supports_tools(self) -> bool:
        return True

    def supports_images(self) -> bool:
        return True
