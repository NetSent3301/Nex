import os
import re
import threading
import time
from typing import Optional

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

RETRY_PATTERNS = [
    re.compile(r"retry in\s+([\d.]+)\s*s", re.IGNORECASE),
    re.compile(r'"seconds"\s*:\s*(\d+)', re.IGNORECASE),
]


def _discover_keys() -> list[str]:
    names = (
        ["GEMINI_API_KEY"]
        + [f"GEMINI_API_KEY_{i}" for i in range(1, 10)]
        + ["GEMINI_API_KEY_BACKUP"]
    )
    keys: list[str] = []
    for name in names:
        value = os.getenv(name, "").strip()
        if value and value not in keys:
            keys.append(value)
    return keys


class APIKeyManager:
    def __init__(self, keys: Optional[list[str]] = None) -> None:
        self._keys: list[str] = []
        seen: set[str] = set()
        for key in (keys if keys is not None else _discover_keys()):
            stripped = key.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                self._keys.append(stripped)
        self._index = 0
        self._blacklisted_until: dict[str, float] = {}
        self._lock = threading.RLock()

        if not self._keys:
            raise ValueError(
                "No hay API keys disponibles. Configura GEMINI_API_KEY en .env"
            )

    @property
    def current_key(self) -> str:
        with self._lock:
            return self._keys[self._index]

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def all_keys(self) -> list[str]:
        return list(self._keys)

    def rotate(self) -> Optional[str]:
        """Avanza a la siguiente clave, saltándose las suspendidas.

        Devuelve la clave seleccionada o None si todas están suspendidas.
        """
        with self._lock:
            return self._advance_locked()

    def select_available(self) -> Optional[str]:
        """Selecciona una clave no suspendida empezando por la actual.

        Devuelve la clave elegida o None si todas están suspendidas.
        """
        now = time.time()
        with self._lock:
            for _ in range(len(self._keys)):
                key = self._keys[self._index]
                if self._blacklisted_until.get(key, 0.0) <= now:
                    return key
                self._index = (self._index + 1) % len(self._keys)
            return None

    def blacklist_current(self, cooldown_seconds: float) -> Optional[str]:
        """Suspende la clave actual y trata de pasar a la siguiente disponible.

        Devuelve la nueva clave o None si todas quedan suspendidas.
        """
        with self._lock:
            self._blacklisted_until[self.current_key] = time.time() + max(
                0.1, cooldown_seconds
            )
            return self._advance_locked()

    def time_until_available(self, cap: float = 30.0) -> float:
        """Segundos hasta que alguna clave esté disponible (0.0 si ya hay).

        Útil para esperar cuando todas las claves están suspendidas.
        """
        now = time.time()
        with self._lock:
            if any(self._blacklisted_until.get(key, 0.0) <= now for key in self._keys):
                return 0.0
            earliest = min(self._blacklisted_until.values())
            return max(0.1, min(earliest - now, cap))

    def get_retry_delay(self, error: Exception) -> Optional[float]:
        for pattern in RETRY_PATTERNS:
            match = pattern.search(str(error))
            if match:
                return float(match.group(1))
        return None

    def is_exhausted_error(self, error: Exception) -> bool:
        code = getattr(error, "code", None)
        if code == 429:
            return True
        msg = str(error).lower()
        exhausted_markers = ("quota", "resource exhausted", "rate limit", "daily limit")
        if any(marker in msg for marker in exhausted_markers):
            return True
        return False

    def handle_error(self, error: Exception, cooldown: int = 120) -> Optional[str]:
        return self.blacklist_current(cooldown)

    def _advance_locked(self) -> Optional[str]:
        now = time.time()
        for _ in range(len(self._keys)):
            self._index = (self._index + 1) % len(self._keys)
            key = self._keys[self._index]
            if self._blacklisted_until.get(key, 0.0) <= now:
                return key
        return None
