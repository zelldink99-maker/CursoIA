"""Replica la indexación de un corpus de ejemplo en una colección separada."""

from __future__ import annotations

import math
import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

if TYPE_CHECKING:
    from langchain_chroma import Chroma

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PERSIST_DIR = (PROJECT_ROOT / "vectorstore_ejemplo").resolve()
NOMBRE_COLECCION = "replica_corpus_ejemplo"
MODELO_EMBEDDINGS = "models/gemini-embedding-001"
CORPUS_EJEMPLO = (
    "Los pedidos se pueden cancelar dentro de las primeras 24 horas despues de "
    "realizados, sin costo adicional.",
    "Las devoluciones se aceptan hasta 30 dias despues de la entrega, siempre que "
    "el producto este sin usar.",
    "El reembolso se procesa en un plazo de 5 a 10 dias habiles despues de recibir "
    "el producto devuelto.",
    "Los productos en oferta o liquidacion no tienen devolucion, salvo defecto de "
    "fabrica.",
    "El envio de una devolucion corre por cuenta del cliente, excepto cuando el "
    "producto llego danado.",
)

T = TypeVar("T")


def dividir_corpus(
    corpus: Sequence[str] = CORPUS_EJEMPLO,
) -> list[Document]:
    """Divide cada texto del corpus con los parámetros de la lección."""
    if not corpus or any(not isinstance(texto, str) or not texto.strip() for texto in corpus):
        raise ValueError("El corpus debe contener textos no vacíos.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=150,
        chunk_overlap=20,
    )
    return splitter.create_documents(list(corpus))


def verificar_integridad(
    chunks: Sequence[Document],
    corpus: Sequence[str] = CORPUS_EJEMPLO,
) -> None:
    """Imprime las comprobaciones locales y falla si el ejemplo está incompleto."""
    vacios = [
        indice
        for indice, chunk in enumerate(chunks)
        if not chunk.page_content.strip()
    ]
    textos = [chunk.page_content for chunk in chunks]
    hay_duplicados = len(textos) != len(set(textos))
    total_chars_chunks = sum(len(texto) for texto in textos)
    total_chars_corpus = sum(len(texto) for texto in corpus)

    print("chunks vacios:", vacios)
    print("hay duplicados:", hay_duplicados)
    print("total de caracteres en los chunks:", total_chars_chunks)
    print("total de caracteres en el corpus original:", total_chars_corpus)

    if (
        vacios
        or hay_duplicados
        or len(chunks) != len(corpus)
        or textos != list(corpus)
    ):
        raise ValueError("La integridad de los chunks no coincide con el corpus.")


def con_reintentos(
    operacion: Callable[[], T],
    max_intentos: int = 4,
    espera_inicial: float = 5,
) -> T:
    """Reintenta únicamente errores de cuota 429 con espera exponencial."""
    if not callable(operacion):
        raise ValueError("La operación debe ser invocable.")
    if (
        not isinstance(max_intentos, int)
        or isinstance(max_intentos, bool)
        or max_intentos <= 0
    ):
        raise ValueError("max_intentos debe ser un entero mayor que cero.")
    if (
        not isinstance(espera_inicial, (int, float))
        or isinstance(espera_inicial, bool)
        or not math.isfinite(espera_inicial)
        or espera_inicial < 0
    ):
        raise ValueError("espera_inicial debe ser un número finito no negativo.")

    espera = float(espera_inicial)
    for intento in range(1, max_intentos + 1):
        try:
            return operacion()
        except Exception as error:
            mensaje = str(error).upper()
            es_limite = "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje
            if not es_limite or intento == max_intentos:
                raise

            print(
                "Límite de peticiones alcanzado. "
                f"Reintento {intento} de {max_intentos - 1} en {espera:g} s..."
            )
            time.sleep(espera)
            espera *= 2

    raise RuntimeError("El flujo de reintentos terminó inesperadamente.")


def crear_embeddings() -> Embeddings:
    """Carga la clave de la raíz del proyecto y prepara Gemini Embeddings."""
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise ValueError(
            f'Falta GEMINI_API_KEY. Defínela en "{PROJECT_ROOT / ".env"}".'
        )

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)


def indexar_chunks(
    chunks: Sequence[Document],
    embeddings: Embeddings,
    persist_directory: str | Path = PERSIST_DIR,
) -> Chroma:
    """Persiste los chunks con IDs estables para evitar duplicados al reejecutar."""
    from langchain_chroma import Chroma

    ids = [f"corpus-ejemplo-{indice}" for indice in range(len(chunks))]
    return Chroma.from_documents(
        documents=list(chunks),
        embedding=embeddings,
        ids=ids,
        collection_name=NOMBRE_COLECCION,
        persist_directory=str(Path(persist_directory).resolve()),
    )


def abrir_vectorstore(
    embeddings: Embeddings,
    persist_directory: str | Path = PERSIST_DIR,
) -> Chroma:
    """Reconecta a la colección de ejemplo sin recalcular los embeddings."""
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=NOMBRE_COLECCION,
        embedding_function=embeddings,
        persist_directory=str(Path(persist_directory).resolve()),
    )


def main(
    persist_directory: str | Path = PERSIST_DIR,
    embeddings: Embeddings | None = None,
) -> int:
    """Ejecuta la réplica; la indexación real requiere clave y llamadas a Gemini."""
    chunks = dividir_corpus()
    print("5 chunks generados")
    for indice, chunk in enumerate(chunks):
        print(f"--- chunk {indice} ({len(chunk.page_content)} caracteres) ---")
        print(chunk.page_content)

    verificar_integridad(chunks)
    ruta = Path(persist_directory).resolve()
    print("Ruta del índice:", ruta)

    try:
        modelo_embeddings = embeddings if embeddings is not None else crear_embeddings()
        con_reintentos(
            lambda: indexar_chunks(chunks, modelo_embeddings, ruta),
        )
        recargado = abrir_vectorstore(modelo_embeddings, ruta)
        cantidad = len(recargado.get()["ids"])
    except Exception as error:
        mensaje = str(error)
        mensaje_normalizado = mensaje.upper()
        if "FALTA GEMINI_API_KEY" in mensaje_normalizado:
            print(mensaje, file=sys.stderr)
        elif (
            "API KEY" in mensaje_normalizado
            or "401" in mensaje_normalizado
            or "403" in mensaje_normalizado
        ):
            print(
                'La API rechazó tu clave. Revisa GEMINI_API_KEY en ".env".',
                file=sys.stderr,
            )
            print("Detalle técnico:", mensaje, file=sys.stderr)
        elif "429" in mensaje_normalizado or "RESOURCE_EXHAUSTED" in mensaje_normalizado:
            print(
                "Límite de peticiones alcanzado. Espera un minuto y vuelve a "
                "ejecutar.",
                file=sys.stderr,
            )
            print("Detalle técnico:", mensaje, file=sys.stderr)
        else:
            print(
                f"No se pudo indexar el corpus: {type(error).__name__}",
                file=sys.stderr,
            )
            print("Detalle técnico:", mensaje, file=sys.stderr)
        return 1

    if cantidad != len(chunks):
        print(
            f"Se esperaban {len(chunks)} chunks persistidos y se encontraron "
            f"{cantidad}.",
            file=sys.stderr,
        )
        return 1

    print(f"Indexados {cantidad} chunks en {ruta}")
    print(f"Chunks recuperados al reconectar: {cantidad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
