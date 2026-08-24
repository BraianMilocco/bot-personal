import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.bot.handlers import build_application, seed_users
from app.bot.proactivo import crear_scheduler
from app.config import settings
from app.db.session import engine

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


async def _arrancar_bot(app: FastAPI) -> None:
    application = build_application()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    app.state.bot = application
    app.state.scheduler = crear_scheduler(application.bot, settings.tz)
    app.state.scheduler.start()
    logger.info("bot: polling iniciado y resumen semanal programado")


async def _frenar_bot(app: FastAPI) -> None:
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    application = getattr(app.state, "bot", None)
    if application is None:
        return
    await application.updater.stop()
    await application.stop()
    await application.shutdown()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await seed_users()
    except Exception:
        logger.exception("seed_users falló (¿migraciones pendientes?)")
    try:
        await _arrancar_bot(app)
    except Exception:
        logger.exception("bot no pudo arrancar (¿token inválido?); la API sigue viva")
    yield
    await _frenar_bot(app)
    await engine.dispose()


app = FastAPI(title="asesor-personal", lifespan=lifespan)


@app.get("/health")
async def health():
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("health: fallo el check de db")
    return {"status": "ok", "db": db_ok}
