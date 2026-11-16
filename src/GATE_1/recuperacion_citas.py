"""Recupera contexto del vector store y responde con referencias a sus fuentes."""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __package__:
    from .configuracion import crear_chat_modelo
    from .indexar_corpus import (
        CORPUS_DOCUMENTOS,
        RUTA_VECTORSTORE,
        crear_embeddings,
        indexar_corpus,
    )
else:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from src.GATE_1.configuracion import crear_chat_modelo
    from src.GATE_1.indexar_corpus import (
        CORPUS_DOCUMENTOS,
        RUTA_VECTORSTORE,
        crear_embeddings,
        indexar_corpus,
    )

if TYPE_CHECKING:
    from langchain_chroma import Chroma

PREGUNTAS_DEMO = (
    "¿Qué errores reintenta el cliente y cuántos intentos hace?",
    "¿Qué información registra el sistema en las trazas del agente?",
)
PATRON_CITA = re.compile(r"\[(\d+)\]")
FRASES_SIN_RESPUESTA = (
    "no se recuperó contexto",
    "no hay contexto",
    "no hay información",
    "no cuento con información",
    "no es posible responder",
)


def formatear_contexto(
    documentos: Sequence[Document],
) -> tuple[str, dict[int, str]]:
    """Numera los fragmentos recuperados y devuelve su mapa de fuentes."""
    fragmentos: list[str] = []
    fuentes: dict[int, str] = {}

    for numero, documento in enumerate(documentos, start=1):
        fuente = documento.metadata.get("source")
        if not isinstance(fuente, str) or not fuente.strip():
            raise ValueError(
                f"El fragmento {numero} no tiene metadatos source válidos."
            )
        contenido = documento.page_content.strip()
        if not contenido:
            raise ValueError(f"El fragmento {numero} no tiene contenido.")

        fuentes[numero] = fuente
        fragmentos.append(f"[{numero}] Fuente: {fuente}\n{contenido}")

    return "\n\n".join(fragmentos), fuentes


def construir_prompt(pregunta: str, contexto: str) -> str:
    """Construye una instrucción que restringe respuestas y citas al contexto."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser un texto no vacío.")
    if not isinstance(contexto, str):
        raise ValueError("El contexto debe ser texto.")

    contexto_final = contexto.strip() or "No se recuperó contexto pertinente."
    return (
        "Responde la pregunta usando SOLO el contexto de abajo. "
        "Cita cada afirmación factual con el número de su fuente entre "
        "corchetes, por ejemplo [1]. Si el contexto no alcanza para responder, "
        "dilo explícitamente en vez de inventar.\n\n"
        f"Contexto:\n{contexto_final}\n\n"
        f"Pregunta: {pregunta.strip()}\n"
        "Respuesta:"
    )


def validar_citas(respuesta: str, fuentes: dict[int, str]) -> None:
    """Rechaza referencias inexistentes y respuestas sin citas cuando hay contexto."""
    numeros_citados = {
        int(numero)
        for numero in PATRON_CITA.findall(respuesta)
    }
    desconocidos = numeros_citados - fuentes.keys()
    if desconocidos:
        raise ValueError(
            "La respuesta incluye números de cita no recuperados: "
            + ", ".join(f"[{numero}]" for numero in sorted(desconocidos))
        )

    es_abstencion = any(
        frase in respuesta.casefold()
        for frase in FRASES_SIN_RESPUESTA
    )
    if fuentes and not numeros_citados and not es_abstencion:
        raise ValueError(
            "La respuesta no incluye citas para el contexto recuperado."
        )


def responder_con_citas(
    pregunta: str,
    vectorstore: Chroma,
    modelo: BaseChatModel,
    *,
    cantidad_resultados: int = 3,
) -> tuple[str, dict[int, str]]:
    """Recupera documentos, consulta el modelo y retorna respuesta y fuentes."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser un texto no vacío.")
    if (
        not isinstance(cantidad_resultados, int)
        or isinstance(cantidad_resultados, bool)
        or cantidad_resultados <= 0
    ):
        raise ValueError("cantidad_resultados debe ser un entero positivo.")

    documentos = vectorstore.similarity_search(
        pregunta,
        k=cantidad_resultados,
    )
    contexto, fuentes = formatear_contexto(documentos)
    resultado = modelo.invoke(construir_prompt(pregunta, contexto))
    contenido = resultado.content
    if isinstance(contenido, str):
        respuesta = contenido
    elif isinstance(contenido, list):
        partes = [
            bloque["text"]
            for bloque in contenido
            if isinstance(bloque, dict)
            and bloque.get("type") == "text"
            and isinstance(bloque.get("text"), str)
        ]
        respuesta = "".join(partes)
    else:
        raise TypeError("El modelo devolvió una respuesta sin texto compatible.")

    if not respuesta.strip():
        raise ValueError("El modelo devolvió una respuesta vacía.")
    respuesta = respuesta.strip()
    validar_citas(respuesta, fuentes)
    return respuesta, fuentes


def main(
    embeddings: Embeddings | None = None,
    modelo: BaseChatModel | None = None,
    persist_directory: str | Path = RUTA_VECTORSTORE,
) -> int:
    """Reindexa y ejecuta dos consultas RAG con fuentes numeradas."""
    try:
        print("PASO 1: reindexando el corpus del proyecto con metadatos")
        embeddings_activos = embeddings or crear_embeddings()
        vectorstore = indexar_corpus(
            embeddings_activos,
            persist_directory=persist_directory,
        )
        cantidad = len(vectorstore.get()["ids"])
        print(
            f"Reindexados {cantidad} chunks en {persist_directory}, "
            "con metadata source y chunk_index."
        )
        if cantidad < len(CORPUS_DOCUMENTOS):
            print(
                f"Se esperaban al menos {len(CORPUS_DOCUMENTOS)} chunks, "
                f"pero Chroma informa {cantidad}.",
                file=sys.stderr,
            )
            return 1

        print("\nPASO 2: preparando el formato de contexto y el prompt")
        modelo_activo = modelo or crear_chat_modelo()
        print("formatear_contexto y construir_prompt listas.")

        print("\nPASO 3: recuperando y respondiendo dos preguntas con citas")
        for indice, pregunta in enumerate(PREGUNTAS_DEMO, start=1):
            respuesta, fuentes = responder_con_citas(
                pregunta,
                vectorstore,
                modelo_activo,
            )
            print(f"\nPregunta {indice}: {pregunta}")
            print(f"Respuesta:\n{respuesta}")
            print(f"citas: {fuentes}")
    except (OSError, ValueError, TypeError) as error:
        print(f"No se pudo completar la recuperación con citas: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
