"""DoD 6.2: comparación valor vs rango EN CÓDIGO, defensiva; persistencia completa."""

from decimal import Decimal

from sqlalchemy import select

from app.agent.graph import procesar_mensaje
from app.agent.nodes import marcar_fuera_de_rango, parsear_numero
from app.db.models import Examen, ExamenValor
from app.schemas import ValorExamen
from tests.conftest import respuesta_llm


def test_parsear_numero_defensivo():
    assert parsear_numero("95") == Decimal("95")
    assert parsear_numero("1,2") == Decimal("1.2")
    assert parsear_numero("<5") == Decimal("5")
    assert parsear_numero("38 mg/dl") == Decimal("38")
    assert parsear_numero("negativo") is None
    assert parsear_numero(None) is None
    assert parsear_numero("") is None


def test_marcar_fuera_de_rango():
    valores = [
        ValorExamen(nombre="glucemia", valor="95", ref_min="70", ref_max="110"),
        ValorExamen(nombre="hdl", valor="38", ref_min="40", ref_max=None),
        ValorExamen(nombre="leucocitos", valor="<5", ref_min=None, ref_max="10"),
        ValorExamen(nombre="serologia", valor="negativo"),  # sin rango → NULL
        ValorExamen(nombre="vsg", valor="raro##", ref_min="0", ref_max="20"),  # no parsea
    ]
    filas = marcar_fuera_de_rango(valores)
    assert filas[0]["fuera_de_rango"] is False  # 95 dentro de 70-110
    assert filas[1]["fuera_de_rango"] is True  # 38 < 40
    assert filas[2]["fuera_de_rango"] is False  # 5 <= 10
    assert filas[3]["fuera_de_rango"] is None  # sin rango
    assert filas[4]["fuera_de_rango"] is None  # valor no numérico no rompe


async def test_examen_persistido_end_to_end(cliente_mock, user_id, session, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm(
            '{"fecha_estudio": "2026-08-01", "tipo": "sangre", "valores": ['
            '{"nombre": "Glucemia", "valor": "95", "unidad": "mg/dl",'
            ' "ref_min": "70", "ref_max": "110"},'
            '{"nombre": "HDL", "valor": "38", "unidad": "mg/dl", "ref_min": "40"},'
            '{"nombre": "Serologia", "valor": "negativo"}'
            "]}"
        ),
        respuesta_llm("Resumen: hdl figura fuera del rango del estudio."),
    ]
    respuesta = await procesar_mensaje(
        {
            "telegram_id": 424242,
            "user_id": user_id,
            "nombre": "Test",
            "tz": "UTC",
            "pdf_text": "informe de laboratorio ...",
            "archivo_path": "data/examenes/x/abc.pdf",
            "origen": "imagen",
        }
    )
    assert "hdl figura fuera del rango" in respuesta
    assert "médico" in respuesta  # cierre agregado en código

    examen = await session.scalar(select(Examen).where(Examen.user_id == user_id))
    assert examen.tipo == "sangre"
    assert examen.fecha_estudio.isoformat() == "2026-08-01"
    assert examen.archivo_path == "data/examenes/x/abc.pdf"
    valores = (
        await session.scalars(select(ExamenValor).where(ExamenValor.examen_id == examen.id))
    ).all()
    por_nombre = {v.nombre: v for v in valores}
    assert por_nombre["glucemia"].fuera_de_rango is False
    assert por_nombre["hdl"].fuera_de_rango is True
    assert por_nombre["serologia"].fuera_de_rango is None  # estudio sin rango → NULL
    assert por_nombre["serologia"].valor == "negativo"
