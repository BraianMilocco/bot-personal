"""DoD 3.2: carga en diferido y ciclo de aclaración con registro pendiente."""

from datetime import date

from sqlalchemy import select

from app.agent.graph import procesar_mensaje
from app.db.models import Comida, RegistroPendiente
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


async def test_diferido_desayuno_cargado_de_noche(cliente_mock, user_id, session):
    hoy = date.today().isoformat()
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "registrar_comida"}'),
        respuesta_llm(
            '{"descripcion_normalizada": "tostadas con palta", "kcal_est": 300,'
            f' "confianza": "alta", "fecha": "{hoy}", "momento": "desayuno"}}'
        ),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "a la mañana comí tostadas con palta"))
    assert "Anotado" in respuesta
    fila = await session.scalar(select(Comida).where(Comida.user_id == user_id))
    assert fila.fecha == date.today()
    assert fila.momento == "desayuno"


async def test_ambiguo_pregunta_y_completa(cliente_mock, user_id):
    hoy = date.today().isoformat()
    # 1er mensaje: comida a las 16 sin momento → pregunta corta y pendiente en db
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "registrar_comida"}'),
        respuesta_llm(
            '{"descripcion_normalizada": "sanguche de miga", "kcal_est": 350,'
            f' "confianza": "media", "fecha": "{hoy}", "hora_aprox": "16:00:00",'
            ' "necesita_aclaracion": "momento"}'
        ),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "comí un sanguche a las 16"))
    assert respuesta == "¿Almuerzo o merienda?"

    from app.db.session import get_session

    async with get_session() as s:
        pendiente = await s.get(RegistroPendiente, user_id)
        assert pendiente is not None
        assert pendiente.campo == "momento"
        assert pendiente.payload["descripcion_normalizada"] == "sanguche de miga"

    # 2do mensaje: responde la pregunta → completa, guarda y borra el pendiente
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm(
            '{"descripcion_normalizada": "sanguche de miga", "kcal_est": 350,'
            f' "confianza": "media", "fecha": "{hoy}", "hora_aprox": "16:00:00",'
            ' "momento": "merienda"}'
        ),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "fue merienda"))
    assert "Anotado" in respuesta

    async with get_session() as s:
        fila = await s.scalar(select(Comida).where(Comida.user_id == user_id))
        assert fila.momento == "merienda"
        assert fila.descripcion == "sanguche de miga"
        assert await s.get(RegistroPendiente, user_id) is None
