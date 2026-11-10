"""Pruebas locales de chunking y persistencia sin API de embeddings."""

from pathlib import Path
import sys

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import src.GATE_1.indexar_corpus as indexador

from src.GATE_1.indexar_corpus import (
    CORPUS_DOCUMENTOS,
    TAMANO_CHUNK,
    abrir_vectorstore,
    dividir_corpus,
    indexar_corpus,
)


class EmbeddingsDeterministas(Embeddings):
    """Embeddings pequeños solo para verificar persistencia local de Chroma."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        valores = [0.0] * 8
        for indice, caracter in enumerate(text.casefold()):
            valores[indice % len(valores)] += ord(caracter) / 1000
        return valores


def test_corpus_tiene_cinco_fuentes_y_chunks_validos() -> None:
    chunks = dividir_corpus()

    assert len(CORPUS_DOCUMENTOS) >= 5
    assert len(chunks) >= 5
    assert all(0 < len(chunk.page_content) <= TAMANO_CHUNK for chunk in chunks)
    assert all(chunk.metadata["source"] for chunk in chunks)
    assert all(isinstance(chunk.metadata["chunk_index"], int) for chunk in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (100, 100), (100, -1)],
)
def test_chunking_rechaza_parametros_invalidos(
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    with pytest.raises(ValueError):
        dividir_corpus(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def test_chunking_rechaza_corpus_menor_a_cinco_documentos() -> None:
    with pytest.raises(ValueError, match="al menos cinco"):
        dividir_corpus(CORPUS_DOCUMENTOS[:4])


def test_chroma_persiste_recarga_y_no_duplica_al_reindexar(
    tmp_path: Path,
) -> None:
    embeddings = EmbeddingsDeterministas()
    ruta = tmp_path / "vectorstore"

    index = indexar_corpus(
        embeddings,
        persist_directory=ruta,
    )
    cantidad_inicial = len(index.get()["ids"])
    indexar_corpus(embeddings, persist_directory=ruta)
    recargado = abrir_vectorstore(embeddings, ruta)

    assert cantidad_inicial >= 5
    assert len(recargado.get()["ids"]) == cantidad_inicial
    assert ruta.is_dir()


def test_main_muestra_indexacion_persistencia_y_reconexion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ruta = tmp_path / "vectorstore"
    monkeypatch.setattr(indexador, "RUTA_VECTORSTORE", ruta)
    monkeypatch.setattr(indexador, "crear_embeddings", EmbeddingsDeterministas)

    assert indexador.main() == 0

    salida = capsys.readouterr().out
    assert "PASO 1: chunking + embeddings + indexación" in salida
    assert "Corpus original: 5 documentos" in salida
    assert "Después de chunking: 5 chunks" in salida
    assert "PASO 2: confirmando que quedó en disco" in salida
    assert "chroma.sqlite3" in salida
    assert "PASO 3: reconectando al índice ya persistido" in salida
    assert "Chunks recuperados al reconectar: 5" in salida


def test_reindexar_elimina_chunks_obsoletos_de_las_mismas_fuentes(
    tmp_path: Path,
) -> None:
    embeddings = EmbeddingsDeterministas()
    ruta = tmp_path / "vectorstore"
    corpus_largo = tuple(
        Document(
            page_content=(
                f"Documento {indice}. " + ("detalle del proyecto " * 35)
            ),
            metadata={"source": f"documento-{indice}.md"},
        )
        for indice in range(5)
    )
    corpus_corto = tuple(
        Document(
            page_content=f"Documento breve {indice}.",
            metadata={"source": f"documento-{indice}.md"},
        )
        for indice in range(5)
    )

    index_largo = indexar_corpus(
        embeddings,
        persist_directory=ruta,
        documentos=corpus_largo,
    )
    cantidad_larga = len(index_largo.get()["ids"])
    index_corto = indexar_corpus(
        embeddings,
        persist_directory=ruta,
        documentos=corpus_corto,
    )

    assert cantidad_larga > 5
    assert len(index_corto.get()["ids"]) == 5


def test_no_se_acepta_documento_sin_fuente() -> None:
    documentos = tuple(CORPUS_DOCUMENTOS[:4]) + (
        Document(page_content="Documento sin metadatos."),
    )

    with pytest.raises(ValueError, match="metadatos source"):
        dividir_corpus(documentos)
