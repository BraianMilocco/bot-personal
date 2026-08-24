import pytest
from sqlalchemy import text

from app.db.models import User
from app.db.session import SessionFactory

TABLAS = (
    "conversacion_mensajes, examen_valores, examenes, metricas_dia, "
    "actividades, comidas, pesos, perfiles, users"
)


@pytest.fixture
async def user_id():
    """Db limpia con un usuario de prueba; devuelve su id interno."""
    async with SessionFactory() as session, session.begin():
        await session.execute(text(f"TRUNCATE {TABLAS} RESTART IDENTITY CASCADE"))
        usuario = User(telegram_id=424242, nombre="Test", timezone="America/Argentina/Buenos_Aires")
        session.add(usuario)
        await session.flush()
        uid = usuario.id
    return uid


@pytest.fixture
async def session():
    async with SessionFactory() as s, s.begin():
        yield s
