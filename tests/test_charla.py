"""DoD 5.2: charla multi-turno con tools, historial y repregunta coherente."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.agent.graph import procesar_mensaje
from app.db import consultas
from app.db import repository as repo
from app.db.models import ConversacionMensaje
from app.db.session import get_session
from tests.conftest import respuesta_llm, respuesta_tool_call

HOY = date.today()
LUNES, _ = consultas.semana_de(HOY)


def _estado(user_id: int, texto: str) -> dict:
    return {
        "telegram_id": 424242,
        "user_id": user_id,
        "nombre": "Test",
        "tz": "America/Argentina/Buenos_Aires",
        "input_text": texto,
        "origen": "texto",
    }


async def _seed(user_id):
    async with get_session() as session:
        await repo.crear_comida(
            session,
            user_id,
            fecha=LUNES,
            momento="almuerzo",
            descripcion="milanesa",
            origen="texto",
            kcal_est=600,
            proteinas_g=35,
        )
        await repo.crear_peso(session, user_id, fecha=HOY, peso_kg=Decimal("83.20"))


async def test_charla_tres_turnos_con_repregunta(cliente_mock, user_id):
    await _seed(user_id)

    # turno 1: pregunta → tool promedios_semana → respuesta con números
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "consultar"}'),
        respuesta_tool_call("promedios_semana", "{}"),
        respuesta_llm("Esta semana promediás ~600 kcal/día con 1 comida cargada."),
    ]
    r1 = await procesar_mensaje(_estado(user_id, "¿cómo vengo esta semana?"))
    assert "600" in r1
    # el resultado real de la tool viajó al LLM
    mensajes_enviados = cliente_mock.chat.completions.create.call_args_list[2].kwargs["messages"]
    mensaje_tool = [m for m in mensajes_enviados if m.get("role") == "tool"][0]
    assert '"kcal_dia": 600' in mensaje_tool["content"]

    # turno 2: repregunta → el historial del turno 1 viaja en los messages
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "consultar"}'),
        respuesta_tool_call("comparar_semanas", "{}"),
        respuesta_llm("La semana pasada no tenés comidas cargadas, así que no hay comparación."),
    ]
    r2 = await procesar_mensaje(_estado(user_id, "¿y la semana pasada?"))
    assert "semana pasada" in r2
    # call_args_list acumula entre turnos: 0-2 turno 1; 3 intent turno 2; 4 conversar turno 2
    mensajes_enviados = cliente_mock.chat.completions.create.call_args_list[4].kwargs["messages"]
    contenidos = [m.get("content") for m in mensajes_enviados]
    assert "¿cómo vengo esta semana?" in contenidos  # historial del turno 1
    assert "Esta semana promediás ~600 kcal/día con 1 comida cargada." in contenidos

    # turno 3: sin tools, respuesta directa con historial
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "consultar"}'),
        respuesta_llm("¡De nada! Seguí cargando tus comidas."),
    ]
    r3 = await procesar_mensaje(_estado(user_id, "gracias"))
    assert "De nada" in r3

    # cada turno quedó guardado (3 user + 3 assistant)
    async with get_session() as s:
        filas = (
            await s.scalars(
                select(ConversacionMensaje).where(ConversacionMensaje.user_id == user_id)
            )
        ).all()
    assert len(filas) == 6
    assert {f.rol for f in filas} == {"user", "assistant"}


async def test_contexto_del_usuario_en_system(cliente_mock, user_id):
    await _seed(user_id)
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "consultar"}'),
        respuesta_llm("ok"),
    ]
    await procesar_mensaje(_estado(user_id, "¿cómo viene mi peso?"))
    system = cliente_mock.chat.completions.create.call_args_list[1].kwargs["messages"][0]
    assert system["role"] == "system"
    assert "83.20" in system["content"]  # peso del bloque de contexto
