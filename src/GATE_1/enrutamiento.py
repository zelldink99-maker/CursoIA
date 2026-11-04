"""Enruta mensajes de soporte a una respuesta según su categoría."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)

logger = logging.getLogger(__name__)


def _normalizar_categoria(categoria: str) -> str:
    return categoria.strip().lower()


def _construir_cadena_segura(cadena: Runnable[Any, Any]) -> Runnable[Any, Any]:
    respuesta_generica = RunnableLambda(
        lambda _: (
            "Gracias por tu mensaje. Un miembro de nuestro "
            "equipo te va a responder pronto."
        )
    )
    return cadena.with_fallbacks([respuesta_generica])


def construir_cadena_queja_segura(
    cadena_queja: Runnable[Any, Any],
) -> Runnable[Any, Any]:
    """Agrega una respuesta genérica de respaldo a la ruta de quejas."""
    return _construir_cadena_segura(cadena_queja)


def construir_paso_clasificacion(modelo: Runnable[Any, Any]) -> Runnable[Any, str]:
    """Clasifica y normaliza el tipo de mensaje antes de enrutarlo."""
    plantilla = PromptTemplate.from_template(
        "Clasifica el siguiente mensaje de soporte en una sola palabra: "
        "pregunta, queja o sugerencia. Responde solo con esa palabra.\n\n"
        "{mensaje}"
    )
    return (
        plantilla
        | modelo
        | StrOutputParser()
        | RunnableLambda(_normalizar_categoria)
    )


def construir_cadena_con_enrutamiento(
    paso_clasificacion: Runnable[Any, str],
    cadena_queja: Runnable[Any, Any] | None = None,
    cadena_sugerencia: Runnable[Any, Any] | None = None,
    cadena_pregunta: Runnable[Any, Any] | None = None,
) -> Runnable[Any, Any]:
    """Conecta el clasificador a las rutas; pregunta es la ruta por defecto."""
    ruta_queja = (
        cadena_queja if cadena_queja is not None else RunnablePassthrough()
    )
    ruta_sugerencia = (
        cadena_sugerencia
        if cadena_sugerencia is not None
        else RunnablePassthrough()
    )
    ruta_pregunta = (
        cadena_pregunta if cadena_pregunta is not None else RunnablePassthrough()
    )
    ruta_queja_segura = construir_cadena_queja_segura(ruta_queja)
    ruta_sugerencia_segura = _construir_cadena_segura(ruta_sugerencia)
    ruta_pregunta_segura = _construir_cadena_segura(ruta_pregunta)
    bifurcacion = RunnableBranch(
        (lambda entrada: entrada["categoria"] == "queja", ruta_queja_segura),
        (
            lambda entrada: entrada["categoria"] == "sugerencia",
            ruta_sugerencia_segura,
        ),
        ruta_pregunta_segura,
    )
    return RunnablePassthrough.assign(categoria=paso_clasificacion) | bifurcacion


def procesar_mensaje_seguro(
    cadena: Runnable[Any, Any], mensaje: str
) -> Any:
    """Invoca el flujo y devuelve un mensaje seguro ante fallos no cubiertos."""
    try:
        return cadena.invoke({"mensaje": mensaje})
    except Exception:
        logger.exception("Error procesando mensaje")
        return (
            "No pudimos procesar tu mensaje en este momento. "
            "Intenta de nuevo más tarde."
        )


def construir_cadena(modelo: Runnable[Any, Any]) -> Runnable[Any, str]:
    """Construye el flujo completo usando el modelo para clasificar y responder."""
    parser_salida = StrOutputParser()
    cadena_pregunta = (
        PromptTemplate.from_template(
            "Responde esta pregunta técnica con precisión:\n\n{mensaje}"
        )
        | modelo
        | parser_salida
    )
    cadena_queja = (
        PromptTemplate.from_template(
            "Responde a esta queja con empatía, reconociendo el problema "
            "antes de ofrecer una solución:\n\n{mensaje}"
        )
        | modelo
        | parser_salida
    )
    cadena_sugerencia = (
        PromptTemplate.from_template(
            "Agradece esta sugerencia y explica cómo se evaluará dentro "
            "del producto:\n\n{mensaje}"
        )
        | modelo
        | parser_salida
    )
    return construir_cadena_con_enrutamiento(
        paso_clasificacion=construir_paso_clasificacion(modelo),
        cadena_queja=cadena_queja,
        cadena_sugerencia=cadena_sugerencia,
        cadena_pregunta=cadena_pregunta,
    )


def main() -> int:
    """Ejecuta un ejemplo real; requiere credenciales y puede costar."""
    from dotenv import load_dotenv
    from langchain_google_genai import ChatGoogleGenerativeAI

    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=project_root / ".env")

    modelo = ChatGoogleGenerativeAI(model="gemini-3.5-flash")
    cadena = construir_cadena(modelo)
    print(procesar_mensaje_seguro(cadena, "La app se cierra al subir una foto."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
