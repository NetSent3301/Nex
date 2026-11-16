"""Fábrica de la aplicación FastAPI de Nex.

Monta los routers por dominio (chat, settings, system, watch), configura CORS
y auto-arranca Nex Watch en el lifespan.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chat import router as chat_router
from api.routes.settings import router as settings_router
from api.routes.system import router as system_router
from api.routes.watch import router as watch_router

logger = logging.getLogger("nex.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.watch import watch_service

    watch_service.start()
    logger.info("Nex Watch activo (vigilante del workspace)")
    yield
    watch_service.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Nex", version="0.1.0-dev", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8765",
            "http://localhost:5173",
            "http://localhost:8765",
            "file://",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.include_router(system_router)
    app.include_router(settings_router)
    app.include_router(chat_router)
    app.include_router(watch_router)
    return app


app = create_app()