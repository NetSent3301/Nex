from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: list[dict], tools: list[dict] | None = None) -> str:
        ...

    @abstractmethod
    def generate_sync(self, message: str) -> str:
        ...

    def generate_with_image(self, prompt: str, image_base64: str, mime_type: str = "image/png") -> str:
        return self.generate_sync(f"{prompt}\n[Image: {mime_type}, base64 data ({len(image_base64)} bytes)]")

    def supports_tools(self) -> bool:
        return False

    def supports_images(self) -> bool:
        return False

    def list_models(self) -> list[str]:
        return []
