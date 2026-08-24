"""DoD 4.1: clasificación de imagen (visión mockeada) y ruteo."""

import pytest

from app.agent import nodes
from app.agent.graph import procesar_mensaje
from tests.conftest import respuesta_llm

B64 = "aW1hZ2VuLWZha2U="  # bytes fake


def _estado(user_id: int, caption: str | None = None) -> dict:
    return {
        "telegram_id": 424242,
        "user_id": user_id,
        "nombre": "Test",
        "tz": "America/Argentina/Buenos_Aires",
        "input_text": caption,
        "image_b64": B64,
        "origen": "imagen",
    }


@pytest.mark.parametrize("categoria", ["plato", "estudio", "captura_app"])
async def test_clasifica_los_tres_tipos(cliente_mock, user_id, categoria):
    cliente_mock.chat.completions.create.return_value = respuesta_llm(
        f'{{"categoria": "{categoria}"}}'
    )
    update = await nodes.vision_clasificar(_estado(user_id))
    assert update["clasificacion_imagen"] == categoria
    # el call de visión usa el modelo de visión y manda la imagen
    llamada = cliente_mock.chat.completions.create.call_args
    assert llamada.kwargs["model"] == "gpt-4o-mini"
    contenido = llamada.kwargs["messages"][1]["content"]
    assert any(parte.get("type") == "image_url" for parte in contenido)


async def test_imagen_otro_responde_amable(cliente_mock, user_id):
    cliente_mock.chat.completions.create.return_value = respuesta_llm('{"categoria": "otro"}')
    respuesta = await procesar_mensaje(_estado(user_id))
    assert "no parece" in respuesta
    assert "plato" in respuesta


async def test_foto_de_plato_registra_comida(cliente_mock, user_id, session):
    """DoD 4.2: foto de plato → comida con macros y momento por hora local."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from app.agent.nodes import momento_por_hora
    from app.db.models import Comida

    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"categoria": "plato"}'),
        respuesta_llm(
            '{"descripcion_normalizada": "milanesa con ensalada", "kcal_est": 600,'
            ' "proteinas_g": 38, "carbs_g": 40, "grasas_g": 28, "confianza": "media"}'
        ),
    ]
    respuesta = await procesar_mensaje(_estado(user_id))
    assert "🍽 Anotado" in respuesta
    assert "600" in respuesta

    fila = await session.scalar(select(Comida).where(Comida.user_id == user_id))
    assert fila.descripcion == "milanesa con ensalada"
    assert fila.kcal_est == 600
    assert fila.origen == "imagen"
    # sin momento en la extracción → momento por hora local
    hora_local = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).time()
    assert fila.momento == momento_por_hora(hora_local)


async def test_captura_fit_carga_pasos_y_segunda_pisa(cliente_mock, user_id, session):
    """DoD 4.3: captura carga pasos_total del día; una segunda captura del día pisa."""
    from datetime import date

    from sqlalchemy import select

    from app.db.models import MetricasDia

    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"categoria": "captura_app"}'),
        respuesta_llm('{"tipo": "pasos", "pasos": 5000}'),  # sin fecha visible
        respuesta_llm('{"categoria": "captura_app"}'),
        respuesta_llm('{"tipo": "pasos", "pasos": 8400}'),
    ]
    respuesta = await procesar_mensaje(_estado(user_id))
    assert "5000 pasos hoy" in respuesta
    assert "Si era de otro día, avisame" in respuesta  # fecha no visible → asumió hoy

    respuesta = await procesar_mensaje(_estado(user_id))
    assert "8400 pasos" in respuesta

    filas = (await session.scalars(select(MetricasDia).where(MetricasDia.user_id == user_id))).all()
    assert len(filas) == 1  # upsert: una sola fila para el día
    assert filas[0].fecha == date.today()
    assert filas[0].pasos_total == 8400  # la segunda pisó a la primera


async def test_caption_viaja_junto_a_la_imagen(cliente_mock, user_id):
    cliente_mock.chat.completions.create.return_value = respuesta_llm('{"categoria": "otro"}')
    await nodes.vision_clasificar(_estado(user_id, caption="es mi almuerzo"))
    contenido = cliente_mock.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert {"type": "text", "text": "es mi almuerzo"} in contenido
