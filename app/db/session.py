from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session():
    """Sesión por mensaje: abre, commitea al salir, rollback ante excepción."""
    async with SessionFactory() as session, session.begin():
        yield session
