"""Pruebas del agente y sus herramientas sin llamadas a Gemini."""

import sys
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from pydantic import Field, ValidationError

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1.agente_con_herramientas import (  # noqa: E402
    buscar_en_documentacion,
    calcular_costo_tokens,
    cerrar_sesion,
    construir_ejecutor_agente,
    construir_agente_con_memoria,
    obtener_historial,
)
from src.GATE_1.costo import (  # noqa: E402
    PRECIO_ENTRADA_POR_TOKEN,
    PRECIO_SALIDA_POR_TOKEN,
)


class ModeloConHerramientasFalso(BaseChatModel):
    """Reproduce llamadas a herramientas para probar la traza sin red."""

    respuestas: list[AIMessage]
    indice_respuesta: int = 0
    mensajes_recibidos: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "modelo-falso-con-herramientas"

    def bind_tools(
        self,
        tools: list[Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[Any, AIMessage]:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.mensajes_recibidos.append(messages)
        respuesta = self.respuestas[self.indice_respuesta]
        if self.indice_respuesta < len(self.respuestas) - 1:
            self.indice_respuesta += 1
        return ChatResult(generations=[ChatGeneration(message=respuesta)])


def test_busqueda_documental_devuelve_politica_de_reintentos() -> None:
    resultado = buscar_en_documentacion.invoke("¿Cuántos reintentos hay?")

    assert "3 veces" in resultado
    assert "401/403" in resultado


def test_calculo_de_costo_usa_tarifas_del_proyecto() -> None:
    resultado = calcular_costo_tokens.invoke(
        {
            "tokens_entrada": 1000,
            "tokens_salida": 200,
            "tokens_pensamiento": 50,
        }
    )
    costo_esperado = (
        1000 * PRECIO_ENTRADA_POR_TOKEN
        + 250 * PRECIO_SALIDA_POR_TOKEN
    )

    assert f"USD {costo_esperado:.8f}" in resultado


def test_herramienta_de_costo_tiene_nombre_y_esquema_descriptivos() -> None:
    esquema = calcular_costo_tokens.args_schema

    assert calcular_costo_tokens.name == "calcular_costo_tokens_gemini"
    assert esquema is not None
    assert set(esquema.model_fields) == {
        "tokens_entrada",
        "tokens_salida",
        "tokens_pensamiento",
    }
    assert all(
        campo.description for campo in esquema.model_fields.values()
    )
    assert esquema.model_fields["tokens_pensamiento"].default == 0


def test_esquema_rechaza_contadores_negativos_antes_de_ejecutar() -> None:
    with pytest.raises(ValidationError):
        calcular_costo_tokens.invoke(
            {"tokens_entrada": -1, "tokens_salida": 200}
        )


def test_agente_registra_herramienta_y_observacion_en_pasos_intermedios() -> None:
    modelo = ModeloConHerramientasFalso(
        respuestas=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "buscar_en_documentacion",
                        "args": {"consulta": "reintentos"},
                        "id": "llamada-1",
                    }
                ],
            ),
            AIMessage(content="El cliente reintenta hasta 3 veces."),
        ]
    )
    ejecutor = construir_ejecutor_agente(modelo)

    resultado = ejecutor.invoke({"entrada": "¿Cuántos reintentos hace?"})

    assert resultado["intermediate_steps"][0][0].tool == "buscar_en_documentacion"
    assert "3 veces" in resultado["intermediate_steps"][0][1]
    assert "3 veces" in resultado["output"]


def test_agente_encadena_busqueda_y_calculo_en_orden() -> None:
    modelo = ModeloConHerramientasFalso(
        respuestas=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "buscar_en_documentacion",
                        "args": {"consulta": "costos"},
                        "id": "llamada-1",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calcular_costo_tokens_gemini",
                        "args": {
                            "tokens_entrada": 1000,
                            "tokens_salida": 200,
                        },
                        "id": "llamada-2",
                    }
                ],
            ),
            AIMessage(content="El costo estimado está basado en esos tokens."),
        ]
    )
    ejecutor = construir_ejecutor_agente(modelo)

    resultado = ejecutor.invoke(
        {"entrada": "¿Cómo se calcula el costo de 1000 tokens de entrada y 200 de salida?"}
    )

    pasos = resultado["intermediate_steps"]
    assert [accion.tool for accion, _ in pasos] == [
        "buscar_en_documentacion",
        "calcular_costo_tokens_gemini",
    ]
    assert "tarifas configuradas" in pasos[0][1]
    assert "USD 0.00150000" in pasos[1][1]


