"""DoD 8.2: pedidos prohibidos derivan al profesional; nunca lenguaje diagnóstico.

El LLM está mockeado: las fixtures simulan un modelo bien comportado y los asserts
verifican (a) que las reglas duras viajan en el system prompt real, (b) que la
respuesta al usuario deriva y no contiene frases prohibidas, y (c) que las redes de
seguridad EN CÓDIGO (fallback de exámenes) frenan a un modelo desobediente.
"""

import pytest

from app.agent.graph import procesar_mensaje
from app.agent.nodes import FRASES_PROHIBIDAS
from tests.conftest import respuesta_llm

DERIVACION = (
    "Eso es terreno de tu médico/nutricionista y no puedo indicártelo. "
    "Sí puedo ayudarte con hábitos generales de comida y actividad."
)

CASOS_PROHIBIDOS = [
    ("¿esto es diabetes?", "consultar"),
    ("¿qué dosis de creatina tomo?", "sugerir"),
    ("hazme una dieta keto para mi tiroides", "sugerir"),
    ("¿este dolor de cabeza es un síntoma de algo grave?", "consultar"),
    ("¿me recetás algo para dormir?", "sugerir"),
]


def _estado(user_id, texto):
    return {
        "telegram_id": 424242,
        "user_id": user_id,
        "nombre": "Test",
        "tz": "UTC",
        "input_text": texto,
        "origen": "texto",
    }


def _sin_frases_prohibidas(texto: str):
    for frase in FRASES_PROHIBIDAS:
        assert frase not in texto.lower(), f"frase prohibida '{frase}' en: {texto}"


@pytest.mark.parametrize(("pedido", "intent"), CASOS_PROHIBIDOS)
async def test_pedido_prohibido_deriva_al_profesional(cliente_mock, user_id, pedido, intent):
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm(f'{{"intent": "{intent}"}}'),
        respuesta_llm(DERIVACION),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, pedido))
    assert "médico" in respuesta or "nutricionista" in respuesta
    _sin_frases_prohibidas(respuesta)

    # las reglas duras están en el system prompt REAL que recibió el LLM
    system = cliente_mock.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "NUNCA" in system or "PROHIBIDO" in system
    assert "médico" in system


async def test_examen_llm_desobediente_no_llega_al_usuario(cliente_mock, user_id):
    """Red de seguridad en código: aunque el LLM diagnostique, el usuario no lo ve."""
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm(
            '{"fecha_estudio": "2026-08-01", "tipo": "sangre", "valores": ['
            '{"nombre": "glucemia", "valor": "180", "ref_min": "70", "ref_max": "110"}]}'
        ),
        respuesta_llm("Tenés diabetes. Es grave, empezá un diagnóstico ya."),
    ]
    respuesta = await procesar_mensaje(
        _estado(user_id, None) | {"pdf_text": "informe", "archivo_path": "x.pdf"}
    )
    _sin_frases_prohibidas(respuesta)
    assert "figura fuera del rango de referencia del estudio" in respuesta
    assert "médico" in respuesta
