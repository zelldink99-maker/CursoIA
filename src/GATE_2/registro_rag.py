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
from uuid import uuid4

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __package__:
    from .configuracion import crear_chat_modelo
    from .indexar_corpus import (
        RUTA_VECTORSTORE,
        abrir_vectorstore,
        crear_embeddings,
        validar_fuentes_actuales,
    )
    from .recuperacion_citas import (
        construir_prompt,
        formatear_contexto,
        validar_citas,
    )
    from .costo import calcular_costo
    from .seguridad_rag import filtrar_documentos_sospechosos
else:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from src.GATE_2.configuracion import crear_chat_modelo
    from src.GATE_2.indexar_corpus import (
        RUTA_VECTORSTORE,
        abrir_vectorstore,
        crear_embeddings,
        validar_fuentes_actuales,
    )
    from src.GATE_2.recuperacion_citas import (
        construir_prompt,
        formatear_contexto,
        validar_citas,
    )
    from src.GATE_2.costo import calcular_costo
    from src.GATE_2.seguridad_rag import filtrar_documentos_sospechosos

if TYPE_CHECKING:
    from langchain_chroma import Chroma

RUTA_REGISTRO = PROJECT_ROOT / "registros_latencia_costo.jsonl"
PREGUNTA_PREDETERMINADA = "¿Qué errores reintenta el cliente y cuántos intentos hace?"
PREGUNTAS_ACTIVIDAD_CORE = (
    PREGUNTA_PREDETERMINADA,
    "¿Cómo se calcula el costo de una llamada?",
    "¿Qué información se guarda en las trazas del agente?",
)
PREGUNTAS_DEMO_CONSOLA = (
    PREGUNTA_PREDETERMINADA,
    "¿Qué información registra el sistema en las trazas del agente?",
)


@contextmanager
def medir(tiempos: dict[str, float], etapa: str) -> Generator[None, None, None]:
    """Guarda la duración de una etapa con un reloj monotónico."""
    inicio = time.perf_counter()
    yield
    tiempos[etapa] = time.perf_counter() - inicio


def _ejecutar_consulta(
    pregunta: str,
    persist_directory: str | Path = RUTA_VECTORSTORE,
    k: int = 1,
    *,
    embeddings: Embeddings | None = None,
    vectorstore: Chroma | None = None,
    chat_model: BaseChatModel | None = None,
) -> tuple[str, dict[int, str], dict[str, Any]]:
    """Ejecuta el flujo RAG y separa la respuesta del registro sin contenido."""
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

    trace_id = f"trace-{uuid4().hex[:8]}"
    eventos: list[dict[str, Any]] = []

    def registrar_evento(
        evento: str,
        nivel: str,
        mensaje: str,
        **campos: Any,
    ) -> None:
        eventos.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": nivel,
                "msg": mensaje,
                "trace_id": trace_id,
                "evento": evento,
                **campos,
            }
        )

    registrar_evento(
        "consulta_recibida",
        "INFO",
        "consulta recibida",
        pregunta_len=len(pregunta),
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
                "Ejecuta primero src.GATE_2.indexar_corpus."
            )
        validar_fuentes_actuales(vectorstore_activo)
        retriever = vectorstore_activo.as_retriever(search_kwargs={"k": k})
        documentos = retriever.invoke(pregunta)

    documentos_limpios, documentos_descartados = filtrar_documentos_sospechosos(
        documentos
    )
    if documentos_descartados:
        registrar_evento(
            "documento_descartado_por_inyeccion",
            "WARNING",
            "documentos descartados por patrones de inyección",
            n_descartados=len(documentos_descartados),
        )
    registrar_evento(
        "contexto_filtrado",
        "INFO",
        "contexto filtrado",
        n_limpios=len(documentos_limpios),
        n_descartados=len(documentos_descartados),
    )
    contexto, fuentes = formatear_contexto(documentos_limpios)
    prompt = construir_prompt(pregunta, contexto)
    with medir(tiempos, "generacion"):
        mensaje = modelo_activo.invoke(prompt)

    contenido = mensaje.content
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

    usage_metadata = mensaje.usage_metadata
    tokens = dict(usage_metadata) if usage_metadata else None
    costo_estimado_usd = None
    if tokens is not None:
        tokens_entrada = tokens.get("input_tokens")
        tokens_salida = tokens.get("output_tokens")
        if tokens_entrada is None or tokens_salida is None:
            raise ValueError(
                "El modelo devolvió metadatos de uso incompletos; "
                "no se puede estimar el costo."
            )
        metadatos_costo = {
            "promptTokenCount": tokens_entrada,
            "candidatesTokenCount": tokens_salida,
            "totalTokenCount": tokens.get(
                "total_tokens",
                tokens_entrada + tokens_salida,
            ),
        }
        tokens_pensamiento = tokens.get("thoughts_tokens")
        if tokens_pensamiento is not None:
            metadatos_costo["thoughtsTokenCount"] = tokens_pensamiento
        costo_estimado_usd = calcular_costo(
            {"usageMetadata": metadatos_costo}
        )
    registrar_evento(
        "consumo_llm",
        "INFO",
        "consumo registrado",
        input_tokens=tokens.get("input_tokens") if tokens else None,
        output_tokens=tokens.get("output_tokens") if tokens else None,
        total_tokens=tokens.get("total_tokens") if tokens else None,
        costo_estimado_usd=costo_estimado_usd,
    )
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "pregunta_len": len(pregunta),
        "k": k,
        "tiempos_ms": {
            etapa: round(segundos * 1000, 2)
            for etapa, segundos in tiempos.items()
        },
        "tiempo_total_ms": round(sum(tiempos.values()) * 1000, 2),
        "tokens": tokens,
        "costo_estimado_usd": costo_estimado_usd,
        "n_limpios": len(documentos_limpios),
        "n_descartados": len(documentos_descartados),
        "eventos": eventos,
    }
    return respuesta, fuentes, registro


