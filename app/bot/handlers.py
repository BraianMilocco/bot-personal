import base64
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pymupdf as fitz
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.agent import llm
from app.agent.graph import procesar_mensaje
from app.archivos import guardar_archivo_examen
from app.config import settings
from app.db import consultas
from app.db import repository as repo
from app.db.models import Perfil, User
from app.db.session import get_session

logger = logging.getLogger(__name__)

_AYUDA = (
    "¡Hola{nombre}! Soy tu asesor personal. Contame qué comiste, qué actividad "
    "hiciste, tu peso, o mandame fotos de platos, capturas de tu app de pasos, "
    "audios o PDFs de estudios. Después podés preguntarme por tus datos.\n"
    "Comandos: /hoy /semana /perfil /deshacer"
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


def _hoy_de(usuario: dict):
    return datetime.now(ZoneInfo(usuario["tz"])).date()


def _formato_dia(resumen: dict) -> str:
    lineas = [f"📅 {resumen['fecha'].strftime('%d/%m')}"]
    comidas = resumen["comidas"]
    if comidas:
        lineas.append(
            f"🍽 {len(comidas)} comida(s) (~{resumen['kcal_total']} kcal, "
            f"~{resumen['proteinas_total']}g prot)"
        )
        lineas.extend(
            f" • {c.momento}: {c.descripcion}" + (f" (~{c.kcal_est} kcal)" if c.kcal_est else "")
            for c in comidas
        )
    else:
        lineas.append("🍽 sin comidas cargadas")
    if resumen["actividades"]:
        for a in resumen["actividades"]:
            detalle = a.tipo + (f" {a.duracion_min}'" if a.duracion_min else "")
            lineas.append(f"🏃 {detalle}")
    if resumen["pasos_total"]:
        lineas.append(f"👟 {resumen['pasos_total']} pasos")
    if resumen["peso"]:
        lineas.append(f"⚖️ {resumen['peso']} kg")
    return "\n".join(lineas)


async def cmd_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "comando")
    if usuario is None:
        return
    async with get_session() as session:
        resumen = await consultas.resumen_dia(session, usuario["user_id"], _hoy_de(usuario))
    await update.message.reply_text(_formato_dia(resumen))
    _log_mensaje(update, "comando", inicio)


async def cmd_semana(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "comando")
    if usuario is None:
        return
    hoy = _hoy_de(usuario)
    async with get_session() as session:
        prom = await consultas.promedios_semana(session, usuario["user_id"], hoy)
        resumen = await consultas.resumen_semana(session, usuario["user_id"], hoy)
    lineas = [
        f"📊 Semana del {prom['desde'].strftime('%d/%m')}",
        f"~{prom['kcal_dia'] or 0} kcal/día · ~{prom['proteinas_dia'] or 0}g prot/día · "
        f"{prom['sesiones']} sesión(es) · {prom['pasos_dia'] or 0} pasos/día",
        "",
    ]
    for dia in resumen["dias"]:
        partes = [dia["fecha"].strftime("%a %d/%m")]
        partes.append(f"{dia['kcal_total']} kcal" if dia["comidas"] else "sin comidas")
        if dia["actividades"]:
            partes.append(f"{len(dia['actividades'])} actividad(es)")
        if dia["pasos_total"]:
            partes.append(f"{dia['pasos_total']} pasos")
        lineas.append(" · ".join(partes))
    await update.message.reply_text("\n".join(lineas))
    _log_mensaje(update, "comando", inicio)


async def cmd_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "comando")
    if usuario is None:
        return
    async with get_session() as session:
        perfil = await session.get(Perfil, usuario["user_id"])
    if perfil is None:
        await update.message.reply_text(
            "Todavía no tenés perfil. Contame tu objetivo, altura o restricciones y lo armo."
        )
        return
    lineas = [f"👤 Perfil de {usuario['nombre']}"]
    campos = (
        ("Objetivo", perfil.objetivo),
        ("Restricciones", perfil.restricciones),
        ("Altura", f"{perfil.altura_cm} cm" if perfil.altura_cm else None),
        ("Peso actual", f"{perfil.peso_actual_kg} kg" if perfil.peso_actual_kg else None),
        ("Sexo", perfil.sexo),
        ("Nacimiento", perfil.fecha_nac.isoformat() if perfil.fecha_nac else None),
        ("Notas", perfil.notas),
    )
    lineas.extend(f"• {etiqueta}: {valor}" for etiqueta, valor in campos if valor)
    await update.message.reply_text("\n".join(lineas))
    _log_mensaje(update, "comando", inicio)


async def _procesar_texto(update: Update, usuario: dict, texto: str, origen: str) -> None:
    respuesta = await procesar_mensaje(
        {
            "telegram_id": update.effective_user.id,
            "user_id": usuario["user_id"],
            "nombre": usuario["nombre"],
            "tz": usuario["tz"],
            "input_text": texto,
            "origen": origen,
        }
    )
    await update.message.reply_text(respuesta)


