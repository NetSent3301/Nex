import json
import os
from typing import Any

from llm.provider import LLMProvider


class DeepSeekProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "deepseek-chat",
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "No DeepSeek API key found. Set DEEPSEEK_API_KEY in .env"
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
            "messages": messages,
        }

        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode())
                return self._parse_response(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"DeepSeek API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"DeepSeek request failed: {e}")

    def generate_sync(self, message: str) -> str:
        import urllib.request
        import urllib.error

        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
        }

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
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
            raise RuntimeError(f"DeepSeek API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"DeepSeek request failed: {e}")

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

    def supports_tools(self) -> bool:
        return True
