from llm.provider import LLMProvider


class LLMManager:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, name: str, provider: LLMProvider) -> None:
        self._providers[name] = provider

    def register_all(self, **providers: LLMProvider) -> None:
        for name, provider in providers.items():
            self.register(name, provider)

    def get(self, name: str) -> LLMProvider:
        if name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(
                f"Provider '{name}' not found. Available providers: {available or 'none'}"
            )
        return self._providers[name]

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def has_provider(self, name: str) -> bool:
        return name in self._providers

    def get_provider_info(self) -> list[dict]:
        info = []
        for name, provider in self._providers.items():
            models = []
            try:
                models = provider.list_models()
            except Exception:
                pass
            info.append({
                "name": name,
                "models": models,
                "configured": True,
            })
        return info


def create_default_manager() -> LLMManager:
    manager = LLMManager()

    try:
        from llm.gemini import GeminiProvider
        manager.register("gemini", GeminiProvider())
    except Exception:
        pass

    try:
        from llm.openai_provider import OpenAIProvider
        manager.register("openai", OpenAIProvider())
    except Exception:
        pass

    try:
        from llm.anthropic_provider import AnthropicProvider
        manager.register("anthropic", AnthropicProvider())
    except Exception:
        pass

    try:
        from llm.deepseek_provider import DeepSeekProvider
        manager.register("deepseek", DeepSeekProvider())
    except Exception:
        pass

    try:
        from llm.ollama_provider import OllamaProvider
        ollama = OllamaProvider()
        models = ollama.list_models()
        if models:
            manager.register("ollama", ollama)
        else:
            for model in models:
                try:
                    manager.register(f"ollama/{model}", OllamaProvider(model=model))
                except Exception:
                    pass
    except Exception:
        pass

    return manager
