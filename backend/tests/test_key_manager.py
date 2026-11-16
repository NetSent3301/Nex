import time

import pytest

from llm.key_manager import APIKeyManager


def _clear_key_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_BACKUP", raising=False)
    for i in range(1, 10):
        monkeypatch.delenv(f"GEMINI_API_KEY_{i}", raising=False)


def test_discover_keys_dedups(monkeypatch):
    _clear_key_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "key-a")
    monkeypatch.setenv("GEMINI_API_KEY_BACKUP", "key-a")
    monkeypatch.setenv("GEMINI_API_KEY_1", "key-b")
    assert APIKeyManager().all_keys() == ["key-a", "key-b"]


def test_constructor_dedups_and_preserves_order():
    km = APIKeyManager(keys=["b", "a", "b", "a"])
    assert km.all_keys() == ["b", "a"]
    assert km.current_key == "b"
    assert km.key_count == 2


def test_missing_keys_raises():
    with pytest.raises(ValueError):
        APIKeyManager(keys=[])


def test_rotate_cycles():
    km = APIKeyManager(keys=["a", "b"])
    assert km.rotate() == "b"
    assert km.current_key == "b"
    assert km.rotate() == "a"
    assert km.current_key == "a"


def test_rotate_skips_blacklisted():
    km = APIKeyManager(keys=["a", "b", "c"])
    assert km.blacklist_current(300) == "b"
    assert km.rotate() == "c"


def test_blacklist_current_returns_next_available():
    km = APIKeyManager(keys=["a", "b", "c"])
    assert km.blacklist_current(300) == "b"
    assert km.current_key == "b"


def test_blacklist_current_returns_none_when_all_suspended():
    km = APIKeyManager(keys=["a", "b"])
    assert km.blacklist_current(300) == "b"
    assert km.blacklist_current(300) is None


def test_select_available_none_when_all_suspended():
    km = APIKeyManager(keys=["a", "b"])
    km.blacklist_current(300)
    km.blacklist_current(300)
    assert km.select_available() is None


def test_select_available_after_expiry():
    km = APIKeyManager(keys=["a", "b"])
    km.blacklist_current(0.05)
    km.blacklist_current(0.05)
    assert km.select_available() is None
    time.sleep(0.12)
    assert km.select_available() is not None


def test_time_until_available_zero_when_free():
    km = APIKeyManager(keys=["a"])
    assert km.time_until_available() == 0.0


def test_time_until_available_when_all_suspended():
    km = APIKeyManager(keys=["a", "b"])
    km.blacklist_current(0.05)
    km.blacklist_current(0.05)
    wait = km.time_until_available(cap=10.0)
    assert 0.0 < wait <= 0.1


def test_handle_error_blacklists_current():
    km = APIKeyManager(keys=["a", "b"])
    assert km.handle_error(RuntimeError("quota exceeded"), cooldown=300) == "b"
    assert km.current_key == "b"
    assert km.select_available() is not None


def test_get_retry_delay_seconds():
    km = APIKeyManager(keys=["a"])
    assert km.get_retry_delay(RuntimeError("Please retry in 3.5s")) == 3.5


def test_get_retry_delay_retrydelay_json():
    km = APIKeyManager(keys=["a"])
    error = RuntimeError('429 Resource exhausted. retryDelay: {"seconds": 30}')
    assert km.get_retry_delay(error) == 30.0


def test_get_retry_delay_none():
    km = APIKeyManager(keys=["a"])
    assert km.get_retry_delay(RuntimeError("boom")) is None


@pytest.mark.parametrize(
    "message",
    [
        "quota exceeded",
        "rate limit reached",
        "Resource has been exhausted (e.g. check quota)",
        "daily limit reached",
    ],
)
def test_is_exhausted_error_true(message: str):
    assert APIKeyManager(keys=["a"]).is_exhausted_error(RuntimeError(message))


def test_is_exhausted_error_false():
    assert not APIKeyManager(keys=["a"]).is_exhausted_error(RuntimeError("key invalid"))
