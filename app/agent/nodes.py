"""Nodos del grafo. Cada nodo captura sus errores: el grafo nunca explota al handler."""

import functools
import json
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.agent import llm, prompts
from app.agent import tools as tools_mod
from app.config import settings
from app.db import consultas
from app.db import repository as repo
from app.db.models import Perfil
from app.db.session import get_session
from app.schemas import (
    ActividadExtraida,
    ClasificacionImagen,
    ComidaExtraida,
    IntentResult,
    PerfilUpdate,
    PesoExtraido,
)

logger = logging.getLogger(__name__)

RESPUESTA_ERROR = "Uy, algo salió mal procesando tu mensaje. Probá de nuevo en un rato."


def _con_manejo(fn):
    @functools.wraps(fn)
    async def wrapper(state):
        try:
            return await fn(state)
        except Exception:
            logger.exception(
                "nodo %s falló telegram_id=%s intent=%s",
                fn.__name__,
                state.get("telegram_id"),
                state.get("intent"),
            )
            return {"respuesta": RESPUESTA_ERROR}

    return wrapper


def ahora_usuario(state) -> datetime:
    return datetime.now(ZoneInfo(state.get("tz") or "America/Argentina/Buenos_Aires"))


def momento_por_hora(hora: time) -> str:
    if hora < time(11, 0):
        return "desayuno"
    if hora < time(15, 30):
        return "almuerzo"
    if hora < time(19, 0):
        return "merienda"
    return "cena"


@_con_manejo
async def entrada(state):
    """Carga el registro pendiente de aclaración, si hay."""
    async with get_session() as session:
        pendiente = await repo.obtener_pendiente(session, state["user_id"])
        if pendiente is None:
            return {"pendiente": None}
        return {
            "pendiente": {
                "tipo": pendiente.tipo,
                "payload": pendiente.payload,
                "campo": pendiente.campo,
                "pregunta": pendiente.pregunta,
            }
        }


def pregunta_para(extraccion: ComidaExtraida) -> str:
    if extraccion.necesita_aclaracion == "momento":
        hora = extraccion.hora_aprox
        if hora and time(15, 0) <= hora < time(19, 0):
            return "¿Almuerzo o merienda?"
        return "¿A qué comida corresponde: desayuno, almuerzo, merienda, cena o snack?"
    if extraccion.necesita_aclaracion == "fecha":
        return "¿Qué día fue eso?"
    return f"¿Me aclarás {extraccion.necesita_aclaracion}?"


@_con_manejo
async def aclarar(state):
    """Guarda el registro pendiente y hace UNA pregunta corta."""
    extraccion = state["extraccion"]
    pregunta = pregunta_para(extraccion)
    async with get_session() as session:
        await repo.guardar_pendiente(
            session,
            state["user_id"],
            tipo="comida",
            payload=extraccion.model_dump(mode="json"),
            campo=extraccion.necesita_aclaracion,
            pregunta=pregunta,
        )
    return {"respuesta": pregunta}


@_con_manejo
async def completar(state):
    """El mensaje actual responde la pregunta pendiente: fusiona y sigue a guardar."""
    ahora = ahora_usuario(state)
    pendiente = state["pendiente"]
    contexto = (
        f"Hay un registro de comida a medio guardar: {pendiente['payload']}\n"
        f'Se le preguntó al usuario: "{pendiente["pregunta"]}"\n'
        f'El usuario respondió: "{state["input_text"]}"\n'
        "Devolvé el registro COMPLETO combinando ambos, sin necesita_aclaracion."
    )
    comida = await llm.extraer(
        ComidaExtraida,
        [
            {"role": "system", "content": prompts.system_extraccion_comida(ahora)},
            {"role": "user", "content": contexto},
        ],
    )
    comida = comida.model_copy(update={"necesita_aclaracion": None})
    async with get_session() as session:
        await repo.borrar_pendiente(session, state["user_id"])
    return {"extraccion": comida, "intent": "registrar_comida", "pendiente": None}


