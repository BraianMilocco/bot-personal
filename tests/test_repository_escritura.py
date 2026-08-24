from datetime import date, time
from decimal import Decimal

from sqlalchemy import select

from app.db import repository as repo
from app.db.models import Comida, ExamenValor, MetricasDia
from app.db.session import get_session


async def test_crear_comida(session, user_id):
    comida = await repo.crear_comida(
        session,
        user_id,
        fecha=date(2026, 8, 24),
        momento="almuerzo",
        descripcion="milanesas con puré",
        origen="texto",
        hora_aprox=time(13, 0),
        kcal_est=650,
        proteinas_g=35,
    )
    assert comida.id is not None
    fila = await session.get(Comida, comida.id)
    assert fila.descripcion == "milanesas con puré"
    assert fila.kcal_est == 650


async def test_crear_actividad_y_peso(session, user_id):
    actividad = await repo.crear_actividad(
        session,
        user_id,
        fecha=date(2026, 8, 24),
        tipo="futbol",
        origen="texto",
        duracion_min=60,
        intensidad="alta",
    )
    assert actividad.id is not None
    peso = await repo.crear_peso(
        session, user_id, fecha=date(2026, 8, 24), peso_kg=Decimal("82.50")
    )
    assert peso.peso_kg == Decimal("82.50")


async def test_upsert_metricas_dia_pisa_y_completa(session, user_id):
    hoy = date(2026, 8, 24)
    await repo.upsert_metricas_dia(session, user_id, fecha=hoy, pasos_total=5000, fuente="fit")
    # segunda captura del día pisa pasos
    await repo.upsert_metricas_dia(session, user_id, fecha=hoy, pasos_total=8400)
    fila = await session.scalar(select(MetricasDia).where(MetricasDia.user_id == user_id))
    assert fila.pasos_total == 8400
    assert fila.fuente == "fit"  # None no pisó el valor previo


async def test_upsert_perfil(session, user_id):
    await repo.upsert_perfil(session, user_id, objetivo="bajar 5kg", altura_cm=178)
    perfil = await repo.upsert_perfil(session, user_id, peso_actual_kg=Decimal("82.5"))
    assert perfil.objetivo == "bajar 5kg"  # no se pisó
    assert perfil.peso_actual_kg == Decimal("82.5")


async def test_borrar_ultimo_registro(user_id):
    # transacciones separadas como en el uso real (una por mensaje):
    # now() de Postgres es por transacción y empataría creado_en
    async with get_session() as s:
        await repo.crear_comida(
            s, user_id, fecha=date(2026, 8, 24), momento="cena", descripcion="pizza", origen="texto"
        )
    async with get_session() as s:
        await repo.crear_actividad(
            s, user_id, fecha=date(2026, 8, 24), tipo="caminata", origen="texto"
        )
    async with get_session() as s:
        assert await repo.borrar_ultimo_registro(s, user_id) == ("actividad", "caminata")
    async with get_session() as s:
        assert await repo.borrar_ultimo_registro(s, user_id) == ("comida", "pizza")
    async with get_session() as s:
        assert await repo.borrar_ultimo_registro(s, user_id) is None


async def test_guardar_examen_con_valores(session, user_id):
    examen = await repo.guardar_examen(
        session,
        user_id,
        fecha_estudio=date(2026, 8, 1),
        tipo="sangre",
        valores=[
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
        ],
    )
    valores = (
        await session.scalars(select(ExamenValor).where(ExamenValor.examen_id == examen.id))
    ).all()
    assert len(valores) == 2


async def test_guardar_mensaje_conversacion(session, user_id):
    await repo.guardar_mensaje_conversacion(session, user_id, rol="user", contenido="hola")
    await repo.guardar_mensaje_conversacion(session, user_id, rol="assistant", contenido="¡hola!")
