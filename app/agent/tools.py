"""Tools de consulta para tool-calling. `quien` es implícito: siempre el user del mensaje."""

import json
from datetime import date
from decimal import Decimal

from app.db import consultas
from app.db.session import get_session


def _json(valor):
    """Serializa fechas/Decimal/filas ORM a algo que el LLM pueda leer."""
    if isinstance(valor, dict):
        return {k: _json(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [_json(v) for v in valor]
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if hasattr(valor, "__table__"):  # fila ORM
        return {c.name: _json(getattr(valor, c.name)) for c in valor.__table__.columns}
    if hasattr(valor, "isoformat"):  # datetime / time
        return valor.isoformat()
    return valor


DEFINICIONES = [
    {
        "type": "function",
        "function": {
            "name": "resumen_dia",
            "description": "Comidas, actividades, pasos y peso de un día dado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "YYYY-MM-DD; default hoy"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_semana",
            "description": "Resumen día por día de la semana calendario de una fecha.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "YYYY-MM-DD; default hoy"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "promedios_semana",
            "description": "Promedios de la semana: kcal/día, proteína/día, sesiones, pasos/día.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "YYYY-MM-DD; default hoy"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "comparar_semanas",
            "description": "Promedios de esta semana vs la anterior.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tendencia_peso",
            "description": "Puntos de peso de los últimos N días y delta total.",
            "parameters": {
                "type": "object",
                "properties": {"dias": {"type": "integer", "description": "default 30"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "historial_actividad",
            "description": "Actividades registradas en los últimos N días.",
            "parameters": {
                "type": "object",
                "properties": {"dias": {"type": "integer", "description": "default 14"}},
            },
        },
    },
]


async def ejecutar_tool(nombre: str, argumentos: dict, user_id: int) -> str:
    """Ejecuta una tool contra el repository y devuelve JSON (para el mensaje de tool)."""
    fecha = date.fromisoformat(argumentos["fecha"]) if argumentos.get("fecha") else date.today()
    async with get_session() as session:
        match nombre:
            case "resumen_dia":
                resultado = await consultas.resumen_dia(session, user_id, fecha)
            case "resumen_semana":
                resultado = await consultas.resumen_semana(session, user_id, fecha)
            case "promedios_semana":
                resultado = await consultas.promedios_semana(session, user_id, fecha)
            case "comparar_semanas":
                resultado = await consultas.comparar_semanas(session, user_id, date.today())
            case "tendencia_peso":
                resultado = await consultas.tendencia_peso(
                    session, user_id, int(argumentos.get("dias") or 30)
                )
            case "historial_actividad":
                resultado = await consultas.historial_actividad(
                    session, user_id, int(argumentos.get("dias") or 14)
                )
            case _:
                return json.dumps({"error": f"tool desconocida: {nombre}"})
    return json.dumps(_json(resultado), ensure_ascii=False)