def _mensaje_con_imagen(system: str, state) -> list[dict]:
    contenido = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{state['image_b64']}"},
        }
    ]
    if state.get("input_text"):
        contenido.append({"type": "text", "text": state["input_text"]})
    return [{"role": "system", "content": system}, {"role": "user", "content": contenido}]


@_con_manejo
async def vision_clasificar(state):
    clasificacion = await llm.extraer(
        ClasificacionImagen,
        _mensaje_con_imagen(prompts.SYSTEM_VISION_CLASIFICAR, state),
        model=settings.vision_model,
    )
    update = {"clasificacion_imagen": clasificacion.categoria}
    if clasificacion.categoria == "otro":
        update["respuesta"] = (
            "Vi la imagen pero no parece un plato, un estudio médico ni una captura de "
            "actividad. Mandame alguna de esas y la registro."
        )
    return update


@_con_manejo
async def examen_extraer(state):
    """Nodo de extracción de exámenes (PDF texto, PDF escaneado o foto)."""
    # ponytail: placeholder hasta 6.2 — acá llega el estudio por las 3 vías
    return {
        "respuesta": (
            "Recibí tu estudio. Todavía estoy aprendiendo a leerlos, pronto va a estar disponible."
        )
    }


@_con_manejo
async def vision_captura(state):
    """Captura de app de actividad → ActividadExtraida (pasos → metricas_dia)."""
    ahora = ahora_usuario(state)
    actividad = await llm.extraer(
        ActividadExtraida,
        _mensaje_con_imagen(prompts.system_vision_captura(ahora), state),
        model=settings.vision_model,
    )
    update = {"extraccion": actividad, "intent": "registrar_actividad"}
    if actividad.fecha is None:
        update["fecha_asumida"] = True
    if actividad.necesita_aclaracion:
        update["pendiente_aclaracion"] = actividad.necesita_aclaracion
    return update


@_con_manejo
async def vision_plato(state):
    """Foto de plato → ComidaExtraida; de acá el flujo sigue igual que texto."""
    ahora = ahora_usuario(state)
    comida = await llm.extraer(
        ComidaExtraida,
        _mensaje_con_imagen(prompts.system_vision_plato(ahora), state),
        model=settings.vision_model,
    )
    update = {"extraccion": comida, "intent": "registrar_comida"}
    if comida.necesita_aclaracion:
        update["pendiente_aclaracion"] = comida.necesita_aclaracion
    return update


@_con_manejo
async def clasificar(state):
    ahora = ahora_usuario(state)
    resultado = await llm.extraer(
        IntentResult,
        [
            {"role": "system", "content": prompts.system_intent(ahora)},
            {"role": "user", "content": state["input_text"]},
        ],
    )
    return {"intent": resultado.intent}


_EXTRACTORES = {
    "registrar_comida": (ComidaExtraida, prompts.system_extraccion_comida),
    "registrar_actividad": (ActividadExtraida, prompts.system_extraccion_actividad),
    "registrar_peso": (PesoExtraido, prompts.system_extraccion_peso),
    "actualizar_perfil": (PerfilUpdate, lambda ahora: prompts.system_perfil()),
}


@_con_manejo
async def extraer(state):
    ahora = ahora_usuario(state)
    intent = state.get("intent")
    if intent not in _EXTRACTORES:
        return {"respuesta": "Todavía no sé manejar ese tipo de mensaje, pronto voy a poder."}
    schema, system = _EXTRACTORES[intent]
    extraccion = await llm.extraer(
        schema,
        [
            {"role": "system", "content": system(ahora)},
            {"role": "user", "content": state["input_text"]},
        ],
    )
    update = {"extraccion": extraccion}
    if getattr(extraccion, "necesita_aclaracion", None):
        update["pendiente_aclaracion"] = extraccion.necesita_aclaracion
    return update


