"""Mide la latencia RAG y registra los tokens reales reportados por el modelo."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __package__:
    from .configuracion import crear_chat_modelo
    from .indexar_corpus import (
        RUTA_VECTORSTORE,
        abrir_vectorstore,
        crear_embeddings,
    )
    from .recuperacion_citas import construir_prompt, formatear_contexto
else:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from src.GATE_1.configuracion import crear_chat_modelo
    from src.GATE_1.indexar_corpus import (
        RUTA_VECTORSTORE,
        abrir_vectorstore,
        crear_embeddings,
    )
    from src.GATE_1.recuperacion_citas import (
        construir_prompt,
        formatear_contexto,
    )

if TYPE_CHECKING:
    from langchain_chroma import Chroma

RUTA_REGISTRO = PROJECT_ROOT / "registros_latencia_costo.jsonl"
PREGUNTA_PREDETERMINADA = "¿Qué errores reintenta el cliente y cuántos intentos hace?"
PREGUNTAS_ACTIVIDAD_CORE = (
    PREGUNTA_PREDETERMINADA,
    "¿Cómo se calcula el costo de una llamada?",
    "¿Qué información se guarda en las trazas del agente?",
)


@contextmanager
def medir(tiempos: dict[str, float], etapa: str) -> Generator[None, None, None]:
    """Guarda la duración de una etapa con un reloj monotónico."""
    inicio = time.perf_counter()
    yield
    tiempos[etapa] = time.perf_counter() - inicio


def registrar_consulta(
    pregunta: str,
    persist_directory: str | Path = RUTA_VECTORSTORE,
    k: int = 3,
    *,
    embeddings: Embeddings | None = None,
    vectorstore: Chroma | None = None,
    chat_model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Ejecuta una consulta RAG y devuelve tiempos y tokens reales."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser un texto no vacío.")
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k debe ser un entero positivo.")

    embeddings_activos = (
        embeddings if embeddings is not None else crear_embeddings()
    )
    modelo_activo = (
        chat_model if chat_model is not None else crear_chat_modelo()
    )

    tiempos: dict[str, float] = {}
    with medir(tiempos, "embed_y_busqueda"):
        vectorstore_activo = (
            vectorstore
            if vectorstore is not None
            else abrir_vectorstore(embeddings_activos, persist_directory)
        )
        if not vectorstore_activo.get(limit=1)["ids"]:
            raise ValueError(
                f"No hay chunks indexados en {persist_directory}. "
                "Ejecuta primero src.GATE_1.indexar_corpus."
            )
        retriever = vectorstore_activo.as_retriever(search_kwargs={"k": k})
        documentos = retriever.invoke(pregunta)

    contexto, _ = formatear_contexto(documentos)
    prompt = construir_prompt(pregunta, contexto)
    with medir(tiempos, "generacion"):
        respuesta = modelo_activo.invoke(prompt)

    usage_metadata = respuesta.usage_metadata
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pregunta": pregunta,
        "k": k,
        "tiempos_ms": {
            etapa: round(segundos * 1000, 2)
            for etapa, segundos in tiempos.items()
        },
        "tiempo_total_ms": round(sum(tiempos.values()) * 1000, 2),
        "tokens": dict(usage_metadata) if usage_metadata else None,
    }
    return registro


def guardar_registro(
    registro: dict[str, Any],
    ruta_registro: str | Path = RUTA_REGISTRO,
) -> None:
    """Agrega un registro JSON en una línea, sin reemplazar el historial."""
    with Path(ruta_registro).open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def _imprimir_paso(numero: int, titulo: str) -> None:
    separador = "=" * 66
    print(f"\n{separador}\nPASO {numero}: {titulo}\n{separador}")


def _tokens_entrada(registro: dict[str, Any]) -> str:
    tokens = registro["tokens"]
    if not isinstance(tokens, dict) or tokens.get("input_tokens") is None:
        return "n/a"
    return str(tokens["input_tokens"])


def ejecutar_actividad_core(
    k: int = 3,
    ruta_registro: str | Path = RUTA_REGISTRO,
) -> list[dict[str, Any]]:
    """Ejecuta los cinco registros de la actividad core y muestra su resumen."""
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k debe ser un entero positivo.")

    embeddings = crear_embeddings()
    vectorstore = abrir_vectorstore(embeddings, RUTA_VECTORSTORE)
    chat_model = crear_chat_modelo()
    argumentos = {
        "persist_directory": RUTA_VECTORSTORE,
        "embeddings": embeddings,
        "vectorstore": vectorstore,
        "chat_model": chat_model,
    }

    _imprimir_paso(
        1,
        "registrando 3 consultas distintas (Como se prueba, chequeo 1)",
    )
    registros_distintos = [
        registrar_consulta(pregunta, k=k, **argumentos)
        for pregunta in PREGUNTAS_ACTIVIDAD_CORE
    ]
    for registro in registros_distintos:
        guardar_registro(registro, ruta_registro)
    print(json.dumps(registros_distintos, indent=2, ensure_ascii=False))

    k_comparacion = 2 * k
    _imprimir_paso(
        2,
        f"misma pregunta con k={k} y k={k_comparacion} "
        "(Como se prueba, chequeo 2)",
    )
    registro_k = registrar_consulta(
        PREGUNTAS_ACTIVIDAD_CORE[0],
        k=k,
        **argumentos,
    )
    registro_k_doble = registrar_consulta(
        PREGUNTAS_ACTIVIDAD_CORE[0],
        k=k_comparacion,
        **argumentos,
    )
    guardar_registro(registro_k, ruta_registro)
    guardar_registro(registro_k_doble, ruta_registro)
    print(f"k={k} -> input_tokens: {_tokens_entrada(registro_k)}")
    print(
        f"k={k_comparacion} -> input_tokens: "
        f"{_tokens_entrada(registro_k_doble)}"
    )

    _imprimir_paso(3, "confirmando el archivo de registros")
    ruta = Path(ruta_registro)
    with ruta.open(encoding="utf-8") as archivo:
        cantidad_lineas = sum(1 for _ in archivo)
    print(
        f"{ruta.name} tiene {cantidad_lineas} líneas "
        "(una por corrida)"
    )
    return [*registros_distintos, registro_k, registro_k_doble]


def main(argv: Sequence[str] | None = None) -> int:
    """Registra consultas reales. Cada pregunta puede generar costo de API."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actividad-core",
        action="store_true",
        help=(
            "ejecuta 3 consultas y la comparación k/2k "
            "(5 llamadas de generación)"
        ),
    )
    parser.add_argument(
        "--pregunta",
        action="append",
        help="Pregunta a consultar; puede repetirse.",
    )
    parser.add_argument("--k", type=int, default=3, help="Cantidad de chunks")
    argumentos = parser.parse_args(argv)
    if argumentos.k <= 0:
        parser.error("--k debe ser un entero positivo")
    if argumentos.actividad_core:
        if argumentos.pregunta:
            parser.error("--actividad-core no se combina con --pregunta")
        ejecutar_actividad_core(k=argumentos.k)
        return 0

    preguntas = argumentos.pregunta or [PREGUNTA_PREDETERMINADA]
    for pregunta in preguntas:
        registro = registrar_consulta(
            pregunta,
            persist_directory=RUTA_VECTORSTORE,
            k=argumentos.k,
        )
        print(json.dumps(registro, indent=2, ensure_ascii=False))
        guardar_registro(registro)
    print(f"Registros agregados en {RUTA_REGISTRO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
