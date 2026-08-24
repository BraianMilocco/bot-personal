"""Funciones de escritura. Puras, async, reciben session; sin lógica LLM."""

from datetime import date, time
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Actividad,
    Comida,
    ConversacionMensaje,
    Examen,
    ExamenValor,
    MetricasDia,
    Perfil,
    Peso,
    User,
)


async def obtener_usuario(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def crear_comida(
    session: AsyncSession,
    user_id: int,
    *,
    fecha: date,
    momento: str,
    descripcion: str,
    origen: str,
    hora_aprox: time | None = None,
    kcal_est: int | None = None,
    proteinas_g: int | None = None,
    carbs_g: int | None = None,
    grasas_g: int | None = None,
    raw_input: str | None = None,
) -> Comida:
    comida = Comida(
        user_id=user_id,
        fecha=fecha,
        momento=momento,
        descripcion=descripcion,
        origen=origen,
        hora_aprox=hora_aprox,
        kcal_est=kcal_est,
        proteinas_g=proteinas_g,
        carbs_g=carbs_g,
        grasas_g=grasas_g,
        raw_input=raw_input,
    )
    session.add(comida)
    await session.flush()
    return comida


async def crear_actividad(
    session: AsyncSession,
    user_id: int,
    *,
    fecha: date,
    tipo: str,
    origen: str,
    hora_aprox: time | None = None,
    duracion_min: int | None = None,
    intensidad: str | None = None,
    pasos: int | None = None,
    distancia_km: Decimal | None = None,
    kcal_est: int | None = None,
    notas: str | None = None,
    raw_input: str | None = None,
) -> Actividad:
    actividad = Actividad(
        user_id=user_id,
        fecha=fecha,
        tipo=tipo,
        origen=origen,
        hora_aprox=hora_aprox,
        duracion_min=duracion_min,
        intensidad=intensidad,
        pasos=pasos,
        distancia_km=distancia_km,
        kcal_est=kcal_est,
        notas=notas,
        raw_input=raw_input,
    )
    session.add(actividad)
    await session.flush()
    return actividad


async def crear_peso(session: AsyncSession, user_id: int, *, fecha: date, peso_kg: Decimal) -> Peso:
    peso = Peso(user_id=user_id, fecha=fecha, peso_kg=peso_kg)
    session.add(peso)
    await session.flush()
    return peso


async def upsert_metricas_dia(
    session: AsyncSession,
    user_id: int,
    *,
    fecha: date,
    pasos_total: int | None = None,
    fuente: str | None = None,
) -> None:
    """La captura del día pisa/completa: valores nuevos no-None pisan, None conserva."""
    stmt = insert(MetricasDia).values(
        user_id=user_id, fecha=fecha, pasos_total=pasos_total, fuente=fuente
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_metricas_dia_user_fecha",
        set_={
            "pasos_total": func.coalesce(stmt.excluded.pasos_total, MetricasDia.pasos_total),
            "fuente": func.coalesce(stmt.excluded.fuente, MetricasDia.fuente),
        },
    )
    await session.execute(stmt)


async def upsert_perfil(session: AsyncSession, user_id: int, **campos) -> Perfil:
    """Crea o actualiza el perfil; solo pisa los campos recibidos."""
    perfil = await session.get(Perfil, user_id)
    if perfil is None:
        perfil = Perfil(user_id=user_id)
        session.add(perfil)
    for campo, valor in campos.items():
        setattr(perfil, campo, valor)
    await session.flush()
    return perfil


async def borrar_ultimo_registro(session: AsyncSession, user_id: int) -> tuple[str, str] | None:
    """Borra el registro más reciente (por creado_en) entre comida/actividad/peso.

    Devuelve (tipo, descripción) de lo borrado, o None si no hay registros.
    """
    candidatos = []
    comida = await session.scalar(
        select(Comida).where(Comida.user_id == user_id).order_by(Comida.creado_en.desc()).limit(1)
    )
    if comida:
        candidatos.append((comida.creado_en, "comida", comida.descripcion, Comida, comida.id))
    actividad = await session.scalar(
        select(Actividad)
        .where(Actividad.user_id == user_id)
        .order_by(Actividad.creado_en.desc())
        .limit(1)
    )
    if actividad:
        candidatos.append(
            (actividad.creado_en, "actividad", actividad.tipo, Actividad, actividad.id)
        )
    peso = await session.scalar(
        select(Peso).where(Peso.user_id == user_id).order_by(Peso.creado_en.desc()).limit(1)
    )
    if peso:
        candidatos.append((peso.creado_en, "peso", f"{peso.peso_kg} kg", Peso, peso.id))

    if not candidatos:
        return None
    _, tipo, descripcion, modelo, fila_id = max(candidatos, key=lambda c: c[0])
    await session.execute(delete(modelo).where(modelo.id == fila_id))
    return tipo, descripcion


async def guardar_examen(
    session: AsyncSession,
    user_id: int,
    *,
    fecha_estudio: date,
    tipo: str,
    archivo_path: str | None = None,
    resumen: str | None = None,
    valores: list[dict] | None = None,
) -> Examen:
    examen = Examen(
        user_id=user_id,
        fecha_estudio=fecha_estudio,
        tipo=tipo,
        archivo_path=archivo_path,
        resumen=resumen,
    )
    session.add(examen)
    await session.flush()
    for v in valores or []:
        session.add(ExamenValor(examen_id=examen.id, **v))
    await session.flush()
    return examen


async def guardar_mensaje_conversacion(
    session: AsyncSession, user_id: int, *, rol: str, contenido: str
) -> None:
    session.add(ConversacionMensaje(user_id=user_id, rol=rol, contenido=contenido))
    await session.flush()
