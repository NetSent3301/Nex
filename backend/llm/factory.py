"""Construcción de proveedores LLM a partir de settings.

Fuente única para API (`api/routes/chat.py`) y CLI (`nex`): dado un nombre de
provider y un modelo (o los defaults de `backend/.nex_settings.json`) devuelve
la instancia concreta del provider.
"""


def build_provider(name: str | None = None, model: str | None = None):
    """Devuelve una instancia del provider solicitado usando los settings.

    Si `name` o `model` no se pasan, se leen de `get_settings()`. Los providers
    cloud lanzan ValueError si no hay API key configurada.
    """
    from storage.settings import get_settings

    settings = get_settings()
    provider_name = name or settings.get("provider", "gemini")
    selected_model = model or settings.get("model", "")

    if provider_name == "ollama" or provider_name.startswith("ollama/"):
        from llm.ollama_provider import OllamaProvider, detect_ollama_models

        if not selected_model:
            models = detect_ollama_models()
            selected_model = models[0] if models else ""
        return OllamaProvider(model=selected_model) if selected_model else OllamaProvider()

    if provider_name == "openai":
        from llm.openai_provider import OpenAIProvider

        return OpenAIProvider(model=selected_model or "gpt-4o")

    if provider_name == "anthropic":
        from llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=selected_model or "claude-sonnet-4-20250514")

    if provider_name == "deepseek":
        from llm.deepseek_provider import DeepSeekProvider

        return DeepSeekProvider(model=selected_model or "deepseek-chat")

    if provider_name == "freellm":
        from llm.freellm_provider import FreeLLMProvider

        return FreeLLMProvider(model=selected_model or "auto")

    from llm.gemini import GeminiProvider

    return GeminiProvider(model=selected_model or "gemini-2.5-flash")
