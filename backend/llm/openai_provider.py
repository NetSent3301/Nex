import json
import os
from typing import Any

from llm.provider import LLMProvider
from llm.key_manager import APIKeyManager


class OpenAIProvider(LLMProvider):
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

    async def generate(
        self, messages: list[dict] | str, tools: list[dict] | None = None
    ) -> Any:
        import urllib.request
        import urllib.error

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages if isinstance(messages, list) else [
                {"role": "user", "content": messages}
            ],
        }

        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode())
                return self._parse_response(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"OpenAI API error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"OpenAI request failed: {e}")

    def generate_sync(self, message: str) -> str:
        import urllib.request
        import urllib.error

        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
        }

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
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
        from google.genai import types as genai_types

        if config and hasattr(config, 'system_instruction') and config.system_instruction:
            system_instruction = config.system_instruction
        else:
            system_instruction = None
        temperature = None
        if config and hasattr(config, 'temperature') and config.temperature is not None:
            temperature = config.temperature
        # Fall back to settings
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
                        args = dict(fc.args) if hasattr(fc, 'args') and fc.args else {}
                        tool_calls.append({
                            "id": f"call_{fc.name}",
                            "type": "function",
                            "function": {
                                "name": str(fc.name) if hasattr(fc, 'name') else "",
                                "arguments": json.dumps(args, ensure_ascii=False),
                            },
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
                messages.append({"role": "tool", "content": "\n".join(text_parts) if text_parts else ""})
            elif tool_calls:
                messages.append({"role": "assistant", "content": "\n".join(text_parts) if text_parts else "", "tool_calls": tool_calls})
            else:
                messages.append({"role": role, "content": "\n".join(text_parts) if text_parts else ""})

        if not messages or all(not m.get("content", "").strip() and "tool_calls" not in m for m in messages):
            messages = [{"role": "user", "content": "Hello"}]

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        import urllib.request, urllib.error
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return self._parse_response(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"OpenAI API error {e.code}: {error_body}")
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
