import logging
import time

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import settings
from app.db.models import User
from app.db.session import get_session

logger = logging.getLogger(__name__)

_AYUDA = (
    "¡Hola{nombre}! Soy tu asesor personal. Contame qué comiste, qué actividad "
    "hiciste, tu peso, o mandame fotos de platos, capturas de tu app de pasos, "
    "audios o PDFs de estudios. Después podés preguntarme por tus datos.\n"
    "Comandos: /start"
)

# ponytail: cache simple con TTL, invalidación fina si algún día hace falta
_whitelist_cache: dict[int, str] = {}
_whitelist_ts: float = 0.0
_WHITELIST_TTL = 60.0


async def usuario_autorizado(telegram_id: int) -> str | None:
    """Devuelve el nombre si el id está activo en la db, None si no."""
    global _whitelist_ts, _whitelist_cache
    if time.monotonic() - _whitelist_ts > _WHITELIST_TTL:
        async with get_session() as session:
            filas = await session.execute(select(User.telegram_id, User.nombre).where(User.activo))
            _whitelist_cache = dict(filas.all())
        _whitelist_ts = time.monotonic()
    return _whitelist_cache.get(telegram_id)


async def seed_users() -> None:
    """Upsert de ALLOWED_USERS en la tabla users al arranque."""
    usuarios = settings.usuarios_permitidos
    if not usuarios:
        return
    async with get_session() as session:
        for u in usuarios:
            stmt = insert(User).values(
                telegram_id=u.telegram_id,
                nombre=u.nombre,
                telefono=u.telefono,
                activo=True,
                timezone=settings.tz,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={"nombre": u.nombre, "telefono": u.telefono},
            )
            await session.execute(stmt)
    logger.info("seed_users: %d usuarios upserteados", len(usuarios))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    telegram_id = update.effective_user.id
    nombre = await usuario_autorizado(telegram_id)
    if nombre is None:
        await update.message.reply_text("No autorizado.")
        logger.warning("mensaje rechazado telegram_id=%s tipo=comando", telegram_id)
        return
    await update.message.reply_text(_AYUDA.format(nombre=f" {nombre}" if nombre else ""))
    latencia_ms = int((time.monotonic() - inicio) * 1000)
    logger.info(
        "mensaje telegram_id=%s tipo=comando latencia_ms=%d",
        telegram_id,
        latencia_ms,
    )


def build_application() -> Application:
    application = Application.builder().token(settings.telegram_token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    return application
