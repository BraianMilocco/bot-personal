"""Grafo LangGraph del agente."""

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agent import nodes

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    telegram_id: int
    user_id: int
    nombre: str
    tz: str
    input_text: str | None
    image_b64: str | None
    pdf_text: str | None
    origen: str  # 'texto' | 'imagen' | 'audio'
    intent: str | None
    extraccion: object | None
    pendiente_aclaracion: str | None
    pendiente: dict | None
    clasificacion_imagen: str | None
    fecha_asumida: bool | None
    respuesta: str | None


def _despues_de_entrada(state: AgentState) -> str:
    if state.get("respuesta"):
        return "fin"
    if state.get("pendiente"):
        return "completar"
    if state.get("image_b64"):
        return "vision"
    return "clasificar"


def _despues_de_vision(state: AgentState) -> str:
    if state.get("respuesta"):
        return "responder"
    if state.get("clasificacion_imagen") == "plato":
        return "vision_plato"
    if state.get("clasificacion_imagen") == "captura_app":
        return "vision_captura"
    return "responder"


def _despues_de_clasificar(state: AgentState) -> str:
    if state.get("respuesta"):
        return "fin"
    if state.get("intent") == "consultar":
        return "consultar"
    return "extraer"


def _despues_de_extraer(state: AgentState) -> str:
    if state.get("respuesta"):
        return "responder"
    if state.get("pendiente_aclaracion"):
        return "aclarar"
    return "guardar"


def _despues_de_completar(state: AgentState) -> str:
    if state.get("respuesta"):
        return "responder"
    return "guardar"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("entrada", nodes.entrada)
    g.add_node("vision", nodes.vision_clasificar)
    g.add_node("vision_plato", nodes.vision_plato)
    g.add_node("vision_captura", nodes.vision_captura)
    g.add_node("clasificar", nodes.clasificar)
    g.add_node("consultar", nodes.consultar)
    g.add_node("extraer", nodes.extraer)
    g.add_node("aclarar", nodes.aclarar)
    g.add_node("completar", nodes.completar)
    g.add_node("guardar", nodes.guardar)
    g.add_node("responder", nodes.responder)

    g.set_entry_point("entrada")
    g.add_conditional_edges(
        "entrada",
        _despues_de_entrada,
        {"completar": "completar", "clasificar": "clasificar", "vision": "vision", "fin": END},
    )
    g.add_conditional_edges(
        "vision",
        _despues_de_vision,
        {
            "vision_plato": "vision_plato",
            "vision_captura": "vision_captura",
            "responder": "responder",
        },
    )
    for nodo_vision in ("vision_plato", "vision_captura"):
        g.add_conditional_edges(
            nodo_vision,
            _despues_de_extraer,
            {"guardar": "guardar", "aclarar": "aclarar", "responder": "responder"},
        )
    g.add_conditional_edges(
        "clasificar",
        _despues_de_clasificar,
        {"extraer": "extraer", "consultar": "consultar", "fin": END},
    )
    g.add_edge("consultar", END)
    g.add_conditional_edges(
        "extraer",
        _despues_de_extraer,
        {"guardar": "guardar", "aclarar": "aclarar", "responder": "responder"},
    )
    g.add_conditional_edges(
        "completar", _despues_de_completar, {"guardar": "guardar", "responder": "responder"}
    )
    g.add_edge("aclarar", END)
    g.add_edge("guardar", "responder")
    g.add_edge("responder", END)
    return g.compile()


_graph = None


async def procesar_mensaje(state: AgentState) -> str:
    """Punto de entrada del handler. Nunca lanza: siempre devuelve una respuesta."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    try:
        final = await _graph.ainvoke(state)
        return final.get("respuesta") or "No entendí el mensaje. ¿Me lo repetís de otra forma?"
    except Exception:
        logger.exception("grafo falló telegram_id=%s", state.get("telegram_id"))
        return "Uy, algo salió mal procesando tu mensaje. Probá de nuevo en un rato."
