from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text

from app.agent import llm
from app.db.models import User
from app.db.session import SessionFactory


def respuesta_llm(contenido: str) -> MagicMock:
    """Arma una respuesta de chat.completions con el contenido dado (sin tool calls)."""
    r = MagicMock()
    r.choices = [MagicMock()]
    r.choices[0].message.content = contenido
    r.choices[0].message.tool_calls = None
    return r


def respuesta_tool_call(nombre: str, argumentos: str = "{}", call_id: str = "call_1") -> MagicMock:
    """Arma una respuesta de chat.completions que pide ejecutar una tool."""
    r = MagicMock()
    r.choices = [MagicMock()]
    r.choices[0].message.content = None
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = nombre
    tc.function.arguments = argumentos
    tc.model_dump.return_value = {
        "id": call_id,
        "type": "function",
        "function": {"name": nombre, "arguments": argumentos},
    }
    r.choices[0].message.tool_calls = [tc]
    return r


@pytest.fixture
def cliente_mock(monkeypatch):
    cliente = MagicMock()
    cliente.chat.completions.create = AsyncMock()
    cliente.audio.transcriptions.create = AsyncMock()
    monkeypatch.setattr(llm, "_client", cliente)
    return cliente


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
