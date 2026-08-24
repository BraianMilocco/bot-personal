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


async def test_caption_viaja_junto_a_la_imagen(cliente_mock, user_id):
    cliente_mock.chat.completions.create.return_value = respuesta_llm('{"categoria": "otro"}')
    await nodes.vision_clasificar(_estado(user_id, caption="es mi almuerzo"))
    contenido = cliente_mock.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert {"type": "text", "text": "es mi almuerzo"} in contenido
