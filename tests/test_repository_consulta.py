from datetime import date, timedelta
from decimal import Decimal

from app.db import consultas
from app.db import repository as repo

HOY = date.today()
LUNES, DOMINGO = consultas.semana_de(HOY)
LUNES_PREV = LUNES - timedelta(days=7)


async def _seed(session, user_id):
    # semana actual: lunes 500+300 kcal (30+10g prot), martes 700 kcal (40g prot)
    await repo.crear_comida(
        session,
        user_id,
        fecha=LUNES,
        momento="almuerzo",
        descripcion="a",
        origen="texto",
        kcal_est=500,
        proteinas_g=30,
    )
    await repo.crear_comida(
        session,
        user_id,
        fecha=LUNES,
        momento="cena",
        descripcion="b",
        origen="texto",
        kcal_est=300,
        proteinas_g=10,
    )
    await repo.crear_comida(
        session,
        user_id,
        fecha=LUNES + timedelta(days=1),
        momento="almuerzo",
        descripcion="c",
        origen="texto",
        kcal_est=700,
        proteinas_g=40,
    )
    # 2 sesiones esta semana, 1 la anterior
    await repo.crear_actividad(
        session, user_id, fecha=LUNES, tipo="gym", origen="texto", duracion_min=45
    )
    await repo.crear_actividad(
        session, user_id, fecha=LUNES + timedelta(days=1), tipo="caminata", origen="texto"
    )
    await repo.crear_actividad(
        session, user_id, fecha=LUNES_PREV, tipo="futbol", origen="texto", duracion_min=60
    )
    # pasos: 8000 y 10000 esta semana; 5000 la anterior
    await repo.upsert_metricas_dia(session, user_id, fecha=LUNES, pasos_total=8000)
    await repo.upsert_metricas_dia(
        session, user_id, fecha=LUNES + timedelta(days=1), pasos_total=10000
    )
    await repo.upsert_metricas_dia(session, user_id, fecha=LUNES_PREV, pasos_total=5000)
    # semana anterior: 2000 kcal en un solo día
    await repo.crear_comida(
        session,
        user_id,
        fecha=LUNES_PREV,
        momento="almuerzo",
        descripcion="asado",
        origen="texto",
        kcal_est=2000,
        proteinas_g=90,
    )
    # pesos para tendencia
    await repo.crear_peso(
        session, user_id, fecha=HOY - timedelta(days=10), peso_kg=Decimal("84.00")
    )
    await repo.crear_peso(session, user_id, fecha=HOY, peso_kg=Decimal("83.50"))


async def test_resumen_dia(session, user_id):
    await _seed(session, user_id)
    resumen = await consultas.resumen_dia(session, user_id, LUNES)
    assert resumen["kcal_total"] == 800  # 500 + 300
    assert resumen["proteinas_total"] == 40  # 30 + 10
    assert len(resumen["comidas"]) == 2
    assert len(resumen["actividades"]) == 1
    assert resumen["pasos_total"] == 8000


async def test_promedios_y_comparar_semanas(session, user_id):
    await _seed(session, user_id)
    prom = await consultas.promedios_semana(session, user_id, HOY)
    assert prom["kcal_dia"] == 750  # 1500 kcal / 2 días con comidas
    assert prom["proteinas_dia"] == 40  # 80 g / 2 días
    assert prom["sesiones"] == 2
    assert prom["pasos_dia"] == 9000  # (8000 + 10000) / 2

    comparacion = await consultas.comparar_semanas(session, user_id, HOY)
    assert comparacion["actual"]["kcal_dia"] == 750
    assert comparacion["anterior"]["kcal_dia"] == 2000
    assert comparacion["anterior"]["sesiones"] == 1
    assert comparacion["anterior"]["pasos_dia"] == 5000


async def test_resumen_semana(session, user_id):
    await _seed(session, user_id)
    resumen = await consultas.resumen_semana(session, user_id, HOY)
    assert resumen["desde"] == LUNES
    assert resumen["dias"][0]["kcal_total"] == 800


async def test_tendencia_peso(session, user_id):
    await _seed(session, user_id)
    tendencia = await consultas.tendencia_peso(session, user_id, 30)
    assert len(tendencia["puntos"]) == 2
    assert tendencia["delta_kg"] == Decimal("-0.50")


async def test_historial_actividad(session, user_id):
    await _seed(session, user_id)
    historial = await consultas.historial_actividad(session, user_id, 30)
    assert len(historial) == 3
    assert historial[0].tipo == "futbol"  # el más viejo primero


async def test_ultimo_examen_y_valores(session, user_id):
    viejo = await repo.guardar_examen(
        session,
        user_id,
        fecha_estudio=date(2026, 1, 10),
        tipo="sangre",
        valores=[{"nombre": "glucemia", "valor": "90"}],
    )
    nuevo = await repo.guardar_examen(
        session,
        user_id,
        fecha_estudio=date(2026, 8, 1),
        tipo="sangre",
        valores=[{"nombre": "glucemia", "valor": "95"}, {"nombre": "hdl", "valor": "42"}],
    )
    ultimo = await consultas.ultimo_examen(session, user_id, "sangre")
    assert ultimo.id == nuevo.id
    valores = await consultas.valores_examen(session, ultimo.id)
    assert [v.nombre for v in valores] == ["glucemia", "hdl"]
    assert await consultas.ultimo_examen(session, user_id, "orina") is None
    assert viejo.id != nuevo.id


async def test_ultimos_mensajes(session, user_id):
    for i in range(12):
        await repo.guardar_mensaje_conversacion(
            session, user_id, rol="user" if i % 2 == 0 else "assistant", contenido=f"msg {i}"
        )
    mensajes = await consultas.ultimos_mensajes(session, user_id, 10)
    assert len(mensajes) == 10
    assert mensajes[0].contenido == "msg 2"  # los 2 más viejos quedaron afuera
    assert mensajes[-1].contenido == "msg 11"