def test_agente_puede_responder_sin_usar_herramientas() -> None:
    modelo = ModeloConHerramientasFalso(
        respuestas=[AIMessage(content="LangChain permite componer flujos.")],
    )
    ejecutor = construir_ejecutor_agente(modelo)

    resultado = ejecutor.invoke({"entrada": "¿Qué es LangChain?"})

    assert resultado["intermediate_steps"] == []
    assert resultado["output"] == "LangChain permite componer flujos."


def test_memoria_conserva_contexto_entre_turnos_de_la_misma_sesion() -> None:
    modelo = ModeloConHerramientasFalso(
        respuestas=[
            AIMessage(content="El primer costo fue USD 0.0015."),
            AIMessage(content="Conservo el contexto de la pregunta anterior."),
        ]
    )
    agente = construir_agente_con_memoria(construir_ejecutor_agente(modelo))
    config = {"configurable": {"session_id": "prueba-memoria-misma"}}

    agente.invoke({"entrada": "Calcula el primer costo."}, config)
    resultado = agente.invoke({"entrada": "¿Y si duplico la entrada?"}, config)

    assert "Calcula el primer costo." in [
        mensaje.content for mensaje in modelo.mensajes_recibidos[1]
    ]
    assert "El primer costo fue USD 0.0015." in [
        mensaje.content for mensaje in modelo.mensajes_recibidos[1]
    ]
    assert len(obtener_historial("prueba-memoria-misma").messages) == 4
    assert resultado["output"] == "Conservo el contexto de la pregunta anterior."
    cerrar_sesion("prueba-memoria-misma")


def test_memoria_normaliza_bloques_de_texto_del_modelo_entre_turnos() -> None:
    texto = "La respuesta incluye USD 0.0015."
    modelo = ModeloConHerramientasFalso(
        respuestas=[
            AIMessage(
                content=[
                    {
                        "type": "text",
                        "text": texto,
                        "index": 0,
                        "extras": {"signature": "firma-de-prueba"},
                    }
                ]
            ),
            AIMessage(content="Conservo la respuesta anterior."),
        ]
    )
    agente = construir_agente_con_memoria(construir_ejecutor_agente(modelo))
    config = {"configurable": {"session_id": "prueba-memoria-bloques"}}

    primera_respuesta = agente.invoke({"entrada": "Calcula el costo."}, config)
    segunda_respuesta = agente.invoke(
        {"entrada": "¿Cuál fue el resultado?"},
        config,
    )

    assert primera_respuesta["output"] == texto
    assert texto in [mensaje.content for mensaje in modelo.mensajes_recibidos[1]]
    assert segunda_respuesta["output"] == "Conservo la respuesta anterior."
    assert all(
        isinstance(mensaje.content, str)
        for mensaje in obtener_historial("prueba-memoria-bloques").messages
    )
    cerrar_sesion("prueba-memoria-bloques")


def test_memoria_aisla_sesiones_y_permite_cerrar_sesion() -> None:
    modelo = ModeloConHerramientasFalso(
        respuestas=[
            AIMessage(content="Respuesta de la sesión uno."),
            AIMessage(content="No hay contexto previo en esta sesión."),
        ]
    )
    agente = construir_agente_con_memoria(construir_ejecutor_agente(modelo))
    config_uno = {"configurable": {"session_id": "prueba-aislamiento-uno"}}
    config_dos = {"configurable": {"session_id": "prueba-aislamiento-dos"}}

    agente.invoke({"entrada": "Dato privado de la sesión uno."}, config_uno)
    resultado = agente.invoke({"entrada": "¿Qué dato compartí?"}, config_dos)

    assert "Dato privado de la sesión uno." not in [
        mensaje.content for mensaje in modelo.mensajes_recibidos[1]
    ]
    assert len(obtener_historial("prueba-aislamiento-uno").messages) == 2
    assert len(obtener_historial("prueba-aislamiento-dos").messages) == 2
    assert resultado["output"] == "No hay contexto previo en esta sesión."

    cerrar_sesion("prueba-aislamiento-uno")
    cerrar_sesion("prueba-aislamiento-dos")
    cerrar_sesion("sesion-inexistente")
    assert obtener_historial("prueba-aislamiento-uno").messages == []
    cerrar_sesion("prueba-aislamiento-uno")
