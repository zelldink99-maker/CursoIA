"""Agente de soporte que consulta documentación y estima costos de Gemini."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langchain_core.agents import AgentAction
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool, tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

if __package__:
    from .configuracion import crear_chat_modelo
    from .costo import (
        PRECIO_ENTRADA_POR_TOKEN,
        PRECIO_SALIDA_POR_TOKEN,
        calcular_costo,
    )
    from .trazas_agente import registrar_traza
else:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.GATE_2.configuracion import crear_chat_modelo
    from src.GATE_2.costo import (
        PRECIO_ENTRADA_POR_TOKEN,
        PRECIO_SALIDA_POR_TOKEN,
        calcular_costo,
    )
    from src.GATE_2.trazas_agente import registrar_traza


@tool
def buscar_en_documentacion(consulta: str) -> str:
    """Busca políticas y datos del proyecto; úsala para preguntas sobre reintentos,
    cálculo de costos o los tokens reportados por Gemini.
    """
    documentacion = {
        "reintentos": (
            "El cliente reintenta errores transitorios hasta 3 veces en total, "
            "con backoff exponencial y jitter. No reintenta errores de "
            "autenticación 401/403."
        ),
        "costos": (
            "El costo se estima con los tokens de entrada, salida y, si Gemini "
            "lo informa por separado, los tokens de pensamiento. El proyecto "
            "usa las tarifas configuradas en src/GATE_2/costo.py."
        ),
        "tokens": (
            "Gemini informa promptTokenCount, candidatesTokenCount y "
            "totalTokenCount en usageMetadata. thoughtsTokenCount puede "
            "aparecer por separado."
        ),
    }
    consulta_normalizada = consulta.casefold()
    for tema, respuesta in documentacion.items():
        if tema in consulta_normalizada:
            return respuesta
    return "No se encontró información sobre esa consulta en la documentación."


class ArgumentosCostoTokens(BaseModel):
    """Argumentos validados para estimar costos de uso de Gemini."""

    tokens_entrada: int = Field(
        ge=0,
        description="Cantidad no negativa de tokens de entrada reportados por Gemini.",
    )
    tokens_salida: int = Field(
        ge=0,
        description="Cantidad no negativa de tokens de salida reportados por Gemini.",
    )
    tokens_pensamiento: int = Field(
        default=0,
        ge=0,
        description=(
            "Tokens de pensamiento no negativos, si Gemini los reporta aparte; "
            "por defecto es 0."
        ),
    )


@tool("calcular_costo_tokens_gemini", args_schema=ArgumentosCostoTokens)
def calcular_costo_tokens(
    tokens_entrada: int,
    tokens_salida: int,
    tokens_pensamiento: int = 0,
) -> str:
    """Estima en USD el costo Gemini para cantidades conocidas de tokens.

    Úsala cuando la consulta pide calcular el costo y proporciona los tokens
    de entrada y salida; incluye tokens de pensamiento si se conocen.
    """
    datos = {
        "usageMetadata": {
            "promptTokenCount": tokens_entrada,
            "candidatesTokenCount": tokens_salida,
            "totalTokenCount": tokens_entrada + tokens_salida + tokens_pensamiento,
            "thoughtsTokenCount": tokens_pensamiento,
        }
    }
    try:
        costo = calcular_costo(datos)
    except ValueError as error:
        return f"No se pudo calcular el costo: {error}"

    return (
        f"Costo estimado: USD {costo:.8f} "
        f"(entrada: {tokens_entrada} tokens a "
        f"USD {PRECIO_ENTRADA_POR_TOKEN:.8f}/token; salida y pensamiento: "
        f"{tokens_salida + tokens_pensamiento} tokens a "
        f"USD {PRECIO_SALIDA_POR_TOKEN:.8f}/token)."
    )


def obtener_herramientas() -> list[BaseTool]:
    """Devuelve las herramientas disponibles para el agente."""
    return [buscar_en_documentacion, calcular_costo_tokens]


def construir_ejecutor_agente(
    modelo: BaseChatModel, *, verbose: bool = False
) -> AgentExecutor:
    """Construye el agente y su traza, con historial opcional de conversación."""
    herramientas = obtener_herramientas()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres un asistente técnico del proyecto. Usa las herramientas "
                "para responder preguntas sobre datos específicos del proyecto "
                "o para calcular costos con cantidades de tokens conocidas. "
                "No inventes datos que no estén en la documentación. Si la "
                "pregunta es general, responde directamente.",
            ),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{entrada}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agente = create_tool_calling_agent(modelo, herramientas, prompt)
    return AgentExecutor(
        agent=agente,
        tools=herramientas,
        verbose=verbose,
        return_intermediate_steps=True,
        max_iterations=5,
    )


class EstadoConversacion(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    output: str
    intermediate_steps: list[tuple[AgentAction, str]]


AplicacionConversacion = CompiledStateGraph[
    EstadoConversacion,
    None,
    EstadoConversacion,
    EstadoConversacion,
]

aplicaciones_por_sesion: dict[str, AplicacionConversacion] = {}


def obtener_historial(session_id: str) -> list[BaseMessage]:
    """Devuelve los mensajes del estado persistido en memoria de LangGraph."""
    aplicacion = aplicaciones_por_sesion.get(session_id)
    if aplicacion is None:
        return []
    estado = aplicacion.get_state(
        {"configurable": {"thread_id": session_id}}
    )
    return list(estado.values.get("messages", []))


def cerrar_sesion(session_id: str) -> None:
    """Elimina el grafo y su checkpoint en memoria asociado a la sesión."""
    aplicaciones_por_sesion.pop(session_id, None)


def _normalizar_respuesta_agente(
    resultado: Mapping[str, Any],
) -> dict[str, Any]:
    """Convierte bloques de texto del proveedor en texto antes de guardar historial."""
    salida = resultado.get("output")
    if isinstance(salida, str):
        return dict(resultado)
    if not isinstance(salida, list):
        raise TypeError("La salida del agente debe ser texto o una lista de bloques.")

    fragmentos: list[str] = []
    for bloque in salida:
        if isinstance(bloque, str):
            fragmentos.append(bloque)
        elif isinstance(bloque, Mapping) and bloque.get("type") == "text":
            texto = bloque.get("text")
            if not isinstance(texto, str):
                raise ValueError("Un bloque de texto del agente no contiene texto.")
            fragmentos.append(texto)
        else:
            raise ValueError(
                "La salida del agente contiene un bloque que no es de texto."
            )

    if not fragmentos:
        raise ValueError("La salida del agente no contiene texto.")
    return {**resultado, "output": "".join(fragmentos)}


def construir_agente_con_memoria(
    ejecutor: AgentExecutor,
) -> Runnable[dict[str, Any], dict[str, Any]]:
    """Conserva mensajes por sesión usando el checkpoint en memoria de LangGraph."""
    ejecutor_con_salida_texto: Runnable[dict[str, Any], dict[str, Any]] = (
        ejecutor | _normalizar_respuesta_agente
    )

    def responder(estado: EstadoConversacion) -> dict[str, Any]:
        mensajes = estado.get("messages", [])
        if not mensajes or not isinstance(mensajes[-1], HumanMessage):
            raise ValueError("El estado debe terminar con un mensaje del usuario.")
        entrada = mensajes[-1].content
        if not isinstance(entrada, str):
            raise TypeError("El mensaje del usuario debe contener texto.")
        resultado = ejecutor_con_salida_texto.invoke(
            {
                "entrada": entrada,
                "chat_history": mensajes[:-1],
            }
        )
        salida = resultado.get("output")
        if not isinstance(salida, str):
            raise TypeError("La salida del agente debe ser texto.")
        return {
            "messages": [AIMessage(content=salida)],
            "output": salida,
            "intermediate_steps": resultado.get("intermediate_steps", []),
        }

    grafo = StateGraph(EstadoConversacion)
    grafo.add_node("responder", responder)
    grafo.add_edge(START, "responder")
    grafo.add_edge("responder", END)
    aplicacion = grafo.compile(checkpointer=InMemorySaver())

    def ejecutar(
        entrada: dict[str, Any],
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        configurable = config.get("configurable", {}) if config else {}
        if not isinstance(configurable, Mapping):
            raise TypeError("La configuración del agente debe ser un mapa.")
        session_id = configurable.get("session_id")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("La configuración requiere un session_id no vacío.")
        contenido = entrada.get("entrada")
        if not isinstance(contenido, str) or not contenido.strip():
            raise ValueError("La entrada del agente debe ser un texto no vacío.")

        aplicacion_sesion = aplicaciones_por_sesion.get(session_id)
        if aplicacion_sesion is None:
            aplicaciones_por_sesion[session_id] = aplicacion
            aplicacion_sesion = aplicacion
        estado = aplicacion_sesion.invoke(
            {"messages": [HumanMessage(content=contenido)]},
            {"configurable": {"thread_id": session_id}},
        )
        salida = estado.get("output")
        if not isinstance(salida, str):
            raise TypeError("El estado del agente no contiene una salida de texto.")
        return {
            "output": salida,
            "intermediate_steps": estado.get("intermediate_steps", []),
        }

    return RunnableLambda(ejecutar)


def main() -> int:
    """Ejecuta un ejemplo real; requiere credenciales y puede generar costo."""
    project_root = Path(__file__).resolve().parents[2]

    modelo = crear_chat_modelo()
    ejecutor = construir_ejecutor_agente(modelo, verbose=True)
    agente_con_memoria = construir_agente_con_memoria(ejecutor)
    config = {"configurable": {"session_id": "demostracion-bloque-22"}}
    for entrada in (
        "¿Cuánto cuesta una respuesta con 1000 tokens de entrada y 200 de salida?",
        "¿Y cuánto costaría si duplico solo los tokens de entrada?",
    ):
        resultado = agente_con_memoria.invoke(
            {"entrada": entrada},
            config,
        )
        registrar_traza(
            session_id=config["configurable"]["session_id"],
            entrada=entrada,
            resultado=resultado,
            archivo=project_root / "trazas_agente.jsonl",
        )
        print("\nAcciones y observaciones:")
        for accion, observacion in resultado["intermediate_steps"]:
            print(f"{accion.tool} {accion.tool_input} -> {observacion}")
        print("\nRespuesta:")
        print(resultado["output"])
    cerrar_sesion(config["configurable"]["session_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