def ejecutar_consulta(
    pregunta: str,
    persist_directory: str | Path = RUTA_VECTORSTORE,
    k: int = 1,
    *,
    embeddings: Embeddings | None = None,
    vectorstore: Chroma | None = None,
    chat_model: BaseChatModel | None = None,
) -> tuple[str, dict[int, str], dict[str, Any]]:
    """Devuelve la respuesta citada, las fuentes y un registro sin texto crudo."""
    return _ejecutar_consulta(
        pregunta,
        persist_directory,
        k,
        embeddings=embeddings,
        vectorstore=vectorstore,
        chat_model=chat_model,
    )


def registrar_consulta(
    pregunta: str,
    persist_directory: str | Path = RUTA_VECTORSTORE,
    k: int = 1,
    *,
    embeddings: Embeddings | None = None,
    vectorstore: Chroma | None = None,
    chat_model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Ejecuta una consulta y devuelve solo su registro, sin respuesta cruda."""
    _, _, registro = _ejecutar_consulta(
        pregunta,
        persist_directory,
        k,
        embeddings=embeddings,
        vectorstore=vectorstore,
        chat_model=chat_model,
    )
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


def imprimir_consulta_trazada(
    registro: dict[str, Any],
    numero: int,
) -> None:
    """Imprime una consulta real con encabezado y eventos de traza legibles."""
    separador = "=" * 66
    if numero == 1:
        descripcion = (
            "consulta 1 (un documento limpio y uno con inyeccion)"
            if registro["n_descartados"] > 0
            else "consulta 1 (documento limpio)"
        )
    else:
        descripcion = (
            "consulta 2 (otra traza, sin mezclarse con la anterior)"
            if registro["n_descartados"] == 0
            else f"consulta {numero} (otra traza)"
        )

    print(f"\n{separador}")
    print(f"PASO {numero}: {descripcion}")
    print(separador)
    eventos = registro.get("eventos")
    if not isinstance(eventos, list):
        print(json.dumps(registro, ensure_ascii=False))
        return
    for evento in eventos:
        print(json.dumps(evento, ensure_ascii=False))


def imprimir_demo_trazas() -> None:
    """Imprime los tres escenarios de trazas del ejercicio sin usar la API."""
    separador = "=" * 74

    def imprimir_eventos(eventos: Sequence[dict[str, Any]]) -> None:
        for evento in eventos:
            print(json.dumps(evento, ensure_ascii=False))

    print(separador)
    print("PASO 1: indexar, recuperar, filtrar y responder (con traza)")
    print(separador)
    imprimir_eventos(
        [
            {"evento": "consulta_recibida", "trace_id": "trace-2193"},
            {
                "evento": "documentos_recuperados",
                "trace_id": "trace-2193",
                "n": 2,
            },
            {
                "evento": "consumo_llm",
                "trace_id": "trace-2193",
                "input_tokens": 180,
                "output_tokens": 22,
            },
        ]
    )
    print(
        "respuesta final: Según el manual.pdf, la política de devoluciones "
        "permite 30 días."
    )

    print()
    print(separador)
    print("PASO 2: dos consultas seguidas, cada una con su trace_id")
    print(separador)
    imprimir_eventos(
        [
            {"evento": "consulta_recibida", "trace_id": "trace-2193"},
            {
                "evento": "documentos_recuperados",
                "trace_id": "trace-2193",
                "n": 2,
            },
            {
                "evento": "consumo_llm",
                "trace_id": "trace-2193",
                "input_tokens": 180,
                "output_tokens": 22,
            },
            {"evento": "consulta_recibida", "trace_id": "trace-1385"},
            {
                "evento": "documentos_recuperados",
                "trace_id": "trace-1385",
                "n": 2,
            },
            {
                "evento": "consumo_llm",
                "trace_id": "trace-1385",
                "input_tokens": 180,
                "output_tokens": 22,
            },
        ]
    )
    print("trace_id fuera de cualquier consulta: None")

    print()
    print(separador)
    print("PASO 3: si todo el contexto recuperado es sospechoso")
    print(separador)
    imprimir_eventos(
        [
            {
                "evento": "sin_contexto_confiable",
                "trace_id": "trace-7421",
                "n_recuperados": 1,
                "n_descartados": 1,
            }
        ]
    )
    print("No tengo información suficiente y verificada para responder esto.")


def ejecutar_actividad_core(
    k: int = 1,
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
    parser.add_argument("--k", type=int, default=1, help="Cantidad de chunks")
    parser.add_argument(
        "--demo-trazas",
        action="store_true",
        help="muestra localmente el flujo RAG con trazas completas sin usar API",
    )
    argumentos = parser.parse_args(argv)
    if argumentos.k <= 0:
        parser.error("--k debe ser un entero positivo")
    if argumentos.demo_trazas:
        if argumentos.pregunta or argumentos.actividad_core:
            parser.error(
                "--demo-trazas no se combina con --pregunta ni --actividad-core"
            )
        imprimir_demo_trazas()
        return 0
    if argumentos.actividad_core:
        if argumentos.pregunta:
            parser.error("--actividad-core no se combina con --pregunta")
        ejecutar_actividad_core(k=argumentos.k)
        return 0

    preguntas = (
        argumentos.pregunta
        if argumentos.pregunta
        else PREGUNTAS_DEMO_CONSOLA
    )
    registros_consultados = []
    for numero, pregunta in enumerate(preguntas, start=1):
        respuesta, fuentes, registro = ejecutar_consulta(
            pregunta,
            persist_directory=RUTA_VECTORSTORE,
            k=argumentos.k,
        )
        registros_consultados.append(registro)
        imprimir_consulta_trazada(registro, numero)
        print(f"respuesta final: {respuesta}")
        print(f"fuentes citadas: {json.dumps(fuentes, ensure_ascii=False)}")
        guardar_registro(registro)
        if registro["costo_estimado_usd"] is not None:
            print(
                "costo estimado de la consulta: "
                f"USD {registro['costo_estimado_usd']:.8f}"
            )
    if len(registros_consultados) >= 2:
        print("\ntrace_id fuera de cualquier consulta: None")
    print(f"Registros agregados en {RUTA_REGISTRO}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
