from unittest.mock import patch

import pytest


def test_list_providers_includes_expected():
    from llm.connect import list_providers

    names = list_providers()
    for expected in ("freellm", "ollama", "gemini", "openai", "anthropic", "deepseek"):
        assert expected in names


def test_provider_status_unknown_raises():
    from llm.connect import provider_status

    with pytest.raises(ValueError, match="desconocido"):
        provider_status("nope")


def test_provider_status_cloud_sin_key_no_hace_red():
    from llm.connect import provider_status

    with patch("os.getenv", return_value=""):
        st = provider_status("openai")
    assert st["kind"] == "cloud"
    assert st["configured"] is False
    assert st["reachable"] is None
    assert st["models"] == []


def test_provider_status_ollama_offline():
    from llm.connect import provider_status

    with patch("llm.connect._reachable", return_value=False):
        st = provider_status("ollama")
    assert st["reachable"] is False


def test_connect_unknown_raises():
    from llm.connect import connect_provider

    with pytest.raises(ValueError, match="desconocido"):
        connect_provider("nope")


def test_connect_cloud_sin_key_raises():
    from llm.connect import connect_provider

    with patch("os.getenv", return_value=""):
        with pytest.raises(RuntimeError, match="API key"):
            connect_provider("openai")


def test_connect_ollama_offline_raises():
    from llm.connect import connect_provider

    with patch("llm.connect._reachable", return_value=False):
        with pytest.raises(RuntimeError, match="no responde"):
            connect_provider("ollama")


def test_build_provider_ollama_and_freellm():
    from llm.factory import build_provider

    ollama = build_provider("ollama")
    assert ollama.__class__.__name__ == "OllamaProvider"

    with patch("storage.settings.get_settings", return_value={"provider": "freellm", "model": ""}):
        freellm = build_provider("freellm")
    assert freellm.__class__.__name__ == "FreeLLMProvider"
    assert freellm.model == "auto"


def test_factory_uses_settings_defaults():
    from llm.factory import build_provider

    settings = {"provider": "freellm", "model": "auto-fast"}
    with patch("storage.settings.get_settings", return_value=settings):
        provider = build_provider()
    assert provider.model == "auto-fast"


def test_get_provider_api_key_freellm():
    import os

    from storage.settings import get_provider_api_key

    assert get_provider_api_key("freellm") == os.getenv("FREELM_API_KEY", "")


def test_reachable_true_aunque_pida_auth():
    import urllib.error

    from llm.connect import _reachable

    with patch(
        "llm.connect.urllib.request.urlopen",
        side_effect=urllib.error.HTTPError("u", 401, "unauthorized", None, None),
    ):
        assert _reachable("http://127.0.0.1:3000/v1/models") is True


def test_reachable_false_sin_conexion():
    from llm.connect import _reachable

    with patch("llm.connect.urllib.request.urlopen", side_effect=OSError("connection refused")):
        assert _reachable("http://127.0.0.1:3000/v1/models") is False