async def bloque_contexto(session, user_id: int, hoy) -> str:
    """Bloque compacto: perfil + tendencia de peso 30d + esta semana vs anterior."""
    perfil = await session.get(Perfil, user_id)
    tendencia = await consultas.tendencia_peso(session, user_id, 30)
    comparacion = await consultas.comparar_semanas(session, user_id, hoy)
    lineas = []
    if perfil:
        lineas.append(
            f"Perfil: objetivo={perfil.objetivo or '-'}, "
            f"restricciones={perfil.restricciones or '-'}, "
            f"peso_actual={perfil.peso_actual_kg or '-'}kg"
        )
    if tendencia["puntos"]:
        lineas.append(
            f"Peso 30 días: {tendencia['puntos'][0][1]}kg → {tendencia['puntos'][-1][1]}kg "
            f"(delta {tendencia['delta_kg']}kg)"
        )
    actual, anterior = comparacion["actual"], comparacion["anterior"]
    lineas.append(
        f"Esta semana: ~{actual['kcal_dia'] or '-'} kcal/día, "
        f"~{actual['proteinas_dia'] or '-'}g prot/día, {actual['sesiones']} sesiones, "
        f"{actual['pasos_dia'] or '-'} pasos/día. "
        f"Semana anterior: ~{anterior['kcal_dia'] or '-'} kcal/día, "
        f"{anterior['sesiones']} sesiones, {anterior['pasos_dia'] or '-'} pasos/día."
    )
    return "\n".join(lineas) or "Sin datos todavía."


MAX_ITERACIONES_TOOLS = 3


@_con_manejo
async def consultar(state):
    """Charla multi-turno con tool-calling sobre los datos del usuario."""
    ahora = ahora_usuario(state)
    user_id = state["user_id"]
    async with get_session() as session:
        historial = await consultas.ultimos_mensajes(session, user_id, 10, horas=24)
        contexto = await bloque_contexto(session, user_id, ahora.date())

    messages = [
        {
            "role": "system",
            "content": prompts.system_consultar(ahora, state.get("nombre", ""), contexto),
        },
        *[{"role": m.rol, "content": m.contenido} for m in historial],
        {"role": "user", "content": state["input_text"]},
    ]

    respuesta_final = None
    for _ in range(MAX_ITERACIONES_TOOLS):
        r = await llm.conversar(messages, tools=tools_mod.DEFINICIONES)
        mensaje = r.choices[0].message
        if not mensaje.tool_calls:
            respuesta_final = mensaje.content
            break
        messages.append(
            {
                "role": "assistant",
                "content": mensaje.content,
                "tool_calls": [tc.model_dump() for tc in mensaje.tool_calls],
            }
        )
        for tc in mensaje.tool_calls:
            resultado = await tools_mod.ejecutar_tool(
                tc.function.name, json.loads(tc.function.arguments or "{}"), user_id
            )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": resultado})
    if respuesta_final is None:
        # se agotaron las iteraciones con tools: pedir cierre sin tools
        r = await llm.conversar(messages)
        respuesta_final = r.choices[0].message.content

    async with get_session() as session:
        await repo.guardar_mensaje_conversacion(
            session, user_id, rol="user", contenido=state["input_text"]
        )
        await repo.guardar_mensaje_conversacion(
            session, user_id, rol="assistant", contenido=respuesta_final
        )
    return {"respuesta": respuesta_final}


