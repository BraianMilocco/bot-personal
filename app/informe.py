"""Informe para llevar al médico/nutricionista. Determinístico, sin LLM."""

from collections import Counter
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import consultas
from app.db.models import Perfil


async def generar_informe(
    session: AsyncSession, user_id: int, nombre: str, hoy: date, destinatario: str = "medico"
) -> str:
    quien = "nutricionista" if destinatario.startswith("nutri") else "médico"
    lineas = [
        f"INFORME PARA TU {quien.upper()} — {nombre}",
        f"Generado el {hoy.strftime('%d/%m/%Y')} con datos autorreportados por Telegram.",
        "Las calorías y macros son estimaciones automáticas, no mediciones.",
        "",
        "— PERFIL —",
    ]
    perfil = await session.get(Perfil, user_id)
    if perfil:
        if perfil.objetivo:
            lineas.append(f"Objetivo: {perfil.objetivo}")
        if perfil.restricciones:
            lineas.append(f"Restricciones: {perfil.restricciones}")
        if perfil.altura_cm:
            lineas.append(f"Altura: {perfil.altura_cm} cm")
        if perfil.peso_actual_kg:
            lineas.append(f"Peso actual: {perfil.peso_actual_kg} kg")
        if perfil.fecha_nac:
            lineas.append(f"Nacimiento: {perfil.fecha_nac.strftime('%d/%m/%Y')}")
    else:
        lineas.append("Sin perfil cargado.")

    lineas.append("")
    lineas.append("— PESO (últimos 30 días) —")
    tendencia = await consultas.tendencia_peso(session, user_id, 30)
    if tendencia["puntos"]:
        for fecha, peso in tendencia["puntos"]:
            lineas.append(f"{fecha.strftime('%d/%m')}: {peso} kg")
        if tendencia["delta_kg"] is not None:
            lineas.append(f"Variación en el período: {tendencia['delta_kg']:+} kg")
    else:
        lineas.append("Sin registros de peso.")

    lineas.append("")
    lineas.append("— ALIMENTACIÓN (promedios por semana, últimas 4) —")
    for i in range(4):
        prom = await consultas.promedios_semana(session, user_id, hoy - timedelta(days=7 * i))
        if prom["kcal_dia"] is None and prom["sesiones"] == 0 and prom["pasos_dia"] is None:
            continue
        lineas.append(
            f"Semana del {prom['desde'].strftime('%d/%m')}: "
            f"~{prom['kcal_dia'] or 0} kcal/día, ~{prom['proteinas_dia'] or 0}g prot/día, "
            f"{prom['sesiones']} sesión(es), {prom['pasos_dia'] or 0} pasos/día"
        )

    lineas.append("")
    lineas.append("— ACTIVIDAD (últimos 28 días) —")
    actividades = await consultas.historial_actividad(session, user_id, 28)
    if actividades:
        conteo = Counter(a.tipo for a in actividades)
        minutos = sum(a.duracion_min or 0 for a in actividades)
        lineas.append(
            f"{len(actividades)} sesiones ({minutos} min totales): "
            + ", ".join(f"{tipo} x{n}" for tipo, n in conteo.most_common())
        )
    else:
        lineas.append("Sin actividades registradas.")

    lineas.append("")
    lineas.append("— ÚLTIMOS EXÁMENES —")
    examenes = (await consultas.listar_examenes(session, user_id))[:3]
    if examenes:
        for examen in examenes:
            lineas.append(f"{examen.tipo} — {examen.fecha_estudio.strftime('%d/%m/%Y')}:")
            for v in await consultas.valores_examen(session, examen.id):
                rango = (
                    f" (ref {v.ref_min or ''}-{v.ref_max or ''})" if v.ref_min or v.ref_max else ""
                )
                marca = " [FUERA DE RANGO DEL ESTUDIO]" if v.fuera_de_rango else ""
                lineas.append(f"  {v.nombre}: {v.valor} {v.unidad or ''}{rango}{marca}")
    else:
        lineas.append("Sin exámenes cargados.")

    return "\n".join(lineas)
