import json
import os
from typing import Any

import httpx

from llm.provider import LLMProvider
from llm.utils import (
    convert_content_to_openai_messages,
    convert_tools_to_openai,
    get_temperature,
    async_post_json,
)


class OpenAIProvider(LLMProvider):
    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "No OpenAI API key found. Set OPENAI_API_KEY in .env"
            )
        self.model = model

    async def _post(
        self, body: dict[str, Any], timeout: int = 60
    ) -> dict[str, Any]:
        return await async_post_json(
            self.BASE_URL,
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
            body["tools"] = tools
            body["tool_choice"] = "auto"

        result = await self._post(body)
        return self._parse_response(result)

    def generate_sync(self, message: str) -> str:
        import urllib.request
        import urllib.error

        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
        }

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            self.BASE_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode())
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"OpenAI API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"OpenAI request failed: {e}")

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
                self.BASE_URL,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
            return self._parse_response(result)
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"OpenAI API error {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI request failed: {e}")

    def list_models(self) -> list[str]:
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1",
            "o1-mini",
            "o3-mini",
        ]

    def supports_tools(self) -> bool:
        return True

    def supports_images(self) -> bool:
        vision_models = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1"}
        return self.model in vision_models
