"""Agente de soporte que consulta documentación y estima costos de Gemini."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool, tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
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
    from src.GATE_1.configuracion import crear_chat_modelo
    from src.GATE_1.costo import (
        PRECIO_ENTRADA_POR_TOKEN,
        PRECIO_SALIDA_POR_TOKEN,
        calcular_costo,
    )
    from src.GATE_1.trazas_agente import registrar_traza


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
            "usa las tarifas configuradas en src/GATE_1/costo.py."
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


historiales: dict[str, InMemoryChatMessageHistory] = {}


def obtener_historial(session_id: str) -> BaseChatMessageHistory:
    """Devuelve el historial en memoria asociado a una sesión."""
    if session_id not in historiales:
        historiales[session_id] = InMemoryChatMessageHistory()
    return historiales[session_id]


def cerrar_sesion(session_id: str) -> None:
    """Elimina el historial en memoria de una sesión, si existe."""
    historiales.pop(session_id, None)


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
) -> RunnableWithMessageHistory:
    """Envuelve el ejecutor para conservar mensajes separados por session_id."""
    ejecutor_con_salida_texto: Runnable[dict[str, Any], dict[str, Any]] = (
        ejecutor | _normalizar_respuesta_agente
    )
    return RunnableWithMessageHistory(
        ejecutor_con_salida_texto,
        obtener_historial,
        input_messages_key="entrada",
        history_messages_key="chat_history",
    )


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
