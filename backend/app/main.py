"""Punto de entrada de la API de CheckUrRef."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyses, health, session
from app.core.config import get_settings
from app.workers.analysis_worker import create_worker

logger = logging.getLogger(__name__)

# Al apagar, se espera este tiempo a que termine el análisis en curso; si no
# termina, al volver a iniciar regresa a la cola.
SHUTDOWN_WAIT_SECONDS = 5.0


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Arranca el worker de análisis junto con la API, si hay conexión con Supabase."""
    settings = get_settings()
    stop = asyncio.Event()
    worker_task: asyncio.Task[None] | None = None
    if settings.worker_enabled and settings.supabase_url and settings.supabase_service_role_key:
        # Los mensajes del worker (qué análisis toma, cómo termina) se ven en la terminal.
        logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
        # La consulta a la cola cada pocos segundos no se registra; solo sus errores.
        logging.getLogger("httpx").setLevel(logging.WARNING)
        worker_task = asyncio.create_task(create_worker(settings).run(stop))
        logger.info("Worker de análisis iniciado")
    yield
    stop.set()
    if worker_task:
        with suppress(asyncio.TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(worker_task, timeout=SHUTDOWN_WAIT_SECONDS)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(session.router)
    app.include_router(analyses.router)
    return app


app = create_app()
