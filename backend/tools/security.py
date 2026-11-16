import os
import re
from typing import Callable

BLOCKED_COMMANDS = {
    "sudo", "su", "chmod", "chown", "passwd", "useradd", "userdel",
    "usermod", "groupadd", "groupdel", "mkfs", "fdisk", "dd",
    "reboot", "shutdown", "halt", "poweroff", "init",
    "iptables", "ufw", "firewall-cmd",
    "systemctl", "service", "rc-service",
    "mount", "umount", "swapoff",
    "kill", "killall", "pkill", "renice",
    "wget", "curl", "nc", "ncat", "telnet", "ssh", "scp",
    "python -m http.server", "python3 -m http.server",
    "nmap", "masscan",
    "crontab", "at", "batch",
    "insmod", "modprobe", "rmmod",
}

DANGEROUS_PATTERNS = [
    r"(^|\s)>(>|)\s*/dev/",
    r"(^|\s)>(>|)\s*/proc/",
    r"(^|\s)>\s*/sys/",
    r"(^|\s)mkfs\b",
    r"(^|\s)dd\b",
    r"(^|\s)fdisk\b",
    r"(^|\s)format\b",
]

_PROMETER: Callable[[str, str], bool] | None = None


def set_dangerous_prompter(fn: Callable[[str, str], bool] | None) -> None:
    """Registra un callback que preguntará al usuario antes de ejecutar
    un comando peligroso. Sin callback, los comandos peligrosos se bloquean."""
    global _PROMETER
    _PROMETER = fn


def confirm_dangerous(command: str, reason: str) -> bool:
    if _PROMETER is None:
        return False
    try:
        return bool(_PROMETER(command, reason))
    except Exception:
        return False


def is_command_allowed(command: str) -> tuple[bool, str]:
    first_word = command.strip().split()[0].lower() if command.strip().split() else ""

    if first_word in BLOCKED_COMMANDS:
        return False, f"Command '{first_word}' is blocked for security reasons."

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return False, "Command matches dangerous pattern and is blocked."

    return True, ""


def allowlist_workspace_scope(command: str, workspace_root: str) -> tuple[bool, str]:
    if workspace_root and os.path.isdir(workspace_root):
        workspace_root = os.path.abspath(workspace_root)

        if not command.startswith("cd ") and not command.startswith("git "):
            for dangerous_cmd in ["> /", "> /root", "> /etc", "> /usr", "rm -rf /", "rm -rf /*"]:
                if dangerous_cmd in command:
                    return False, "Command attempts to modify system paths outside workspace."
        return True, ""

    return True, ""


def check_allowed(command: str, workspace_root: str | None = None) -> str:
    """Devuelve el motivo de bloqueo o '' si el comando es seguro."""
    allowed, reason = is_command_allowed(command)
    if not allowed:
        return reason
    if workspace_root:
        allowed, reason = allowlist_workspace_scope(command, workspace_root)
        if not allowed:
            return reason
    return ""


def confirm_or_deny(command: str, workspace_root: str | None = None) -> tuple[bool, str]:
    """Autoriza según seguridad; si es peligroso, delega en el prompter del usuario.

    Devuelve (True, "") si se puede ejecutar o (False, motivo) si se bloquea.
    """
    reason = check_allowed(command, workspace_root)
    if not reason:
        return True, ""
    if confirm_dangerous(command, reason):
        return True, ""
    return False, f"Security block: {reason}"