"""Funciones de consulta. Puras, async, reciben session; devuelven datos crudos."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Actividad,
    Comida,
    ConversacionMensaje,
    Examen,
    ExamenValor,
    MetricasDia,
    Peso,
)


def semana_de(fecha: date) -> tuple[date, date]:
    """Semana calendario (lunes a domingo) que contiene la fecha."""
    lunes = fecha - timedelta(days=fecha.weekday())
    return lunes, lunes + timedelta(days=6)


async def resumen_dia(session: AsyncSession, user_id: int, fecha: date) -> dict:
    comidas = (
        await session.scalars(
            select(Comida)
            .where(Comida.user_id == user_id, Comida.fecha == fecha)
            .order_by(Comida.hora_aprox.nulls_last(), Comida.id)
        )
    ).all()
    actividades = (
        await session.scalars(
            select(Actividad)
            .where(Actividad.user_id == user_id, Actividad.fecha == fecha)
            .order_by(Actividad.id)
        )
    ).all()
    pasos_total = await session.scalar(
        select(MetricasDia.pasos_total).where(
            MetricasDia.user_id == user_id, MetricasDia.fecha == fecha
        )
    )
    peso = await session.scalar(
        select(Peso.peso_kg)
        .where(Peso.user_id == user_id, Peso.fecha == fecha)
        .order_by(Peso.id.desc())
        .limit(1)
    )
    return {
        "fecha": fecha,
        "comidas": comidas,
        "actividades": actividades,
        "pasos_total": pasos_total,
        "peso": peso,
        "kcal_total": sum(c.kcal_est or 0 for c in comidas),
        "proteinas_total": sum(c.proteinas_g or 0 for c in comidas),
    }


async def resumen_semana(session: AsyncSession, user_id: int, fecha_ref: date) -> dict:
    """Un dict por día de la semana calendario de fecha_ref, con totales."""
    lunes, domingo = semana_de(fecha_ref)
    dias = []
    for i in range(7):
        dia = lunes + timedelta(days=i)
        if dia > fecha_ref:
            break
        dias.append(await resumen_dia(session, user_id, dia))
    return {"desde": lunes, "hasta": domingo, "dias": dias}


async def promedios_semana(session: AsyncSession, user_id: int, fecha_ref: date) -> dict:
    """Promedios de la semana calendario de fecha_ref.

    kcal/proteína por día se dividen por días CON comidas registradas.
    """
    lunes, domingo = semana_de(fecha_ref)
    total_kcal, total_prot, dias_con_comidas = (
        await session.execute(
            select(
                func.coalesce(func.sum(Comida.kcal_est), 0),
                func.coalesce(func.sum(Comida.proteinas_g), 0),
                func.count(func.distinct(Comida.fecha)),
            ).where(Comida.user_id == user_id, Comida.fecha.between(lunes, domingo))
        )
    ).one()
    sesiones = await session.scalar(
        select(func.count())
        .select_from(Actividad)
        .where(Actividad.user_id == user_id, Actividad.fecha.between(lunes, domingo))
    )
    pasos_prom = await session.scalar(
        select(func.avg(MetricasDia.pasos_total)).where(
            MetricasDia.user_id == user_id,
            MetricasDia.fecha.between(lunes, domingo),
            MetricasDia.pasos_total.is_not(None),
        )
    )
    return {
        "desde": lunes,
        "hasta": domingo,
        "kcal_dia": round(total_kcal / dias_con_comidas) if dias_con_comidas else None,
        "proteinas_dia": round(total_prot / dias_con_comidas) if dias_con_comidas else None,
        "sesiones": sesiones,
        "pasos_dia": round(pasos_prom) if pasos_prom is not None else None,
    }


async def comparar_semanas(session: AsyncSession, user_id: int, fecha_ref: date) -> dict:
    actual = await promedios_semana(session, user_id, fecha_ref)
    anterior = await promedios_semana(session, user_id, fecha_ref - timedelta(days=7))
    return {"actual": actual, "anterior": anterior}


async def tendencia_peso(session: AsyncSession, user_id: int, dias: int) -> dict:
    desde = date.today() - timedelta(days=dias)
    filas = (
        await session.execute(
            select(Peso.fecha, Peso.peso_kg)
            .where(Peso.user_id == user_id, Peso.fecha >= desde)
            .order_by(Peso.fecha, Peso.id)
        )
    ).all()
    puntos = [(f.fecha, f.peso_kg) for f in filas]
    delta = puntos[-1][1] - puntos[0][1] if len(puntos) >= 2 else None
    return {"puntos": puntos, "delta_kg": delta}


async def historial_actividad(session: AsyncSession, user_id: int, dias: int) -> list[Actividad]:
    desde = date.today() - timedelta(days=dias)
    return list(
        await session.scalars(
            select(Actividad)
            .where(Actividad.user_id == user_id, Actividad.fecha >= desde)
            .order_by(Actividad.fecha, Actividad.id)
        )
    )


async def ultimo_examen(
    session: AsyncSession, user_id: int, tipo: str | None = None
) -> Examen | None:
    stmt = select(Examen).where(Examen.user_id == user_id)
    if tipo:
        stmt = stmt.where(Examen.tipo == tipo)
    return await session.scalar(stmt.order_by(Examen.fecha_estudio.desc(), Examen.id.desc()))


async def valores_examen(session: AsyncSession, examen_id: int) -> list[ExamenValor]:
    return list(
        await session.scalars(
            select(ExamenValor).where(ExamenValor.examen_id == examen_id).order_by(ExamenValor.id)
        )
    )


async def ultimos_mensajes(
    session: AsyncSession, user_id: int, n: int = 10
) -> list[ConversacionMensaje]:
    filas = (
        await session.scalars(
            select(ConversacionMensaje)
            .where(ConversacionMensaje.user_id == user_id)
            .order_by(ConversacionMensaje.creado_en.desc(), ConversacionMensaje.id.desc())
            .limit(n)
        )
    ).all()
    return list(reversed(filas))
