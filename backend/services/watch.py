"""Nex Watch: vigila el workspace y registra/bloquea actividad peligrosa.

Auto-arranca con el servidor (lifespan en api/routes.py), persiste las alertas
en backend/storage/.nex_alerts.json y se engancha a run_command para registrar
(como comando bloqueado) cualquier comando peligroso que intente ejecutar el
agente.
"""

import json
import logging
import os
import re
import threading
from datetime import datetime, timezone

from config.loader import WORKSPACE_SKIP_DIRS
from storage.settings import get_settings, get_workspace_path

logger = logging.getLogger("nex.watch")

ALERTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage",
    ".nex_alerts.json",
)

MAX_ALERTS = 500
MAX_COMMANDS = 200

SENSITIVE_NAMES = (
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
)
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".ppk")

SECRET_KEY_RE = re.compile(
    r"(?:api[_-]?key|token|secret|password|passwd|private[_-]?key|"
    r"aws_access_key|authorization)\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+]{12,}",
    re.IGNORECASE,
)

MAX_SECRETS_PER_SCAN = 10
MAX_FILE_SIZE = 64 * 1024


class _NexWatchService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._alerts: list[dict] = []
        self._commands: list[dict] = []
        self._previous_file_count: int | None = None
        self._previous_sensitive: set[str] = set()
        self._load()

    # ── Persistencia ────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if os.path.exists(ALERTS_FILE):
                with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._alerts = list(data.get("alerts", []))[:MAX_ALERTS]
                self._commands = list(data.get("commands", []))[:MAX_COMMANDS]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"No se pudieron cargar las alertas de Nex Watch: {e}")
            self._alerts = []
            self._commands = []

    def _dump(self) -> None:
        try:
            os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)
            with open(ALERTS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"alerts": self._alerts, "commands": self._commands},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except OSError as e:
            logger.error(f"No se pudieron persistir las alertas de Nex Watch: {e}")

    # ── Ciclo de vida ───────────────────────────────────────────────

    def start(self) -> None:
        settings = get_settings()
        if not settings.get("nexwatch_enabled", True):
            logger.info("Nex Watch deshabilitado por configuración (nexwatch_enabled=false)")
            return
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run, name="nex-watch", daemon=True
            )
            self._thread.start()
        logger.info("Nex Watch arrancado")

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
        logger.info("Nex Watch detenido")

    def status(self) -> dict:
        with self._lock:
            running = self._thread is not None and self._thread.is_alive()
            return {
                "running": running,
                "workspace": get_workspace_path(),
                "interval": get_settings().get("nexwatch_interval", 30),
                "alerts": len(self._alerts),
                "commands": len(self._commands),
            }

    def _run(self) -> None:
        """Bucle del vigilante: escanea el workspace hasta que se detenga."""
        while not self._stop_event.is_set():
            try:
                self._scan_once()
            except Exception as e:
                logger.error(f"Error en el escaneo de Nex Watch: {e}")
            interval = get_settings().get("nexwatch_interval", 30)
            self._stop_event.wait(max(5, interval))

    # ── Alertas ─────────────────────────────────────────────────────

    def record_alert(self, kind: str, message: str, details: dict | None = None) -> None:
        alert = {
            "kind": kind,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        with self._lock:
            self._alerts.insert(0, alert)
            if len(self._alerts) > MAX_ALERTS:
                self._alerts = self._alerts[:MAX_ALERTS]
            self._dump()
        logger.info(f"Nex Watch alerta [{kind}]: {message}")

    def get_alerts(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(self._alerts[: max(0, limit)])

    def clear_alerts(self) -> int:
        with self._lock:
            cleared = len(self._alerts)
            self._alerts = []
            self._dump()
        return cleared

    # ── Comandos ────────────────────────────────────────────────────

    def record_command(self, command: str, blocked: bool, reason: str = "") -> None:
        entry = {
            "command": command,
            "blocked": blocked,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        with self._lock:
            self._commands.insert(0, entry)
            if len(self._commands) > MAX_COMMANDS:
                self._commands = self._commands[:MAX_COMMANDS]
            self._dump()
        if blocked:
            self.record_alert(
                "dangerous_command",
                f"Comando peligroso bloqueado: {command[:120]}",
                {"command": command[:200], "reason": reason},
            )

    def get_commands(self, limit: int = 10) -> list[dict]:
        with self._lock:
            return list(self._commands[: max(0, limit)])

    # ── Escaneo del workspace ───────────────────────────────────────

    def _scan_once(self) -> None:
        workspace = get_workspace_path()
        if not workspace or not os.path.isdir(workspace):
            return

        file_count = 0
        sensitive: list[str] = []
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in WORKSPACE_SKIP_DIRS and not d.startswith(".")]
            for name in files:
                file_count += 1
                if self._is_sensitive_name(name):
                    sensitive.append(os.path.join(root, name))

        current_set = set(sensitive)
        self._detect_mass_delete(file_count)
        self._detect_sensitive_deletes(current_set)
        self._report_sensitive_files(current_set)
        self._previous_file_count = file_count
        self._previous_sensitive = current_set

    def _is_sensitive_name(self, name: str) -> bool:
        lower = name.lower()
        if lower in SENSITIVE_NAMES or lower.startswith(".env"):
            return True
        if lower.endswith(SENSITIVE_SUFFIXES):
            return True
        return any(ext in lower for ext in ("secret", "password", "credential", "token"))

    def _detect_mass_delete(self, current_count: int) -> None:
        prev = self._previous_file_count
        if prev is None:
            return
        threshold = get_settings().get("nexwatch_mass_delete_threshold", 10)
        delta = prev - current_count
        if delta >= threshold:
            self.record_alert(
                "mass_delete",
                f"Posible borrado masivo: {delta} archivos eliminados en el workspace",
                {"delta": delta},
            )

    def _detect_sensitive_deletes(self, current: set[str]) -> None:
        if not self._previous_sensitive:
            return
        missed = self._previous_sensitive - current
        for rel in sorted(missed)[:MAX_SECRETS_PER_SCAN]:
            self.record_alert(
                "sensitive_delete",
                f"Archivo sensible eliminado: {os.path.basename(rel)}",
                {"file": rel},
            )

    def _report_sensitive_files(self, current: set[str]) -> None:
        reported = 0
        for path in sorted(current):
            if reported >= MAX_SECRETS_PER_SCAN:
                break
            details = {"file": path}
            if self._is_secret_file(path):
                self.record_alert(
                    "secret_found",
                    f"Posible secreto detectado en {os.path.basename(path)}",
                    details,
                )
                reported += 1
            elif path not in self._previous_sensitive:
                self.record_alert(
                    "sensitive_file",
                    f"Archivo sensible presente: {os.path.basename(path)}",
                    details,
                )
                reported += 1

    def _is_secret_file(self, path: str) -> bool:
        try:
            size = os.path.getsize(path)
            if size > MAX_FILE_SIZE:
                return False
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(MAX_FILE_SIZE)
            return SECRET_KEY_RE.search(content) is not None
        except OSError:
            return False


watch_service = _NexWatchService()
