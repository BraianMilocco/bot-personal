import logging
import time

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.agent.graph import procesar_mensaje
from app.config import settings
from app.db import repository as repo
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
_whitelist_cache: dict[int, dict] = {}
_whitelist_ts: float = 0.0
_WHITELIST_TTL = 60.0


async def usuario_autorizado(telegram_id: int) -> dict | None:
    """Devuelve {user_id, nombre, tz} si el id está activo en la db, None si no."""
    global _whitelist_ts, _whitelist_cache
    if time.monotonic() - _whitelist_ts > _WHITELIST_TTL:
        async with get_session() as session:
            filas = await session.execute(
                select(User.telegram_id, User.id, User.nombre, User.timezone).where(User.activo)
            )
            _whitelist_cache = {
                f.telegram_id: {"user_id": f.id, "nombre": f.nombre, "tz": f.timezone}
                for f in filas.all()
            }
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


async def _autorizar(update: Update, tipo: str) -> dict | None:
    """Whitelist + log de rechazo. Devuelve el usuario o None (ya respondido)."""
    telegram_id = update.effective_user.id
    usuario = await usuario_autorizado(telegram_id)
    if usuario is None:
        await update.message.reply_text("No autorizado.")
        logger.warning("mensaje rechazado telegram_id=%s tipo=%s", telegram_id, tipo)
    return usuario


def _log_mensaje(update: Update, tipo: str, inicio: float) -> None:
    latencia_ms = int((time.monotonic() - inicio) * 1000)
    logger.info(
        "mensaje telegram_id=%s tipo=%s latencia_ms=%d",
        update.effective_user.id,
        tipo,
        latencia_ms,
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "comando")
    if usuario is None:
        return
    nombre = usuario["nombre"]
    await update.message.reply_text(_AYUDA.format(nombre=f" {nombre}" if nombre else ""))
    _log_mensaje(update, "comando", inicio)


async def cmd_deshacer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "comando")
    if usuario is None:
        return
    async with get_session() as session:
        borrado = await repo.borrar_ultimo_registro(session, usuario["user_id"])
    if borrado is None:
        await update.message.reply_text("No hay registros para deshacer.")
    else:
        tipo, descripcion = borrado
        await update.message.reply_text(f"↩️ Borré el último registro: {tipo} ({descripcion}).")
    _log_mensaje(update, "comando", inicio)


async def mensaje_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "texto")
    if usuario is None:
        return
    respuesta = await procesar_mensaje(
        {
            "telegram_id": update.effective_user.id,
            "user_id": usuario["user_id"],
            "nombre": usuario["nombre"],
            "tz": usuario["tz"],
            "input_text": update.message.text,
            "origen": "texto",
        }
    )
    await update.message.reply_text(respuesta)
    _log_mensaje(update, "texto", inicio)


def build_application() -> Application:
    application = Application.builder().token(settings.telegram_token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("deshacer", cmd_deshacer))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_texto))
    return application
