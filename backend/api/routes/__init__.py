"""Re-export del app de FastAPI.

Mantiene el entry point `uvicorn api.routes:app` (usado por README, scripts y
limit-nex.sh) mientras la implementación vive en `api.routes.application`.
"""
from api.routes.application import app

__all__ = ["app"]