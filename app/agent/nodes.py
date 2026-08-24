"""Nodos del grafo. Cada nodo captura sus errores: el grafo nunca explota al handler."""

import functools
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.agent import llm, prompts
from app.db import repository as repo
from app.db.session import get_session
from app.schemas import ComidaExtraida, IntentResult

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


@_con_manejo
async def extraer(state):
    ahora = ahora_usuario(state)
    intent = state.get("intent")
    if intent == "registrar_comida":
        comida = await llm.extraer(
            ComidaExtraida,
            [
                {"role": "system", "content": prompts.system_extraccion_comida(ahora)},
                {"role": "user", "content": state["input_text"]},
            ],
        )
        update = {"extraccion": comida}
        if comida.necesita_aclaracion:
            update["pendiente_aclaracion"] = comida.necesita_aclaracion
        return update
    return {"respuesta": "Todavía no sé manejar ese tipo de mensaje, pronto voy a poder."}


@_con_manejo
async def guardar(state):
    ahora = ahora_usuario(state)
    extraccion = state["extraccion"]
    if isinstance(extraccion, ComidaExtraida):
        fecha = extraccion.fecha or ahora.date()
        momento = extraccion.momento or momento_por_hora(ahora.time())
        async with get_session() as session:
            await repo.crear_comida(
                session,
                state["user_id"],
                fecha=fecha,
                momento=momento,
                descripcion=extraccion.descripcion_normalizada,
                origen=state.get("origen", "texto"),
                hora_aprox=extraccion.hora_aprox,
                kcal_est=extraccion.kcal_est,
                proteinas_g=extraccion.proteinas_g,
                carbs_g=extraccion.carbs_g,
                grasas_g=extraccion.grasas_g,
                raw_input=state.get("input_text"),
            )
        return {"extraccion": extraccion.model_copy(update={"fecha": fecha, "momento": momento})}
    return {"respuesta": RESPUESTA_ERROR}


@_con_manejo
async def responder(state):
    if state.get("respuesta"):
        return {}
    if state.get("pendiente_aclaracion"):
        return {"respuesta": f"Una consulta: ¿me aclarás {state['pendiente_aclaracion']}?"}
    extraccion = state.get("extraccion")
    nombre = state.get("nombre", "")
    if isinstance(extraccion, ComidaExtraida):
        detalle = f"{extraccion.descripcion_normalizada} — {extraccion.momento}"
        if extraccion.kcal_est:
            detalle += f" (~{extraccion.kcal_est} kcal aprox"
            if extraccion.proteinas_g:
                detalle += f", ~{extraccion.proteinas_g}g prot"
            detalle += ")"
        return {"respuesta": f"🍽 Anotado, {nombre}: {detalle}. /deshacer si hubo error."}
    return {"respuesta": "Listo."}
