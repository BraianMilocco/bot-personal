"""DoD 5.1: tools con seed; números exactos en los resultados JSON."""

import json
from datetime import date, timedelta
from decimal import Decimal

from app.agent import tools
from app.db import consultas
from app.db import repository as repo
from app.db.session import get_session

HOY = date.today()
LUNES, _ = consultas.semana_de(HOY)


async def _seed(user_id):
    # sesión propia commiteada: las tools abren su propia sesión y no verían
    # datos sin commitear de la fixture
    async with get_session() as session:
        await _cargar(session, user_id)


async def _cargar(session, user_id):
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
    await repo.crear_comida(
        session,
        user_id,
        fecha=LUNES,
        momento="cena",
        descripcion="sopa",
        origen="texto",
        kcal_est=200,
        proteinas_g=10,
    )
    await repo.crear_actividad(
        session, user_id, fecha=LUNES, tipo="gym", origen="texto", duracion_min=45
    )
    await repo.upsert_metricas_dia(session, user_id, fecha=LUNES, pasos_total=7000)
    await repo.crear_peso(session, user_id, fecha=HOY - timedelta(days=5), peso_kg=Decimal("84.00"))
    await repo.crear_peso(session, user_id, fecha=HOY, peso_kg=Decimal("83.20"))


async def test_resumen_dia_tool(user_id):
    await _seed(user_id)
    resultado = json.loads(
        await tools.ejecutar_tool("resumen_dia", {"fecha": LUNES.isoformat()}, user_id)
    )
    assert resultado["kcal_total"] == 800  # 600 + 200
    assert resultado["proteinas_total"] == 45
    assert resultado["pasos_total"] == 7000
    assert len(resultado["comidas"]) == 2
    assert resultado["comidas"][0]["descripcion"] in ("milanesa", "sopa")


async def test_promedios_y_tendencia_tools(user_id):
    await _seed(user_id)
    prom = json.loads(await tools.ejecutar_tool("promedios_semana", {}, user_id))
    assert prom["kcal_dia"] == 800  # 800 kcal / 1 día con comidas
    assert prom["sesiones"] == 1
    assert prom["pasos_dia"] == 7000

    tendencia = json.loads(await tools.ejecutar_tool("tendencia_peso", {"dias": 30}, user_id))
    assert tendencia["delta_kg"] == "-0.80"
    assert len(tendencia["puntos"]) == 2

    historial = json.loads(await tools.ejecutar_tool("historial_actividad", {}, user_id))
    assert len(historial) == 1
    assert historial[0]["tipo"] == "gym"
    assert historial[0]["duracion_min"] == 45


async def test_tool_desconocida(user_id):
    resultado = json.loads(await tools.ejecutar_tool("dropear_tabla", {}, user_id))
    assert "error" in resultado


def test_definiciones_completas():
    nombres = {d["function"]["name"] for d in tools.DEFINICIONES}
    assert nombres == {
        "resumen_dia",
        "resumen_semana",
        "promedios_semana",
        "comparar_semanas",
        "tendencia_peso",
        "historial_actividad",
    }
