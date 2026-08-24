"""DoD 7.2: /informe genera el documento completo y ordenado con datos de test."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.bot import handlers
from app.db import consultas
from app.db import repository as repo
from app.db.session import get_session

HOY = date.today()
LUNES, _ = consultas.semana_de(HOY)


async def _seed(user_id):
    async with get_session() as session:
        await repo.upsert_perfil(
            session,
            user_id,
            objetivo="bajar 5kg",
            altura_cm=178,
            peso_actual_kg=Decimal("83.20"),
            restricciones="sin lactosa",
        )
        await repo.crear_peso(
            session, user_id, fecha=HOY - timedelta(days=10), peso_kg=Decimal("84.00")
        )
        await repo.crear_peso(session, user_id, fecha=HOY, peso_kg=Decimal("83.20"))
        await repo.crear_comida(
            session,
            user_id,
            fecha=LUNES,
            momento="almuerzo",
            descripcion="milanesa",
            origen="texto",
            kcal_est=800,
            proteinas_g=40,
        )
        await repo.crear_comida(
            session,
            user_id,
            fecha=LUNES - timedelta(days=7),
            momento="cena",
            descripcion="pizza",
            origen="texto",
            kcal_est=1200,
            proteinas_g=50,
        )
        await repo.crear_actividad(
            session, user_id, fecha=LUNES, tipo="gym", origen="texto", duracion_min=45
        )
        await repo.crear_actividad(
            session,
            user_id,
            fecha=LUNES - timedelta(days=6),
            tipo="futbol",
            origen="texto",
            duracion_min=60,
        )
        await repo.upsert_metricas_dia(session, user_id, fecha=LUNES, pasos_total=8000)
        await repo.guardar_examen(
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
                    "fuera_de_rango": True,
                },
            ],
        )


async def test_informe_completo(cliente_mock, user_id, monkeypatch):
    await _seed(user_id)
    monkeypatch.setattr(
        handlers,
        "usuario_autorizado",
        AsyncMock(
            return_value={
                "user_id": user_id,
                "nombre": "Test",
                "tz": "America/Argentina/Buenos_Aires",
            }
        ),
    )
    update = MagicMock()
    update.effective_user.id = 424242
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()

    await handlers.cmd_informe(update, MagicMock(args=["nutricionista"]))
    texto = update.message.reply_text.call_args[0][0]

    assert "INFORME PARA TU NUTRICIONISTA — Test" in texto
    assert "Objetivo: bajar 5kg" in texto
    assert "Restricciones: sin lactosa" in texto
    assert "84.00 kg" in texto and "83.20 kg" in texto
    assert "Variación en el período: -0.80 kg" in texto
    assert "~800 kcal/día" in texto  # semana actual
    assert "~1200 kcal/día" in texto  # semana anterior
    assert "gym x1" in texto and "futbol x1" in texto
    assert "105 min totales" in texto
    assert "sangre — 01/08/2026" in texto
    assert "hdl: 38 mg/dl (ref 40-) [FUERA DE RANGO DEL ESTUDIO]" in texto
    assert "estimaciones" in texto  # aclaración de regla 3
    cliente_mock.chat.completions.create.assert_not_called()  # sin LLM
