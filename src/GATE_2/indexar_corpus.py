"""Divide e indexa documentación del proyecto en un vector store Chroma local."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

if TYPE_CHECKING:
    from langchain_chroma import Chroma

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUTA_VECTORSTORE = PROJECT_ROOT / "vectorstore"
NOMBRE_COLECCION = "curso_ia_corpus"
MODELO_EMBEDDINGS = "models/gemini-embedding-001"
TAMANO_CHUNK = 400
SOLAPAMIENTO_CHUNK = 60

CORPUS_DOCUMENTOS = (
    Document(
        page_content=(
            "El cliente reintenta errores transitorios hasta tres veces en total, "
            "con backoff exponencial y jitter. No reintenta errores de "
            "autenticación 401/403."
        ),
        metadata={"source": "src/GATE_2/cliente.py"},
    ),
    Document(
        page_content=(
            "El costo de Gemini se calcula con promptTokenCount a la tarifa de "
            "entrada y candidatesTokenCount más thoughtsTokenCount a la tarifa "
            "de salida. El total se estima localmente y no es una factura."
        ),
        metadata={"source": "src/GATE_2/costo.py"},
    ),
    Document(
        page_content=(
            "El agente de soporte consulta documentación y estima costos con "
            "herramientas. El historial de conversación se separa por "
            "session_id y se conserva en memoria durante el proceso."
        ),
        metadata={"source": "src/GATE_2/agente_con_herramientas.py"},
    ),
    Document(
        page_content=(
            "Las trazas del agente se guardan en JSONL con entrada, herramientas, "
            "argumentos, observaciones y respuesta final. El analizador marca "
            "invocaciones consecutivas de una misma herramienta para revisión."
        ),
        metadata={"source": "src/GATE_2/trazas_agente.py"},
    ),
    Document(
        page_content=(
            "Las pruebas automatizadas simulan las respuestas de los modelos y "
            "no requieren llamadas de red. Ejecuta python -m pytest -q desde "
            "la raíz para comprobar el proyecto localmente."
        ),
        metadata={"source": "tests/"},
    ),
)


def dividir_corpus(
    documentos: Sequence[Document] = CORPUS_DOCUMENTOS,
    *,
    chunk_size: int = TAMANO_CHUNK,
    chunk_overlap: int = SOLAPAMIENTO_CHUNK,
) -> list[Document]:
    """Divide al menos cinco documentos en chunks recursivos con metadatos."""
    if len(documentos) < 5:
        raise ValueError("El corpus debe contener al menos cinco documentos.")
    if (
        isinstance(chunk_size, bool)
        or not isinstance(chunk_size, int)
        or chunk_size <= 0
    ):
        raise ValueError("chunk_size debe ser mayor que cero.")
    if (
        isinstance(chunk_overlap, bool)
        or not isinstance(chunk_overlap, int)
        or chunk_overlap < 0
        or chunk_overlap >= chunk_size
    ):
        raise ValueError(
            "chunk_overlap debe ser no negativo y menor que chunk_size."
        )
    if any(
        not isinstance(documento, Document)
        or not documento.page_content.strip()
        or not isinstance(documento.metadata.get("source"), str)
        or not documento.metadata["source"].strip()
        for documento in documentos
    ):
        raise ValueError(
            "Cada documento debe tener contenido y metadatos source no vacíos."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_documents(list(documentos))
    contadores: dict[str, int] = {}
    for chunk in chunks:
        fuente = str(chunk.metadata["source"])
        indice = contadores.get(fuente, 0)
        chunk.metadata["chunk_index"] = indice
        contadores[fuente] = indice + 1
    return chunks


def _ids_para_chunks(chunks: Sequence[Document]) -> list[str]:
    """Asigna IDs estables para que volver a indexar actualice en vez de duplicar."""
    return [
        f"{chunk.metadata['source']}::chunk-{chunk.metadata['chunk_index']}"
        for chunk in chunks
    ]


def crear_embeddings() -> Embeddings:
    """Carga la clave local y prepara el modelo de embeddings de Gemini."""
    from dotenv import load_dotenv
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise ValueError(
            f"Falta GEMINI_API_KEY. Configúrala en {PROJECT_ROOT / '.env'}."
        )
    return GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)


def abrir_vectorstore(
    embeddings: Embeddings,
    persist_directory: str | Path = RUTA_VECTORSTORE,
) -> Chroma:
    """Conecta con la colección persistida sin volver a indexar el corpus."""
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=NOMBRE_COLECCION,
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
    )


def validar_fuentes_actuales(vectorstore: Chroma) -> None:
    """Migra referencias obsoletas verificables y rechaza el resto."""
    fuentes_actuales = {
        str(documento.metadata["source"])
        for documento in CORPUS_DOCUMENTOS
    }
    metadatos = vectorstore.get(include=["metadatas"])["metadatas"]
    fuentes_obsoletas = sorted(
        {
            metadata["source"]
            for metadata in metadatos
            if metadata
            and isinstance(metadata.get("source"), str)
            and metadata["source"].startswith("src/")
            and metadata["source"] not in fuentes_actuales
        }
    )
    if fuentes_obsoletas:
        migrar_fuentes_obsoletas(vectorstore)
        metadatos = vectorstore.get(include=["metadatas"])["metadatas"]
        fuentes_sin_migrar = {
            metadata["source"]
            for metadata in metadatos
            if metadata
            and isinstance(metadata.get("source"), str)
            and metadata["source"].startswith("src/")
            and metadata["source"] not in fuentes_actuales
        }
        if fuentes_sin_migrar:
            raise ValueError(
                "El índice contiene fuentes de código que no coinciden con "
                "el corpus actual. Ejecuta "
                "python -m src.GATE_2.indexar_corpus para reindexar."
            )


def migrar_fuentes_obsoletas(vectorstore: Chroma) -> int:
    """Actualiza IDs y fuentes obsoletas al reutilizar embeddings existentes."""
    datos = vectorstore.get(
        include=["documents", "metadatas", "embeddings"]
    )
    campos_requeridos = ("ids", "documents", "metadatas", "embeddings")
    if any(datos.get(campo) is None for campo in campos_requeridos):
        raise ValueError(
            "No se pueden verificar los documentos y embeddings obsoletos. "
            "Ejecuta python -m src.GATE_2.indexar_corpus para reindexar."
        )
    if len({len(datos[campo]) for campo in campos_requeridos}) != 1:
        raise ValueError(
            "El índice tiene registros incompletos; reindexa el corpus."
        )
    chunks_actuales = dividir_corpus()
    fuentes_actuales = {
        str(documento.metadata["source"])
        for documento in CORPUS_DOCUMENTOS
    }
    chunks_por_contenido = {
        (
            str(chunk.metadata["source"]).rsplit("/", 1)[-1],
            chunk.metadata["chunk_index"],
            chunk.page_content,
        ): chunk
        for chunk in chunks_actuales
    }
    ids_existentes = set(datos["ids"])
    datos_por_id = {
        identificador: (metadata, contenido)
        for identificador, metadata, contenido in zip(
            datos["ids"],
            datos["metadatas"],
            datos["documents"],
        )
    }
    adiciones: list[tuple[str, str, dict[str, object], list[float]]] = []
    ids_antiguos: list[str] = []

    for identificador, metadata, contenido, embedding in zip(
        datos["ids"],
        datos["metadatas"],
        datos["documents"],
        datos["embeddings"],
    ):
        if (
            not metadata
            or not isinstance(metadata.get("source"), str)
            or not metadata["source"].startswith("src/")
            or metadata["source"] in fuentes_actuales
        ):
            continue

        clave = (
            metadata["source"].rsplit("/", 1)[-1],
            metadata.get("chunk_index"),
            contenido,
        )
        chunk_actual = chunks_por_contenido.get(clave)
        if chunk_actual is None:
            raise ValueError(
                "No se puede migrar una fuente obsoleta sin una coincidencia "
                "exacta de contenido. Ejecuta "
                "python -m src.GATE_2.indexar_corpus para reindexar."
            )

        id_actual = _ids_para_chunks([chunk_actual])[0]
        if id_actual in ids_existentes:
            metadata_existente, contenido_existente = datos_por_id[id_actual]
            if (
                contenido_existente != contenido
                or not metadata_existente
                or metadata_existente.get("source")
                != chunk_actual.metadata["source"]
            ):
                raise ValueError(
                    f"El ID destino {id_actual!r} ya existe con otro contenido."
                )
            ids_antiguos.append(identificador)
            continue
        if embedding is None:
            raise ValueError(
                "Falta un embedding almacenado para migrar una fuente obsoleta. "
                "Ejecuta python -m src.GATE_2.indexar_corpus para reindexar."
            )

        vector = (
            embedding.tolist()
            if hasattr(embedding, "tolist")
            else list(embedding)
        )
        metadatos_actualizados = {
            **metadata,
            **chunk_actual.metadata,
        }
        adiciones.append(
            (id_actual, contenido, metadatos_actualizados, vector)
        )
        ids_existentes.add(id_actual)
        ids_antiguos.append(identificador)

    if ids_antiguos:
        if adiciones:
            vectorstore._collection.add(
                ids=[identificador for identificador, *_ in adiciones],
                documents=[contenido for _, contenido, _, _ in adiciones],
                metadatas=[metadata for _, _, metadata, _ in adiciones],
                embeddings=[embedding for _, _, _, embedding in adiciones],
            )
        vectorstore.delete(ids=ids_antiguos)

    return len(ids_antiguos)


def _persistir_chunks(
    chunks: Sequence[Document],
    embeddings: Embeddings,
    persist_directory: str | Path,
) -> Chroma:
    """Guarda chunks y elimina los que quedaron obsoletos para sus fuentes."""
    ids = _ids_para_chunks(chunks)
    vectorstore = abrir_vectorstore(embeddings, persist_directory)

    vectorstore.add_documents(documents=list(chunks), ids=ids)

    fuentes = {str(chunk.metadata["source"]) for chunk in chunks}
    ids_actuales = set(ids)
    existentes = vectorstore.get()
    ids_obsoletos = sorted(
        identificador
        for identificador, metadata in zip(
            existentes["ids"],
            existentes["metadatas"],
        )
        if metadata
        and (
            (
                metadata.get("source") in fuentes
                and identificador not in ids_actuales
            )
            or (
                isinstance(metadata.get("source"), str)
                and metadata["source"].startswith("src/")
                and metadata["source"] not in fuentes
            )
        )
    )
    if ids_obsoletos:
        vectorstore.delete(ids=ids_obsoletos)

    return vectorstore


def indexar_corpus(
    embeddings: Embeddings | None = None,
    *,
    persist_directory: str | Path = RUTA_VECTORSTORE,
    documentos: Sequence[Document] = CORPUS_DOCUMENTOS,
) -> Chroma:
    """Persiste los chunks; las llamadas repetidas actualizan IDs existentes."""
    modelo_embeddings = (
        embeddings if embeddings is not None else crear_embeddings()
    )
    chunks = dividir_corpus(documentos)
    return _persistir_chunks(chunks, modelo_embeddings, persist_directory)


def _imprimir_paso(numero: int, titulo: str) -> None:
    separador = "=" * 58
    print(f"\n{separador}\nPASO {numero}: {titulo}\n{separador}")


def _mostrar_contenido_vectorstore(
    persist_directory: str | Path,
) -> None:
    ruta = Path(persist_directory)
    elementos = sorted(ruta.iterdir(), key=lambda elemento: elemento.name)
    print(
        f"Contenido real de la carpeta vectorstore/ "
        f"({len(elementos)} elementos):"
    )
    for elemento in elementos:
        sufijo = (
            "/"
            if elemento.is_dir()
            else f"  ({elemento.stat().st_size} bytes)"
        )
        print(f"  {elemento.name}{sufijo}")


def main() -> int:
    """Indexa el corpus real; esta operación genera embeddings con Gemini."""
    try:
        _imprimir_paso(1, "chunking + embeddings + indexación")
        chunks = dividir_corpus()
        print(f"Corpus original: {len(CORPUS_DOCUMENTOS)} documentos")
        print(f"Después de chunking: {len(chunks)} chunks\n")
        for indice, chunk in enumerate(chunks, start=1):
            print(f"  chunk {indice}: {chunk.page_content}")

        print(
            "\nCalculando embeddings e indexando en Chroma "
            "(esto llama a la API)..."
        )
        embeddings = crear_embeddings()
        vectorstore = _persistir_chunks(chunks, embeddings, RUTA_VECTORSTORE)

        _imprimir_paso(2, "confirmando que quedó en disco, no solo en memoria")
        _mostrar_contenido_vectorstore(RUTA_VECTORSTORE)

        _imprimir_paso(
            3,
            "reconectando al índice ya persistido (sin recalcular embeddings)",
        )
        reconectado = abrir_vectorstore(embeddings, RUTA_VECTORSTORE)
        cantidad = len(reconectado.get()["ids"])
        print(f"Chunks recuperados al reconectar: {cantidad}")
    except (OSError, ValueError) as error:
        print(f"No se pudo indexar el corpus: {error}", file=sys.stderr)
        return 1

    print(f"\nIndexados {cantidad} chunks en {RUTA_VECTORSTORE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
