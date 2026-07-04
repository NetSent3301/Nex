import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from llm.provider import LLMProvider
from llm.key_manager import APIKeyManager
from utils.helpers import get_current_datetime_str, get_system_info
from config.loader import load_system_prompt

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

fecha = get_current_datetime_str()
sistema = get_system_info()
system_prompt = (
    f"{load_system_prompt()}\n\n"
    f"[INFORMACION EN TIEMPO REAL DEL SISTEMA/FECHA]\n"
    f"- Fecha y hora actual: {fecha}\n"
    f"- Información del sistema: {sistema}\n"
)


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
        key_manager: APIKeyManager | None = None,
    ) -> None:
        self._key_manager = key_manager
        if not self._key_manager:
            if api_key:
                self._key_manager = APIKeyManager(keys=[api_key])
            else:
                self._key_manager = APIKeyManager()
        self._client: genai.Client | None = None
        self.model = model

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._key_manager.current_key)
        return self._client

    def _rebuild_client(self) -> genai.Client:
        self._client = genai.Client(api_key=self._key_manager.current_key)
        return self._client

    def _call_with_retry(self, func, max_retries: int = 5, cooldown: int = 120):
        last_error = None
        base_delay = 5
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_error = e
                if not self._key_manager.is_exhausted_error(e):
                    raise
                if attempt == max_retries - 1:
                    raise

                suggested = self._key_manager.get_retry_delay(e)
                if suggested is not None:
                    delay = suggested + 0.5
                    time.sleep(delay)
                    continue

                delay = base_delay * (2 ** attempt)
                rotated = self._key_manager.handle_error(e, cooldown=max(delay, cooldown))
                self._rebuild_client()
                time.sleep(delay)
        raise last_error  # type: ignore

    def generate_content(
        self,
        model: str | None = None,
        contents=None,
        config=None,
        max_retries: int = 3,
    ):
        def call():
            return self.client.models.generate_content(
                model=model or self.model,
                contents=contents,
                config=config,
            )
        return self._call_with_retry(call, max_retries=max_retries)

    async def generate(self, messages: list[dict] | str, tools: list[dict] | None = None):
        config_args = {
            "system_instruction": system_prompt,
            "temperature": 0.2,
        }
        if tools:
            config_args["tools"] = tools

        config = types.GenerateContentConfig(**config_args)

        def call():
            return self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=config,
            )

        return self._call_with_retry(call)

    def generate_sync(self, message: str) -> str:
        config = types.GenerateContentConfig(system_instruction=system_prompt)

        def call():
            return self.client.models.generate_content(
                model=self.model,
                contents=message,
                config=config,
            )

        response = self._call_with_retry(call)
        return response.text

    def generate_with_image(self, prompt: str, image_base64: str, mime_type: str = "image/png") -> str:
        import base64
        img_bytes = base64.b64decode(image_base64)
        config = types.GenerateContentConfig(system_instruction=system_prompt)

        def call():
            return self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                        ],
                    )
                ],
                config=config,
            )

        response = self._call_with_retry(call)
        return response.text

    def list_models(self) -> list[str]:
        return [
            "gemini-2.5-flash",
            "gemini-2.5-flash-8b",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemma-3-27b-it",
        ]

    def supports_images(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        return True
