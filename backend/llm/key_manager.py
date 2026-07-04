import os
import json
import time
import random
from dotenv import load_dotenv
from typing import Optional

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".nex_keys.json")


def _discover_keys() -> list[str]:
    keys: list[str] = []

    raw = os.getenv("GEMINI_API_KEY", "")
    if raw:
        keys.append(raw)

    for i in range(1, 10):
        k = os.getenv(f"GEMINI_API_KEY_{i}", "")
        if k:
            keys.append(k)

    backup = os.getenv("GEMINI_API_KEY_BACKUP", "")
    if backup and backup not in keys:
        keys.append(backup)

    return keys


class APIKeyManager:
    def __init__(self, keys: Optional[list[str]] = None) -> None:
        self._keys = keys or _discover_keys()
        self._index = 0
        self._blacklisted_until: dict[str, float] = {}

        if not self._keys:
            raise ValueError(
                "No hay API keys disponibles. Configura GEMINI_API_KEY en .env"
            )

    @property
    def current_key(self) -> str:
        return self._keys[self._index]

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def all_keys(self) -> list[str]:
        return list(self._keys)

    def rotate(self) -> str:
        self._index = (self._index + 1) % len(self._keys)
        return self.current_key

    def blacklist_current(self, cooldown_seconds: int = 60) -> None:
        self._blacklisted_until[self.current_key] = time.time() + cooldown_seconds
        self._try_skip_blacklisted()

    def _try_skip_blacklisted(self) -> None:
        now = time.time()
        for _ in range(len(self._keys)):
            key = self.current_key
            if key not in self._blacklisted_until or self._blacklisted_until[key] <= now:
                return
            self._index = (self._index + 1) % len(self._keys)

    def is_exhausted_error(self, error: Exception) -> bool:
        code = getattr(error, "code", None)
        if code == 429:
            return True
        msg = str(error).lower()
        if "quota" in msg or "resource exhausted" in msg or "rate limit" in msg or "daily limit" in msg:
            return True
        return False

    def handle_error(self, error: Exception, cooldown: int = 120) -> str:
        self.blacklist_current(cooldown)
        return self.current_key
