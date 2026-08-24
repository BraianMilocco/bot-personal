"""Extracción con respuestas fixture (lo que devolvería el LLM ante cada prompt)."""

from datetime import datetime

from app.agent import llm, prompts
from app.schemas import ActividadExtraida, ComidaExtraida
from tests.conftest import respuesta_llm

AHORA_NOCHE = datetime(2026, 8, 24, 23, 0)  # lunes 23:00


def _mensajes(system: str, texto: str) -> list[dict]:
    return [{"role": "system", "content": system}, {"role": "user", "content": texto}]


def test_prompts_inyectan_fecha_actual():
    system = prompts.system_extraccion_comida(AHORA_NOCHE)
    assert "2026-08-24" in system
    assert "23:00" in system
    assert "lunes" in system
    assert "milanga" in system  # few-shot rioplatense presente


async def test_comida_simple(cliente_mock):
    cliente_mock.chat.completions.create.return_value = respuesta_llm(
        '{"descripcion_normalizada": "milanesa con papas fritas", "kcal_est": 850,'
        ' "proteinas_g": 40, "carbs_g": 70, "grasas_g": 45, "confianza": "media",'
        ' "fecha": "2026-08-24", "momento": "cena", "hora_aprox": "21:00:00"}'
    )
    comida = await llm.extraer(
        ComidaExtraida,
        _mensajes(prompts.system_extraccion_comida(AHORA_NOCHE), "me morfé una milanga con papas"),
    )
    assert comida.momento == "cena"
    assert comida.kcal_est == 850
    assert comida.necesita_aclaracion is None


async def test_comida_en_diferido(cliente_mock):
    # cargada 23hs: "a la mañana comí tostadas con palta" → desayuno de HOY
    cliente_mock.chat.completions.create.return_value = respuesta_llm(
        '{"descripcion_normalizada": "tostadas con palta", "kcal_est": 300,'
        ' "confianza": "alta", "fecha": "2026-08-24", "momento": "desayuno"}'
    )
    comida = await llm.extraer(
        ComidaExtraida,
        _mensajes(
            prompts.system_extraccion_comida(AHORA_NOCHE), "a la mañana comí tostadas con palta"
        ),
    )
    assert comida.fecha.isoformat() == "2026-08-24"
    assert comida.momento == "desayuno"


async def test_actividad_con_pasos(cliente_mock):
    cliente_mock.chat.completions.create.return_value = respuesta_llm(
        '{"tipo": "pasos", "pasos": 9000, "fecha": "2026-08-24"}'
    )
    actividad = await llm.extraer(
        ActividadExtraida,
        _mensajes(prompts.system_extraccion_actividad(AHORA_NOCHE), "hice 9k pasos"),
    )
    assert actividad.tipo == "pasos"
    assert actividad.pasos == 9000


async def test_caso_ambiguo_marca_aclaracion(cliente_mock):
    cliente_mock.chat.completions.create.return_value = respuesta_llm(
        '{"descripcion_normalizada": "sanguche de miga", "kcal_est": 350,'
        ' "confianza": "media", "fecha": "2026-08-24", "necesita_aclaracion": "momento"}'
    )
    comida = await llm.extraer(
        ComidaExtraida,
        _mensajes(prompts.system_extraccion_comida(AHORA_NOCHE), "comí un sanguche a las 16"),
    )
    assert comida.necesita_aclaracion == "momento"
    assert comida.momento is None
