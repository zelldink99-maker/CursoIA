"""Evalúa precisión y exhaustividad del recuperador del corpus RAG."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, TypedDict

from langchain_core.documents import Document

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __package__:
    from .indexar_corpus import (
        RUTA_VECTORSTORE,
        SOLAPAMIENTO_CHUNK,
        TAMANO_CHUNK,
        abrir_vectorstore,
        crear_embeddings,
    )
else:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from src.GATE_1.indexar_corpus import (
        RUTA_VECTORSTORE,
        SOLAPAMIENTO_CHUNK,
        TAMANO_CHUNK,
        abrir_vectorstore,
        crear_embeddings,
    )

RUTA_RESULTADOS = PROJECT_ROOT / "resultados_evaluacion.jsonl"


class CasoEvaluacion(TypedDict):
    pregunta: str
    ids_relevantes: set[str]


class ResultadoEvaluacion(TypedDict):
    pregunta: str
    precision: float
    recall: float | None
    f1: float | None


class Retriever(Protocol):
    def invoke(self, input: str) -> Sequence[Document]: ...


CASOS_EVALUACION: tuple[CasoEvaluacion, ...] = (
    {
        "pregunta": "¿Cuántas veces reintenta el cliente los errores transitorios?",
        "ids_relevantes": {"src/GATE_1/cliente.py::chunk-0"},
    },
    {
        "pregunta": "¿Qué errores no vuelve a intentar el cliente?",
        "ids_relevantes": {"src/GATE_1/cliente.py::chunk-0"},
    },
    {
        "pregunta": "¿Cómo se calcula el costo de entrada de Gemini?",
        "ids_relevantes": {"src/GATE_1/costo.py::chunk-0"},
    },
    {
        "pregunta": "¿Qué tokens se cobran como salida en el cálculo de costos?",
        "ids_relevantes": {"src/GATE_1/costo.py::chunk-0"},
    },
    {
        "pregunta": "¿Cómo se separa la memoria de conversación del agente?",
        "ids_relevantes": {"src/GATE_1/agente_con_herramientas.py::chunk-0"},
    },
    {
        "pregunta": "¿Qué hace el agente de soporte con las herramientas?",
        "ids_relevantes": {"src/GATE_1/agente_con_herramientas.py::chunk-0"},
    },
    {
        "pregunta": "¿Qué información se guarda en las trazas JSONL?",
        "ids_relevantes": {"src/GATE_1/trazas_agente.py::chunk-0"},
    },
    {
        "pregunta": "¿Qué marca el analizador de trazas para revisión?",
        "ids_relevantes": {"src/GATE_1/trazas_agente.py::chunk-0"},
    },
    {
        "pregunta": "¿Las pruebas automatizadas necesitan llamadas a Gemini?",
        "ids_relevantes": {"tests/::chunk-0"},
    },
    {
        "pregunta": "¿Cómo ejecuto la suite local de pruebas del proyecto?",
        "ids_relevantes": {"tests/::chunk-0"},
    },
)


def _validar_k(k: int) -> None:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k debe ser un entero positivo.")


def precision_at_k(ids_recuperados: Sequence[str], ids_relevantes: set[str]) -> float:
    """Fracción de los resultados recuperados que son relevantes."""
    if not ids_recuperados:
        return 0.0
    acertados = set(ids_recuperados) & ids_relevantes
    return len(acertados) / len(ids_recuperados)


def recall_at_k(
    ids_recuperados: Sequence[str],
    ids_relevantes: set[str],
) -> float | None:
    """Fracción de los resultados relevantes que fueron recuperados."""
    if not ids_relevantes:
        return None
    acertados = set(ids_recuperados) & ids_relevantes
    return len(acertados) / len(ids_relevantes)


def f1(precision: float, recall: float | None) -> float | None:
    """Media armónica de precisión y recall; no se define sin relevantes."""
    if recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def promediar(valores: Iterable[float | None]) -> float:
    """Promedia valores definidos e ignora los casos sin recall."""
    validos = [valor for valor in valores if valor is not None]
    return sum(validos) / len(validos) if validos else 0.0


def evaluar_recuperacion(
    retriever: Retriever,
    casos: Sequence[CasoEvaluacion],
    k: int = 3,
) -> tuple[list[ResultadoEvaluacion], float, float, float]:
    """Calcula métricas por pregunta y promedia precisión y recall del top-k."""
    _validar_k(k)
    resultados: list[ResultadoEvaluacion] = []

    for caso in casos:
        documentos = retriever.invoke(caso["pregunta"])
        ids_recuperados: list[str] = []
        for documento in documentos[:k]:
            if not isinstance(documento, Document) or not isinstance(
                documento.id, str
            ):
                raise ValueError(
                    "Un documento recuperado no tiene un ID explícito. "
                    "Reindexa con IDs estables antes de evaluar."
                )
            ids_recuperados.append(documento.id)

        precision = precision_at_k(ids_recuperados, caso["ids_relevantes"])
        recall = recall_at_k(ids_recuperados, caso["ids_relevantes"])
        resultados.append(
            {
                "pregunta": caso["pregunta"],
                "precision": precision,
                "recall": recall,
                "f1": f1(precision, recall),
            }
        )

    precision_promedio = promediar(
        resultado["precision"] for resultado in resultados
    )
    recall_promedio = promediar(resultado["recall"] for resultado in resultados)
    f1_promedio = promediar(resultado["f1"] for resultado in resultados)
    return resultados, precision_promedio, recall_promedio, f1_promedio


def guardar_resultado(
    resultados: Sequence[ResultadoEvaluacion],
    precision_promedio: float,
    recall_promedio: float,
    k: int,
    ruta: str | Path = RUTA_RESULTADOS,
) -> None:
    """Agrega una corrida al historial JSONL sin reemplazar corridas previas."""
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "k": k,
        "chunk_size": TAMANO_CHUNK,
        "chunk_overlap": SOLAPAMIENTO_CHUNK,
        "resultados": list(resultados),
        "precision_promedio": precision_promedio,
        "recall_promedio": recall_promedio,
        "f1_promedio": promediar(
            resultado["f1"] for resultado in resultados
        ),
    }
    with Path(ruta).open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Evalúa el vector store persistido; las búsquedas usan la API de embeddings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=3, help="Cantidad de resultados")
    argumentos = parser.parse_args(argv)
    if argumentos.k <= 0:
        parser.error("--k debe ser un entero positivo")

    embeddings = crear_embeddings()
    vectorstore = abrir_vectorstore(embeddings, RUTA_VECTORSTORE)
    if not vectorstore.get(limit=1)["ids"]:
        raise ValueError(
            f"No hay chunks indexados en {RUTA_VECTORSTORE}. "
            "Ejecuta primero src.GATE_1.indexar_corpus."
        )
    retriever = vectorstore.as_retriever(search_kwargs={"k": argumentos.k})
    (
        resultados,
        precision_promedio,
        recall_promedio,
        f1_promedio,
    ) = evaluar_recuperacion(retriever, CASOS_EVALUACION, k=argumentos.k)

    for resultado in resultados:
        recall_txt = (
            "n/a"
            if resultado["recall"] is None
            else f'{resultado["recall"]:.2f}'
        )
        print(
            f'{resultado["precision"]:.2f}  {recall_txt}  '
            f'{resultado["pregunta"]}'
        )
    print(
        f"\npromedio -> precision: {precision_promedio:.3f}  "
        f"recall: {recall_promedio:.3f}  "
        f"F1: {f1_promedio:.3f}"
    )
    guardar_resultado(
        resultados,
        precision_promedio,
        recall_promedio,
        argumentos.k,
    )
    print(f"Resultados agregados en {RUTA_RESULTADOS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
