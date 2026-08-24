"""Resumen semanal proactivo (domingo 21:00, TZ del usuario)."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.agent import llm, prompts
from app.agent.nodes import bloque_contexto
from app.db import consultas
from app.db.models import User
from app.db.session import get_session

logger = logging.getLogger(__name__)


async def armar_resumen_semanal(user_id: int, nombre: str, tz: str) -> str:
    hoy = datetime.now(ZoneInfo(tz)).date()
    async with get_session() as session:
        prom = await consultas.promedios_semana(session, user_id, hoy)
        contexto = await bloque_contexto(session, user_id, hoy)
    encabezado = (
        f"📊 {nombre}, tu semana: ~{prom['kcal_dia'] or 0} kcal/día, "
        f"~{prom['proteinas_dia'] or 0}g prot/día, {prom['sesiones']} sesión(es), "
        f"{prom['pasos_dia'] or 0} pasos/día."
    )
    ahora = datetime.now(ZoneInfo(tz))
    r = await llm.conversar(
        [
            {"role": "system", "content": prompts.system_sugerir(ahora, nombre, contexto)},
            {
                "role": "user",
                "content": "Dame UNA sola sugerencia corta para arrancar la semana que viene.",
            },
        ]
    )
    sugerencia = (r.choices[0].message.content or "").strip()
    return f"{encabezado}\n\n{sugerencia}"


async def enviar_resumen_semanal(bot) -> None:
    """Job del scheduler: resumen + 1 sugerencia a cada usuario activo."""
    async with get_session() as session:
        usuarios = (
            await session.execute(
                select(User.id, User.telegram_id, User.nombre, User.timezone).where(User.activo)
            )
        ).all()
    for u in usuarios:
        try:
            texto = await armar_resumen_semanal(u.id, u.nombre, u.timezone)
            await bot.send_message(chat_id=u.telegram_id, text=texto)
            logger.info("resumen semanal enviado telegram_id=%s", u.telegram_id)
        except Exception:
            logger.exception("resumen semanal falló telegram_id=%s", u.telegram_id)


def crear_scheduler(bot, tz: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        enviar_resumen_semanal,
        CronTrigger(day_of_week="sun", hour=21, timezone=tz),
        args=[bot],
        id="resumen_semanal",
    )
    return scheduler
