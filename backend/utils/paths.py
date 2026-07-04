import os
from pathlib import Path


def resolve_workspace(path: str | None = None) -> str:
    if path:
        return os.path.abspath(path)
    return str(Path.cwd())
