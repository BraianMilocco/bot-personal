"""DoD 3.3: los 4 tipos por texto end-to-end + /deshacer."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.agent.graph import procesar_mensaje
from app.bot import handlers
from app.db.models import Actividad, MetricasDia, Perfil, Peso
from tests.conftest import respuesta_llm


def _estado(user_id: int, texto: str) -> dict:
    return {
        "telegram_id": 424242,
        "user_id": user_id,
        "nombre": "Test",
        "tz": "America/Argentina/Buenos_Aires",
        "input_text": texto,
        "origen": "texto",
    }


async def test_actividad_sesion(cliente_mock, user_id, session):
    hoy = date.today().isoformat()
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "registrar_actividad"}'),
        respuesta_llm(
            f'{{"tipo": "gym", "duracion_min": 45, "intensidad": "alta", "fecha": "{hoy}"}}'
        ),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "gym 45 minutos fuerte"))
    assert "🏃 Anotado" in respuesta
    assert "gym 45'" in respuesta
    fila = await session.scalar(select(Actividad).where(Actividad.user_id == user_id))
    assert fila.tipo == "gym"
    assert fila.duracion_min == 45
    assert fila.intensidad == "alta"


async def test_actividad_pasos_va_a_metricas(cliente_mock, user_id, session):
    hoy = date.today().isoformat()
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "registrar_actividad"}'),
        respuesta_llm(f'{{"tipo": "pasos", "pasos": 9000, "fecha": "{hoy}"}}'),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "hice 9k pasos"))
    assert "9000 pasos" in respuesta
    fila = await session.scalar(select(MetricasDia).where(MetricasDia.user_id == user_id))
    assert fila.pasos_total == 9000
    assert fila.fecha == date.today()
    # no se creó una fila de actividad
    assert await session.scalar(select(Actividad).where(Actividad.user_id == user_id)) is None


async def test_peso(cliente_mock, user_id, session):
    hoy = date.today().isoformat()
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "registrar_peso"}'),
        respuesta_llm(f'{{"peso_kg": "82.5", "fecha": "{hoy}"}}'),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "hoy pesé 82 y medio"))
    assert "⚖️ Anotado" in respuesta
    assert "82.5" in respuesta
    fila = await session.scalar(select(Peso).where(Peso.user_id == user_id))
    assert fila.peso_kg == Decimal("82.50")
    perfil = await session.get(Perfil, user_id)
    assert perfil.peso_actual_kg == Decimal("82.50")


async def test_perfil(cliente_mock, user_id, session):
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "actualizar_perfil"}'),
        respuesta_llm('{"objetivo": "bajar 5kg", "altura_cm": 178}'),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "mido 1.78 y quiero bajar 5kg"))
    assert "📝 Perfil actualizado" in respuesta
    perfil = await session.get(Perfil, user_id)
    assert perfil.objetivo == "bajar 5kg"
    assert perfil.altura_cm == 178


async def test_deshacer(cliente_mock, user_id, monkeypatch):
    hoy = date.today().isoformat()
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "registrar_comida"}'),
        respuesta_llm(
            f'{{"descripcion_normalizada": "pizza", "kcal_est": 700, "fecha": "{hoy}",'
            ' "momento": "cena", "confianza": "alta"}'
        ),
    ]
    await procesar_mensaje(_estado(user_id, "me comí una pizza"))

    update = MagicMock()
    update.effective_user.id = 424242
    update.message.reply_text = AsyncMock()
    monkeypatch.setattr(
        handlers,
        "usuario_autorizado",
        AsyncMock(return_value={"user_id": user_id, "nombre": "Test", "tz": "UTC"}),
    )
    await handlers.cmd_deshacer(update, None)
    texto = update.message.reply_text.call_args[0][0]
    assert "Borré el último registro" in texto
    assert "pizza" in texto

    await handlers.cmd_deshacer(update, None)
    assert update.message.reply_text.call_args[0][0] == "No hay registros para deshacer."
