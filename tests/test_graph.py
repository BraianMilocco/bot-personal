"""Integración del grafo: texto entra → fila en db → respuesta con datos correctos."""

from sqlalchemy import select

from app.agent.graph import procesar_mensaje
from app.db.models import Comida
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


async def test_texto_comida_end_to_end(cliente_mock, user_id, session):
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "registrar_comida"}'),
        respuesta_llm(
            '{"descripcion_normalizada": "milanesa con puré", "kcal_est": 650,'
            ' "proteinas_g": 35, "confianza": "alta", "momento": "almuerzo"}'
        ),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "me comí una milanesa con puré"))

    assert "Anotado" in respuesta
    assert "milanesa con puré" in respuesta
    assert "650" in respuesta
    fila = await session.scalar(select(Comida).where(Comida.user_id == user_id))
    assert fila is not None
    assert fila.descripcion == "milanesa con puré"
    assert fila.momento == "almuerzo"
    assert fila.kcal_est == 650
    assert fila.raw_input == "me comí una milanesa con puré"


async def test_llm_roto_no_explota(cliente_mock, user_id):
    cliente_mock.chat.completions.create.side_effect = RuntimeError("api caída")
    respuesta = await procesar_mensaje(_estado(user_id, "hola"))
    assert "salió mal" in respuesta
