import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = create_async_engine(settings.database_url)
    yield
    await app.state.engine.dispose()


app = FastAPI(title="asesor-personal", lifespan=lifespan)


@app.get("/health")
async def health():
    db_ok = False
    try:
        async with app.state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("health: fallo el check de db")
    return {"status": "ok", "db": db_ok}
