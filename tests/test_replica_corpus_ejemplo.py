"""Pruebas locales de la réplica del corpus, sin llamadas a Gemini."""

from pathlib import Path
import sys

import pytest
from langchain_core.embeddings import Embeddings

# Permite importar el proyecto tanto en pytest como al ejecutar este archivo.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1.replica_corpus_ejemplo import (
    CORPUS_EJEMPLO,
    abrir_vectorstore,
    con_reintentos,
    dividir_corpus,
    main,
    verificar_integridad,
)


class EmbeddingsDeterministas(Embeddings):
    """Embeddings pequeños para verificar persistencia local de Chroma."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        valores = [0.0] * 8
        for indice, caracter in enumerate(text.casefold()):
            valores[indice % len(valores)] += ord(caracter) / 1000
        return valores


def test_chunking_y_integridad_coinciden_con_el_resultado_esperado(
    capsys: pytest.CaptureFixture[str],
) -> None:
    chunks = dividir_corpus()

    assert len(chunks) == 5
    assert [len(chunk.page_content) for chunk in chunks] == [106, 103, 99, 85, 97]
    verificar_integridad(chunks)
    salida = capsys.readouterr().out
    assert "chunks vacios: []" in salida
    assert "hay duplicados: False" in salida
    assert "total de caracteres en los chunks: 490" in salida
    assert (
        "total de caracteres en el corpus original: 490" in salida
    )
    assert sum(map(len, CORPUS_EJEMPLO)) == 490


def test_chunking_rechaza_texto_vacio() -> None:
    with pytest.raises(ValueError, match="textos no vacíos"):
        dividir_corpus(("texto válido", "  "))


def test_con_reintentos_usa_backoff_exponencial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    esperas: list[float] = []
    llamadas = 0

    def dormir(espera: float) -> None:
        esperas.append(espera)

    def operacion() -> str:
        nonlocal llamadas
        llamadas += 1
        if llamadas < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "indexado"

    monkeypatch.setattr(
        "src.GATE_1.replica_corpus_ejemplo.time.sleep",
        dormir,
    )

    assert con_reintentos(operacion) == "indexado"
    assert llamadas == 3
    assert esperas == [5, 10]


def test_con_reintentos_no_repite_errores_no_relacionados_con_cuota() -> None:
    llamadas = 0

    def operacion() -> None:
        nonlocal llamadas
        llamadas += 1
        raise RuntimeError("API key not valid")

    with pytest.raises(RuntimeError, match="API key not valid"):
        con_reintentos(operacion)

    assert llamadas == 1


def test_con_reintentos_propaga_el_error_al_agotar_intentos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    esperas: list[float] = []
    monkeypatch.setattr(
        "src.GATE_1.replica_corpus_ejemplo.time.sleep",
        lambda espera: esperas.append(espera),
    )

    with pytest.raises(RuntimeError, match="429"):
        con_reintentos(
            lambda: (_ for _ in ()).throw(RuntimeError("429")),
            max_intentos=2,
        )
    assert esperas == [5]


def test_indexacion_persistencia_y_reconexion_sin_duplicados(
    tmp_path: Path,
) -> None:
    embeddings = EmbeddingsDeterministas()
    ruta = tmp_path / "vectorstore_ejemplo"

    assert main(ruta, embeddings) == 0
    assert main(ruta, embeddings) == 0

    recargado = abrir_vectorstore(embeddings, ruta)
    assert len(recargado.get()["ids"]) == 5
    assert ruta.is_dir()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
