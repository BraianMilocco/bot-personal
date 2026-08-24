"""DoD 7.3: job disparado manualmente envía el mensaje correcto."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.bot.proactivo import crear_scheduler, enviar_resumen_semanal
from app.db import consultas
from app.db import repository as repo
from app.db.session import get_session
from tests.conftest import respuesta_llm

HOY = date.today()
LUNES, _ = consultas.semana_de(HOY)


async def test_job_envia_resumen_correcto(cliente_mock, user_id):
    async with get_session() as session:
        await repo.crear_comida(
            session,
            user_id,
            fecha=LUNES,
            momento="almuerzo",
            descripcion="milanesa",
            origen="texto",
            kcal_est=900,
            proteinas_g=45,
        )
        await repo.crear_actividad(session, user_id, fecha=LUNES, tipo="gym", origen="texto")
        await repo.upsert_metricas_dia(session, user_id, fecha=LUNES, pasos_total=6000)
    cliente_mock.chat.completions.create.return_value = respuesta_llm(
        "Una opción es sumar una caminata corta después de cenar."
    )

    bot = MagicMock()
    bot.send_message = AsyncMock()
    await enviar_resumen_semanal(bot)

    llamada = bot.send_message.call_args
    assert llamada.kwargs["chat_id"] == 424242  # telegram_id del usuario de prueba
    texto = llamada.kwargs["text"]
    assert "~900 kcal/día" in texto
    assert "1 sesión(es)" in texto
    assert "6000 pasos/día" in texto
    assert "Una opción es" in texto  # la sugerencia del LLM viaja en el mensaje


async def test_job_no_explota_si_un_usuario_falla(cliente_mock, user_id):
    cliente_mock.chat.completions.create.side_effect = RuntimeError("api caída")
    bot = MagicMock()
    bot.send_message = AsyncMock()
    await enviar_resumen_semanal(bot)  # no lanza
    bot.send_message.assert_not_called()


def test_scheduler_programado_domingo_21():
    scheduler = crear_scheduler(MagicMock(), "America/Argentina/Buenos_Aires")
    job = scheduler.get_job("resumen_semanal")
    trigger = str(job.trigger)
    assert "day_of_week='sun'" in trigger
    assert "hour='21'" in trigger