@_con_manejo
async def guardar(state):
    ahora = ahora_usuario(state)
    extraccion = state["extraccion"]
    user_id = state["user_id"]
    origen = state.get("origen", "texto")
    raw = state.get("input_text")

    if isinstance(extraccion, ComidaExtraida):
        fecha = extraccion.fecha or ahora.date()
        momento = extraccion.momento or momento_por_hora(ahora.time())
        async with get_session() as session:
            await repo.crear_comida(
                session,
                user_id,
                fecha=fecha,
                momento=momento,
                descripcion=extraccion.descripcion_normalizada,
                origen=origen,
                hora_aprox=extraccion.hora_aprox,
                kcal_est=extraccion.kcal_est,
                proteinas_g=extraccion.proteinas_g,
                carbs_g=extraccion.carbs_g,
                grasas_g=extraccion.grasas_g,
                raw_input=raw,
            )
        return {"extraccion": extraccion.model_copy(update={"fecha": fecha, "momento": momento})}

    if isinstance(extraccion, ActividadExtraida):
        fecha = extraccion.fecha or ahora.date()
        async with get_session() as session:
            if extraccion.tipo == "pasos":
                await repo.upsert_metricas_dia(
                    session, user_id, fecha=fecha, pasos_total=extraccion.pasos, fuente=origen
                )
            else:
                await repo.crear_actividad(
                    session,
                    user_id,
                    fecha=fecha,
                    tipo=extraccion.tipo,
                    origen=origen,
                    hora_aprox=extraccion.hora_aprox,
                    duracion_min=extraccion.duracion_min,
                    intensidad=extraccion.intensidad,
                    pasos=extraccion.pasos,
                    distancia_km=extraccion.distancia_km,
                    kcal_est=extraccion.kcal_est,
                    notas=extraccion.notas,
                    raw_input=raw,
                )
        return {"extraccion": extraccion.model_copy(update={"fecha": fecha})}

    if isinstance(extraccion, PesoExtraido):
        fecha = extraccion.fecha or ahora.date()
        async with get_session() as session:
            await repo.crear_peso(session, user_id, fecha=fecha, peso_kg=extraccion.peso_kg)
            await repo.upsert_perfil(session, user_id, peso_actual_kg=extraccion.peso_kg)
        return {"extraccion": extraccion.model_copy(update={"fecha": fecha})}

    if isinstance(extraccion, PerfilUpdate):
        campos = {k: v for k, v in extraccion.model_dump().items() if v is not None}
        if not campos:
            return {"respuesta": "No encontré datos de perfil para actualizar."}
        async with get_session() as session:
            await repo.upsert_perfil(session, user_id, **campos)
        return {}

    return {"respuesta": RESPUESTA_ERROR}


def _dia_legible(fecha, hoy) -> str:
    if fecha == hoy:
        return "hoy"
    if (hoy - fecha).days == 1:
        return "ayer"
    return f"el {fecha.strftime('%d/%m')}"


@_con_manejo
async def responder(state):
    if state.get("respuesta"):
        return {}
    extraccion = state.get("extraccion")
    nombre = state.get("nombre", "")
    hoy = ahora_usuario(state).date()

    if isinstance(extraccion, ComidaExtraida):
        detalle = f"{extraccion.descripcion_normalizada} — {extraccion.momento} "
        detalle += _dia_legible(extraccion.fecha, hoy)
        if extraccion.kcal_est:
            detalle += f" (~{extraccion.kcal_est} kcal aprox"
            if extraccion.proteinas_g:
                detalle += f", ~{extraccion.proteinas_g}g prot"
            detalle += ")"
        return {"respuesta": f"🍽 Anotado, {nombre}: {detalle}. /deshacer si hubo error."}

    if isinstance(extraccion, ActividadExtraida):
        if extraccion.tipo == "pasos":
            detalle = f"{extraccion.pasos or '?'} pasos {_dia_legible(extraccion.fecha, hoy)}"
        else:
            detalle = extraccion.tipo
            if extraccion.duracion_min:
                detalle += f" {extraccion.duracion_min}'"
            if extraccion.intensidad:
                detalle += f" ({extraccion.intensidad})"
            detalle += f" {_dia_legible(extraccion.fecha, hoy)}"
        respuesta = f"🏃 Anotado, {nombre}: {detalle}."
        if state.get("fecha_asumida"):
            respuesta += " Si era de otro día, avisame."
        return {"respuesta": respuesta + " /deshacer si hubo error."}

    if isinstance(extraccion, PesoExtraido):
        detalle = f"{extraccion.peso_kg} kg {_dia_legible(extraccion.fecha, hoy)}"
        return {"respuesta": f"⚖️ Anotado, {nombre}: {detalle}. /deshacer si hubo error."}

    if isinstance(extraccion, PerfilUpdate):
        campos = [k for k, v in extraccion.model_dump().items() if v is not None]
        return {"respuesta": f"📝 Perfil actualizado, {nombre}: {', '.join(campos)}."}

    return {"respuesta": "Listo."}