async def mensaje_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "texto")
    if usuario is None:
        return
    await _procesar_texto(update, usuario, update.message.text, "texto")
    _log_mensaje(update, "texto", inicio)


MAX_AUDIO_SEGUNDOS = 120
MAX_AUDIO_BYTES = 10 * 1024 * 1024


async def mensaje_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "audio")
    if usuario is None:
        return
    audio = update.message.voice or update.message.audio
    if audio.duration and audio.duration > MAX_AUDIO_SEGUNDOS:
        await update.message.reply_text("El audio es muy largo: mandame notas de hasta 2 minutos.")
        return
    if audio.file_size and audio.file_size > MAX_AUDIO_BYTES:
        await update.message.reply_text("El audio es muy pesado, probá con uno más corto.")
        return
    archivo = await audio.get_file()
    audio_bytes = bytes(await archivo.download_as_bytearray())
    texto = await llm.transcribir(audio_bytes)
    await _procesar_texto(update, usuario, texto, "audio")
    _log_mensaje(update, "audio", inicio)


MAX_FOTO_BYTES = 10 * 1024 * 1024


async def mensaje_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "imagen")
    if usuario is None:
        return
    foto = update.message.photo[-1]  # mejor resolución
    if foto.file_size and foto.file_size > MAX_FOTO_BYTES:
        await update.message.reply_text("La foto es muy pesada (máx 10MB).")
        return
    archivo = await foto.get_file()
    imagen_bytes = bytes(await archivo.download_as_bytearray())
    respuesta = await procesar_mensaje(
        {
            "telegram_id": update.effective_user.id,
            "user_id": usuario["user_id"],
            "nombre": usuario["nombre"],
            "tz": usuario["tz"],
            "input_text": update.message.caption,
            "image_b64": base64.b64encode(imagen_bytes).decode(),
            "origen": "imagen",
        }
    )
    await update.message.reply_text(respuesta)
    _log_mensaje(update, "imagen", inicio)


MAX_PDF_BYTES = 20 * 1024 * 1024
MIN_CHARS_PDF = 30


def extraer_pdf(pdf_bytes: bytes) -> tuple[str | None, str | None]:
    """Devuelve (pdf_text, image_b64): texto si el PDF lo tiene, si no pág 1 rasterizada."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        texto = "\n".join(pagina.get_text() for pagina in doc)
        if len(texto.strip()) >= MIN_CHARS_PDF:
            return texto, None
        pixmap = doc[0].get_pixmap(dpi=200)
        return None, base64.b64encode(pixmap.tobytes("png")).decode()


async def mensaje_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inicio = time.monotonic()
    usuario = await _autorizar(update, "pdf")
    if usuario is None:
        return
    documento = update.message.document
    if documento.file_size and documento.file_size > MAX_PDF_BYTES:
        await update.message.reply_text("El PDF es muy pesado (máx 20MB).")
        return
    archivo = await documento.get_file()
    pdf_bytes = bytes(await archivo.download_as_bytearray())
    ruta = guardar_archivo_examen(usuario["user_id"], pdf_bytes, ".pdf")
    pdf_text, imagen_b64 = extraer_pdf(pdf_bytes)
    respuesta = await procesar_mensaje(
        {
            "telegram_id": update.effective_user.id,
            "user_id": usuario["user_id"],
            "nombre": usuario["nombre"],
            "tz": usuario["tz"],
            "input_text": update.message.caption,
            "pdf_text": pdf_text,
            "image_b64": imagen_b64,
            "es_estudio": imagen_b64 is not None,
            "archivo_path": ruta,
            "origen": "imagen",
        }
    )
    await update.message.reply_text(respuesta)
    _log_mensaje(update, "pdf", inicio)


async def mensaje_no_soportado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    usuario = await _autorizar(update, "no_soportado")
    if usuario is None:
        return
    await update.message.reply_text(
        "Ese formato no lo manejo. Acepto: texto, notas de voz/audio, fotos y PDFs."
    )


def build_application() -> Application:
    application = Application.builder().token(settings.telegram_token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("deshacer", cmd_deshacer))
    application.add_handler(CommandHandler("hoy", cmd_hoy))
    application.add_handler(CommandHandler("semana", cmd_semana))
    application.add_handler(CommandHandler("perfil", cmd_perfil))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_texto))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, mensaje_audio))
    application.add_handler(MessageHandler(filters.PHOTO, mensaje_foto))
    application.add_handler(MessageHandler(filters.Document.PDF, mensaje_pdf))
    application.add_handler(
        MessageHandler(
            ~filters.TEXT
            & ~filters.VOICE
            & ~filters.AUDIO
            & ~filters.PHOTO
            & ~filters.Document.PDF
            & ~filters.COMMAND,
            mensaje_no_soportado,
        )
    )
    return application
