"""DoD 6.3: resumen con tono calibrado, sin lenguaje diagnóstico; /examenes y /examen."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.agent.graph import procesar_mensaje
from app.agent.nodes import CIERRE_EXAMEN, FRASES_PROHIBIDAS, resumen_deterministico
from app.bot import handlers
from app.db import repository as repo
from app.db.models import Examen
from app.db.session import get_session
from tests.conftest import respuesta_llm

EXTRACCION = (
    '{"fecha_estudio": "2026-08-01", "tipo": "sangre", "valores": ['
    '{"nombre": "Glucemia", "valor": "95", "unidad": "mg/dl",'
    ' "ref_min": "70", "ref_max": "110"},'
    '{"nombre": "HDL", "valor": "38", "unidad": "mg/dl", "ref_min": "40"}'
    "]}"
)

RESUMEN_BUENO = (
    "📄 Estudio de sangre del 01/08/2026.\n"
    "En rango: glucemia.\n"
    "• hdl: 38 mg/dl figura fuera del rango de referencia del estudio (40-) — "
    "vale la pena consultarlo con tu médico."
)


def _estado(user_id):
    return {
        "telegram_id": 424242,
        "user_id": user_id,
        "nombre": "Test",
        "tz": "UTC",
        "pdf_text": "informe...",
        "archivo_path": "data/x.pdf",
        "origen": "imagen",
    }


async def test_resumen_cumple_formato_y_tono(cliente_mock, user_id, session):
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm(EXTRACCION),
        respuesta_llm(RESUMEN_BUENO),
    ]
    respuesta = await procesar_mensaje(_estado(user_id))
    assert "consultarlo con tu médico" in respuesta
    assert CIERRE_EXAMEN in respuesta  # cierre SIEMPRE (regla 4, agregado en código)
    for frase in FRASES_PROHIBIDAS:
        assert frase not in respuesta.lower()
    # el resumen quedó persistido en la fila
    fila = await session.scalar(select(Examen).where(Examen.user_id == user_id))
    assert fila.resumen is not None
    assert CIERRE_EXAMEN in fila.resumen


async def test_lenguaje_prohibido_activa_fallback(cliente_mock, user_id):
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm(EXTRACCION),
        respuesta_llm("Tenés diabetes, es grave."),  # el LLM se portó mal
    ]
    respuesta = await procesar_mensaje(_estado(user_id))
    for frase in FRASES_PROHIBIDAS:
        assert frase not in respuesta.lower()
    assert "figura fuera del rango de referencia del estudio" in respuesta
    assert CIERRE_EXAMEN in respuesta


async def test_comparacion_con_estudio_anterior(cliente_mock, user_id):
    async with get_session() as s:
        await repo.guardar_examen(
            s,
            user_id,
            fecha_estudio=date(2026, 1, 10),
            tipo="sangre",
            valores=[{"nombre": "glucemia", "valor": "102", "fuera_de_rango": False}],
        )
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm(EXTRACCION),
        respuesta_llm("La glucemia pasó de 102 a 95."),
    ]
    await procesar_mensaje(_estado(user_id))
    # el estudio anterior viajó en el mensaje al LLM de redacción
    llamada = cliente_mock.chat.completions.create.call_args_list[1]
    assert '"102"' in llamada.kwargs["messages"][1]["content"]


def test_resumen_deterministico_formato():
    valores = [
        {
            "nombre": "glucemia",
            "valor": "95",
            "unidad": "mg/dl",
            "ref_min": "70",
            "ref_max": "110",
            "fuera_de_rango": False,
        },
        {
            "nombre": "hdl",
            "valor": "38",
            "unidad": "mg/dl",
            "ref_min": "40",
            "ref_max": None,
            "fuera_de_rango": True,
        },
        {
            "nombre": "serologia",
            "valor": "negativo",
            "unidad": None,
            "ref_min": None,
            "ref_max": None,
            "fuera_de_rango": None,
        },
    ]
    texto = resumen_deterministico("sangre", date(2026, 8, 1), valores)
    assert "En rango: glucemia." in texto
    assert "hdl" in texto and "consultarlo con tu médico" in texto
    assert "Sin rango de referencia en el estudio: serologia." in texto


async def test_comandos_examenes(cliente_mock, user_id, monkeypatch):
    async with get_session() as s:
        await repo.guardar_examen(
            s,
            user_id,
            fecha_estudio=date(2026, 8, 1),
            tipo="sangre",
            resumen="resumen guardado del estudio",
            valores=[
                {
                    "nombre": "hdl",
                    "valor": "38",
                    "unidad": "mg/dl",
                    "ref_min": "40",
                    "fuera_de_rango": True,
                }
            ],
        )
        await repo.guardar_examen(s, user_id, fecha_estudio=date(2026, 1, 10), tipo="orina")
    monkeypatch.setattr(
        handlers,
        "usuario_autorizado",
        AsyncMock(return_value={"user_id": user_id, "nombre": "Test", "tz": "UTC"}),
    )
    update = MagicMock()
    update.effective_user.id = 424242
    update.message.reply_text = AsyncMock()

    await handlers.cmd_examenes(update, MagicMock(args=[]))
    listado = update.message.reply_text.call_args[0][0]
    assert "1. sangre — 01/08/2026" in listado
    assert "2. orina — 10/01/2026" in listado

    await handlers.cmd_examen(update, MagicMock(args=["1"]))
    detalle = update.message.reply_text.call_args[0][0]
    assert "resumen guardado del estudio" in detalle
    assert "hdl: 38 mg/dl (ref 40-) ⚠️" in detalle
    cliente_mock.chat.completions.create.assert_not_called()
