"""DoD 5.3: /hoy, /semana y /perfil sin LLM, repository directo, formato fijo."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.bot import handlers
from app.db import repository as repo
from app.db.session import get_session

HOY = date.today()


def _update() -> MagicMock:
    update = MagicMock()
    update.effective_user.id = 424242
    update.message.reply_text = AsyncMock()
    return update


def _autorizado(monkeypatch, user_id):
    monkeypatch.setattr(
        handlers,
        "usuario_autorizado",
        AsyncMock(
            return_value={
                "user_id": user_id,
                "nombre": "Test",
                "tz": "America/Argentina/Buenos_Aires",
            }
        ),
    )


async def _seed(user_id):
    async with get_session() as session:
        await repo.crear_comida(
            session,
            user_id,
            fecha=HOY,
            momento="almuerzo",
            descripcion="milanesa",
            origen="texto",
            kcal_est=600,
            proteinas_g=35,
        )
        await repo.crear_actividad(
            session, user_id, fecha=HOY, tipo="gym", origen="texto", duracion_min=45
        )
        await repo.upsert_metricas_dia(session, user_id, fecha=HOY, pasos_total=7000)
        await repo.crear_peso(session, user_id, fecha=HOY, peso_kg=Decimal("83.20"))
        await repo.upsert_perfil(
            session,
            user_id,
            objetivo="bajar 5kg",
            altura_cm=178,
            peso_actual_kg=Decimal("83.20"),
        )


async def test_hoy(cliente_mock, user_id, monkeypatch):
    await _seed(user_id)
    _autorizado(monkeypatch, user_id)
    update = _update()
    await handlers.cmd_hoy(update, None)
    texto = update.message.reply_text.call_args[0][0]
    assert "~600 kcal" in texto
    assert "milanesa" in texto
    assert "gym 45'" in texto
    assert "7000 pasos" in texto
    assert "83.20 kg" in texto
    cliente_mock.chat.completions.create.assert_not_called()  # sin LLM


async def test_semana(cliente_mock, user_id, monkeypatch):
    await _seed(user_id)
    _autorizado(monkeypatch, user_id)
    update = _update()
    await handlers.cmd_semana(update, None)
    texto = update.message.reply_text.call_args[0][0]
    assert "📊 Semana del" in texto
    assert "~600 kcal/día" in texto
    assert "1 sesión(es)" in texto
    assert "7000 pasos/día" in texto
    cliente_mock.chat.completions.create.assert_not_called()


async def test_perfil(cliente_mock, user_id, monkeypatch):
    await _seed(user_id)
    _autorizado(monkeypatch, user_id)
    update = _update()
    await handlers.cmd_perfil(update, None)
    texto = update.message.reply_text.call_args[0][0]
    assert "Objetivo: bajar 5kg" in texto
    assert "Altura: 178 cm" in texto
    assert "Peso actual: 83.20 kg" in texto
    cliente_mock.chat.completions.create.assert_not_called()


async def test_perfil_vacio(cliente_mock, user_id, monkeypatch):
    _autorizado(monkeypatch, user_id)
    update = _update()
    await handlers.cmd_perfil(update, None)
    assert "no tenés perfil" in update.message.reply_text.call_args[0][0]
