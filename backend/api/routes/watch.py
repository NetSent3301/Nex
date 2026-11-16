"""Rutas de Nex Watch: alertas y estado del vigilante del workspace."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/alerts")
async def get_alerts(limit: int = 50) -> dict:
    from services.watch import watch_service

    return {"alerts": watch_service.get_alerts(limit)}


@router.post("/api/v1/alerts/clear")
async def clear_alerts() -> dict:
    from services.watch import watch_service

    cleared = watch_service.clear_alerts()
    return {"cleared": cleared}


@router.get("/api/v1/watch/status")
async def watch_status() -> dict:
    from services.watch import watch_service

    return watch_service.status()