"""Chain de tres pasos para transformar texto técnico en viñetas sencillas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda


def _envolver_puntos(puntos: str) -> dict[str, str]:
    """Adapta la salida de extracción a la entrada de simplificación."""
    return {"puntos": puntos}


def _envolver_texto_simple(texto_simple: str) -> dict[str, str]:
    """Adapta la salida simplificada a la entrada de formato."""
    return {"texto_simple": texto_simple}


def construir_cadena(modelo: Runnable[Any, Any]) -> Runnable[Any, str]:
    """Construye la chain inyectando el modelo para facilitar pruebas aisladas."""
    plantilla_extraccion = PromptTemplate.from_template(
        "Lee el siguiente texto y devuelve solo sus 3 puntos clave, "
        "uno por línea, sin desarrollarlos:\n\n{texto}"
    )
    plantilla_simplificacion = PromptTemplate.from_template(
        "Reescribe estos puntos en lenguaje simple, sin jerga técnica, "
        "para alguien sin conocimientos previos:\n\n{puntos}"
    )
    plantilla_formato = PromptTemplate.from_template(
        "Convierte este texto en una lista de viñetas markdown, "
        "de máximo 3 líneas, sin introducción:\n\n{texto_simple}"
    )
    parser_salida = StrOutputParser()

    return (
        plantilla_extraccion
        | modelo
        | parser_salida
        | RunnableLambda(_envolver_puntos)
        | plantilla_simplificacion
        | modelo
        | parser_salida
        | RunnableLambda(_envolver_texto_simple)
        | plantilla_formato
        | modelo
        | parser_salida
    )


def main() -> int:
    """Ejecuta la chain de ejemplo; requiere credenciales y puede costar."""
    from dotenv import load_dotenv
    from langchain_google_genai import ChatGoogleGenerativeAI

    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=project_root / ".env")

    modelo = ChatGoogleGenerativeAI(model="gemini-3.5-flash")
    cadena = construir_cadena(modelo)
    texto = (
        "Los modelos de lenguaje procesan el texto dividiéndolo en tokens. "
        "Un token puede ser una palabra completa, parte de una palabra o un "
        "signo de puntuación. El modelo predice un token a la vez usando el "
        "contexto previo para generar su respuesta."
    )
    print(cadena.invoke({"texto": texto}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
